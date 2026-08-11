# -*- coding: utf-8 -*-
"""切片 6a 测试：V11-GW-001 断言 10——Recall 数据不因投递失败产生重复写入。

覆盖：send-reminders 在 webhook 失败 / Hermes 通道模式 / 无到期 三种路径下，
recall.json 记录数不变、reminder_status 语义正确（failed/sent）、无重复记录。
运行：python scripts/test_gw_001.py（临时数据目录）
"""
import json
import os
import subprocess
import sys
import tempfile

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recall.py")
fails = []


def check(name, ok, detail=""):
    print(("PASS" if ok else "FAIL"), "-", name, detail)
    if not ok:
        fails.append(name)


def run(args, env_dir):
    env = dict(os.environ)
    env["HERMES_RECALL_DIR"] = env_dir
    return subprocess.run([sys.executable, SCRIPT] + args, capture_output=True, text=True, encoding="utf-8",
                          env=env, stdin=subprocess.DEVNULL)


def load(env_dir):
    with open(os.path.join(env_dir, "recall.json"), encoding="utf-8") as f:
        return json.load(f)


def make_rec(rid, remind_at):
    return {"id": rid, "schema_version": "2.0", "content": f"提醒 {rid}", "category": "工作待办",
            "status": "待处理", "reminder_status": "pending", "priority": "normal",
            "created_at": "2026-08-01T00:00:00+08:00", "updated_at": "2026-08-01T00:00:00+08:00",
            "tags": [], "needs_reminder": True, "remind_at": remind_at, "source": "user", "metadata": {},
            "timeline": [{"date": "2026-08-01T00:00:00+08:00", "event": "创建回响"}]}


with tempfile.TemporaryDirectory(prefix="recall-gw-") as td:
    # 场景 1：webhook 不可达（127.0.0.1:9 立即拒绝）→ 置 failed，无重复写入
    cfg = {"feishu_webhook_url": "http://127.0.0.1:9/webhook"}
    with open(os.path.join(td, "config.json"), "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False)
    data = {"version": "2.0", "recalls": [make_rec("r1", "2026-08-01T01:00:00+08:00")]}
    with open(os.path.join(td, "recall.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    n_before = len(load(td)["recalls"])
    r = run(["send-reminders"], td)
    data = load(td)
    check("webhook 失败：退出码 1", r.returncode == 1, f"exit={r.returncode}")
    check("webhook 失败：记录数不变（无重复写入）", len(data["recalls"]) == n_before)
    r1 = [x for x in data["recalls"] if x["id"] == "r1"][0]
    check("webhook 失败：reminder_status=failed", r1["reminder_status"] == "failed")
    check("webhook 失败：未置 sent", r1["reminder_status"] != "sent")
    hist_path = os.path.join(td, "recall_history.json")
    if os.path.exists(hist_path):
        hist = json.load(open(hist_path, encoding="utf-8"))
        create_events = [e for e in hist.get("events", []) if e.get("action") == "create"]
        check("History 无重复 create 事件", len(create_events) <= 1)
    else:
        check("History 无重复 create 事件", True, "(无 history 文件=无写入)")

    # 场景 2：Hermes 通道模式（空 webhook）→ 输出提醒文本，置 sent，无重复
    cfg = {"feishu_webhook_url": ""}
    with open(os.path.join(td, "config.json"), "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False)
    data = {"version": "2.0", "recalls": [make_rec("r2", "2026-08-01T01:00:00+08:00")]}
    with open(os.path.join(td, "recall.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    n_before = len(load(td)["recalls"])
    r = run(["send-reminders"], td)
    data = load(td)
    check("Hermes 通道：退出码 0", r.returncode == 0)
    check("Hermes 通道：输出提醒文本", "Hermes Recall 提醒" in r.stdout)
    check("Hermes 通道：记录数不变", len(data["recalls"]) == n_before)
    check("Hermes 通道：reminder_status=sent", [x for x in data["recalls"] if x["id"] == "r2"][0]["reminder_status"] == "sent")

    # 场景 3：无到期提醒 → 静默，数据不变
    data = {"version": "2.0", "recalls": [make_rec("r3", "2099-01-01T00:00:00+08:00")]}
    with open(os.path.join(td, "recall.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    r = run(["send-reminders"], td)
    data = load(td)
    check("无到期：静默退出 0", r.returncode == 0 and r.stdout.strip() == "")
    check("无到期：数据不变", [x for x in data["recalls"] if x["id"] == "r3"][0]["reminder_status"] == "pending")

print()
print("ALL PASS" if not fails else f"{len(fails)} FAILED: {fails}")
sys.exit(1 if fails else 0)
