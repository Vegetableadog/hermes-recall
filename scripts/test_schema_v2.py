# -*- coding: utf-8 -*-
"""切片 1 测试：Schema v2 Record 模型（memory/timeline/parent_id/五状态/七状态提醒）字段读写与默认值。

运行：python scripts/test_schema_v2.py（使用临时数据目录，不触碰生产数据）
"""
import json
import os
import subprocess
import sys
import tempfile

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recall.py")
fails = []


def run(args, env_dir):
    env = dict(os.environ)
    env["HERMES_RECALL_DIR"] = env_dir
    r = subprocess.run([sys.executable, SCRIPT] + args, capture_output=True, text=True, encoding="utf-8", env=env)
    return r


def load(env_dir):
    with open(os.path.join(env_dir, "recall.json"), encoding="utf-8") as f:
        return json.load(f)


def get_rec(env_dir, rid):
    for r in load(env_dir).get("recalls", []):
        if r.get("id") == rid:
            return r
    return None


def check(name, ok, detail=""):
    print(("PASS" if ok else "FAIL"), "-", name, detail)
    if not ok:
        fails.append(name)


with tempfile.TemporaryDirectory(prefix="recall-test-") as td:
    # 1. add 基础记录：默认字段 + timeline 首事件
    r = run(["add", "测试基础记录"], td)
    check("add 基础记录返回 0", r.returncode == 0, r.stderr.strip()[:80])
    data = load(td)
    rec = data["recalls"][0]
    rid = rec["id"]
    check("基础记录 status=待处理", rec.get("status") == "待处理")
    check("基础记录 reminder_status=pending", rec.get("reminder_status") == "pending")
    check("timeline 首事件=创建回响", rec.get("timeline") == [{"date": rec.get("created_at"), "event": "创建回响"}])
    check("无 memory 字段（可选）", "memory" not in rec)
    check("无 parent_id 字段（可选）", "parent_id" not in rec)

    # 2. add 带 memory 参数 + parent_id
    r = run(["add", "带结构化字段", "--memory-type", "task", "--importance", "high",
             "--entities", "项目复盘, 邹总", "--related-ids", rid, "--parent-id", rid], td)
    check("add 结构化字段返回 0", r.returncode == 0, r.stderr.strip()[:80])
    data = load(td)
    rec2 = [x for x in data["recalls"] if x.get("parent_id")][0]
    mem = rec2.get("memory", {})
    check("memory_type=task", mem.get("memory_type") == "task")
    check("importance=high", mem.get("importance") == "high")
    check("entities 去重列表", mem.get("entities") == ["项目复盘", "邹总"])
    check("related_ids 写入", mem.get("related_ids") == [rid])
    check("parent_id 写入", rec2.get("parent_id") == rid)
    rid2 = rec2["id"]

    # 3. update 进入等待反馈（waiting_for 联动）
    r = run(["update", rid, "--waiting-for", "邹总"], td)
    check("update --waiting-for 返回 0", r.returncode == 0, r.stderr.strip()[:80])
    rec = get_rec(td, rid)
    check("status 自动进入等待反馈", rec.get("status") == "等待反馈")
    check("memory.waiting_for=邹总", rec.get("memory", {}).get("waiting_for") == "邹总")
    events = [e["event"] for e in rec.get("timeline", [])]
    check("timeline 追加进入等待事件", any("→等待反馈" in e for e in events), str(events))

    # 4. update 离开等待反馈：先固化再清空
    r = run(["update", rid, "--status", "进行中"], td)
    check("update 离开等待反馈返回 0", r.returncode == 0, r.stderr.strip()[:80])
    rec = get_rec(td, rid)
    check("status=进行中", rec.get("status") == "进行中")
    check("waiting_for 已清空", not rec.get("memory", {}).get("waiting_for"))
    last = rec["timeline"][-1]
    check("timeline 固化等待对象", "等待对象：邹总" in last["event"], str(last))

    # 5. done：timeline 追加 + 已完成
    r = run(["done", rid], td)
    check("done 返回 0", r.returncode == 0)
    rec = get_rec(td, rid)
    check("done 后 status=已完成", rec.get("status") == "已完成")
    check("done 追加 timeline 事件", rec["timeline"][-1]["event"] == "状态更新：进行中→已完成")

    # 6. reminder_status 七状态 + timeline 追加
    r = run(["update", rid, "--reminder-status", "reminded"], td)
    check("update reminder_status 返回 0", r.returncode == 0)
    rec = get_rec(td, rid)
    check("reminder_status=reminded", rec.get("reminder_status") == "reminded")
    check("提醒状态变化追加 timeline", rec["timeline"][-1]["event"] == "提醒状态：pending→reminded")

    # 7. 手动 timeline 事件
    r = run(["update", rid, "--timeline-event", "已联系少轩，明天三点上牌"], td)
    check("手动 timeline 事件返回 0", r.returncode == 0)
    rec = get_rec(td, rid)
    check("手动事件已追加", rec["timeline"][-1]["event"] == "已联系少轩，明天三点上牌")

    # 8. 非法 status 拒绝
    r = run(["update", rid, "--status", "不存在"], td)
    check("非法 status 被拒绝", r.returncode == 2)

    # 9. V1.0 旧数据兼容：无 memory/timeline 的记录 update 不报错
    old = {"id": "recall_old", "schema_version": "1.01", "content": "旧数据", "category": "工作待办",
           "status": "待处理", "reminder_status": "pending", "priority": "normal",
           "created_at": "2026-01-01T00:00:00+08:00", "updated_at": "2026-01-01T00:00:00+08:00"}
    data = load(td)
    data["recalls"].append(old)
    with open(os.path.join(td, "recall.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    r = run(["update", "recall_old", "--status", "进行中"], td)
    check("V1.0 旧数据 update 兼容", r.returncode == 0, r.stderr.strip()[:80])
    old2 = get_rec(td, "recall_old")
    check("旧数据 timeline 从本次更新开始记录", old2.get("timeline") and old2["timeline"][-1]["event"] == "状态更新：待处理→进行中")

print()
print("ALL PASS" if not fails else f"{len(fails)} FAILED: {fails}")
sys.exit(1 if fails else 0)
