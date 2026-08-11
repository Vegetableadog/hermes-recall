# -*- coding: utf-8 -*-
"""切片 3 测试：Migration v1→v2（备份/预检/迁移/校验/恢复演练）。

运行：python scripts/test_migrate_v2.py（使用临时数据目录，不触碰生产数据）
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recall.py")
fails = []


def check(name, ok, detail=""):
    print(("PASS" if ok else "FAIL"), "-", name, detail)
    if not ok:
        fails.append(name)


def run(args, env_dir):
    env = dict(os.environ)
    env["HERMES_RECALL_DIR"] = env_dir
    return subprocess.run([sys.executable, SCRIPT] + args, capture_output=True, text=True, encoding="utf-8", env=env)


def load(env_dir):
    with open(os.path.join(env_dir, "recall.json"), encoding="utf-8") as f:
        return json.load(f)


def rec(rid, rstatus):
    return {"id": rid, "schema_version": "1.01", "content": f"旧记录 {rid}", "category": "工作待办",
            "status": "待处理", "reminder_status": rstatus, "priority": "normal",
            "created_at": "2026-01-01T00:00:00+08:00", "updated_at": "2026-01-01T00:00:00+08:00",
            "tags": [], "needs_reminder": rstatus in ("pending", "sent"),
            "remind_at": "2026-01-02T00:00:00+08:00" if rstatus in ("pending", "sent") else None,
            "source": "user", "metadata": {}}


with tempfile.TemporaryDirectory(prefix="recall-mig-") as td:
    # 构造 V1.0 数据：4 种 reminder_status，无 memory/timeline
    data = {"version": "1.01", "recalls": [rec("r1", "pending"), rec("r2", "sent"), rec("r3", "failed"), rec("r4", "cancelled")]}
    with open(os.path.join(td, "recall.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    with open(os.path.join(td, "recall_history.json"), "w", encoding="utf-8") as f:
        json.dump({"version": "1.01", "events": []}, f, ensure_ascii=False)

    # 1. 迁移
    r = run(["upgrade"], td)
    check("迁移返回 0", r.returncode == 0, r.stderr.strip()[:100])
    check("迁移输出含备份路径", "备份" in r.stdout)
    check("迁移后校验通过", "迁移后校验通过 ✓" in r.stdout, r.stdout[-60:])

    data = load(td)
    by_id = {x["id"]: x for x in data["recalls"]}
    check("顶层 version=2.0", data.get("version") == "2.0")
    check("schema_version=2.0", all(x.get("schema_version") == "2.0" for x in data["recalls"]))
    check("sent→reminded", by_id["r2"]["reminder_status"] == "reminded")
    check("pending 保留", by_id["r1"]["reminder_status"] == "pending")
    check("failed 保留", by_id["r3"]["reminder_status"] == "failed")
    check("cancelled 保留", by_id["r4"]["reminder_status"] == "cancelled")
    check("缺失 memory 不补", all("memory" not in x for x in data["recalls"]))
    check("缺失 timeline 不补", all("timeline" not in x for x in data["recalls"]))
    check("content 未被修改", by_id["r1"]["content"] == "旧记录 r1")

    # 备份文件存在
    backups = [f for f in os.listdir(td) if f.startswith("recall.backup-")]
    hist_backups = [f for f in os.listdir(td) if f.startswith("recall_history.backup-")]
    check("recall 备份已生成", len(backups) == 1, str(backups))
    check("history 备份已生成", len(hist_backups) == 1, str(hist_backups))
    backup_path = os.path.join(td, backups[0])

    # 2. 恢复演练：restore 备份 → 数据回 V1.0
    r = run(["restore", backup_path], td)
    check("restore 返回 0", r.returncode == 0, r.stderr.strip()[:100])
    data = load(td)
    check("恢复后 version=1.01", data.get("version") == "1.01")
    check("恢复后 sent 回来", [x for x in data["recalls"] if x["id"] == "r2"][0]["reminder_status"] == "sent")
    check("恢复后 schema_version=1.01", [x for x in data["recalls"] if x["id"] == "r1"][0]["schema_version"] == "1.01")

    # 3. 恢复后再迁移（幂等性/可重复）
    r = run(["upgrade"], td)
    check("恢复后再次迁移返回 0", r.returncode == 0)
    data = load(td)
    check("再次迁移后 version=2.0", data.get("version") == "2.0")
    check("再次迁移后 sent→reminded", [x for x in data["recalls"] if x["id"] == "r2"][0]["reminder_status"] == "reminded")

    # 4. 已最新时再迁移：无变更
    r = run(["upgrade"], td)
    check("第三次迁移（已最新）返回 0", r.returncode == 0)
    check("已最新时 0 条变更", "0 条记录已升级" in r.stdout, r.stdout[:60])

    # 5. restore 不存在的备份 → 报错
    r = run(["restore", os.path.join(td, "nope.json")], td)
    check("restore 不存在的备份返回 1", r.returncode == 1)

print()
print("ALL PASS" if not fails else f"{len(fails)} FAILED: {fails}")
sys.exit(1 if fails else 0)
