# -*- coding: utf-8 -*-
"""切片 2 测试：Validator 扩展（memory/timeline/五状态/七状态/悬空关联/waiting_for 联动）。

运行：python scripts/test_validate_v2.py（使用临时数据文件，不触碰生产数据）
"""
import json
import os
import subprocess
import sys
import tempfile

VSCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "validate_recall.py")
fails = []


def check(name, ok, detail=""):
    print(("PASS" if ok else "FAIL"), "-", name, detail)
    if not ok:
        fails.append(name)


def run_validate(data):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
        tmp = f.name
    try:
        r = subprocess.run([sys.executable, VSCRIPT, tmp], capture_output=True, text=True, encoding="utf-8")
        return r
    finally:
        os.unlink(tmp)


def rec(rid, **extra):
    base = {
        "id": rid, "schema_version": "1.01", "content": "测试", "category": "工作待办",
        "status": "待处理", "reminder_status": "pending", "priority": "normal",
        "created_at": "2026-08-12T00:00:00+08:00", "updated_at": "2026-08-12T00:00:00+08:00",
        "tags": [], "needs_reminder": False, "remind_at": None, "source": "user", "metadata": {},
    }
    base.update(extra)
    return base


# 1. V1.0 旧数据（无新字段）→ 通过
data = {"version": "1.01", "recalls": [rec("r1"), rec("r2")]}
r = run_validate(data)
check("V1.0 旧数据通过", r.returncode == 0, r.stdout.strip().splitlines()[-1][:40])

# 2. 合法 v2 数据（memory 全字段 + timeline + parent_id + 等待反馈）→ 通过
data = {"version": "2.0", "recalls": [
    rec("r1", memory={"memory_type": "task", "importance": "high",
                      "entities": ["邹总"], "related_ids": ["r2"], "waiting_for": "邹总"},
        status="等待反馈", timeline=[{"date": "2026-08-12T00:00:00+08:00", "event": "创建回响"},
                                     {"date": "2026-08-12T01:00:00+08:00", "event": "状态更新：待处理→等待反馈（等待对象：邹总）"}]),
    rec("r2", parent_id="r1", timeline=[{"date": "2026-08-12T00:00:00+08:00", "event": "创建回响"}]),
]}
r = run_validate(data)
check("合法 v2 数据通过", r.returncode == 0, r.stdout.strip().splitlines()[-1][:40])

# 3. 悬空 related_ids → 报告 + exit 1
data = {"version": "2.0", "recalls": [rec("r1", memory={"related_ids": ["ghost"]})]}
r = run_validate(data)
check("悬空 related_ids 被报告", r.returncode == 1 and "related_ids 悬空" in r.stdout, r.stdout.strip()[-80:])

# 4. 悬空 parent_id → 报告
data = {"version": "2.0", "recalls": [rec("r1", parent_id="ghost")]}
r = run_validate(data)
check("悬空 parent_id 被报告", r.returncode == 1 and "parent_id 悬空" in r.stdout)

# 5. waiting_for 与 status 不匹配 → 报告
data = {"version": "2.0", "recalls": [rec("r1", memory={"waiting_for": "邹总"}, status="进行中")]}
r = run_validate(data)
check("waiting_for 不匹配被报告", r.returncode == 1 and "waiting_for 非空但 status" in r.stdout)

# 6. 非法 memory_type → 报告
data = {"version": "2.0", "recalls": [rec("r1", memory={"memory_type": "外星"})]}
r = run_validate(data)
check("非法 memory_type 被报告", r.returncode == 1 and "memory_type 非法" in r.stdout)

# 7. 非法 timeline 结构（缺 event）→ 报告
data = {"version": "2.0", "recalls": [rec("r1", timeline=[{"date": "2026-08-12T00:00:00+08:00"}])]}
r = run_validate(data)
check("timeline 缺 event 被报告", r.returncode == 1 and "timeline[0] 需含 date 与 event" in r.stdout)

# 8. 等待反馈状态无 waiting_for → 合法（允许未知来源）
data = {"version": "2.0", "recalls": [rec("r1", status="等待反馈")]}
r = run_validate(data)
check("等待反馈无 waiting_for 合法", r.returncode == 0)

print()
print("ALL PASS" if not fails else f"{len(fails)} FAILED: {fails}")
sys.exit(1 if fails else 0)
