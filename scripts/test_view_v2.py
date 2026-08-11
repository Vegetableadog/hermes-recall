# -*- coding: utf-8 -*-
"""切片 4 测试：Markdown View/search/stats 新字段展示（时间线/父子链/悬空标记）。

运行：python scripts/test_view_v2.py（使用临时数据目录）
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
    return subprocess.run([sys.executable, SCRIPT] + args, capture_output=True, text=True, encoding="utf-8", env=env)


with tempfile.TemporaryDirectory(prefix="recall-view-") as td:
    # 构造 v2 数据：结构化记录（memory/timeline/parent_id）+ 悬空关联
    data = {"version": "2.0", "recalls": [
        {"id": "r1", "schema_version": "2.0", "content": "确认上牌进度", "category": "工作待办",
         "status": "等待反馈", "reminder_status": "pending", "priority": "high",
         "created_at": "2026-08-01T09:00:00+08:00", "updated_at": "2026-08-12T09:00:00+08:00",
         "tags": ["上牌"], "needs_reminder": False, "remind_at": None, "source": "user", "metadata": {},
         "memory": {"memory_type": "task", "importance": "high", "entities": ["邹总", "少轩"],
                    "related_ids": ["ghost"], "waiting_for": "邹总"},
         "timeline": [{"date": "2026-08-01T09:00:00+08:00", "event": "创建回响"},
                      {"date": "2026-08-12T09:00:00+08:00", "event": "状态更新：待处理→等待反馈（等待对象：邹总）"}]},
        {"id": "r2", "schema_version": "2.0", "content": "跟进上牌完成结果", "category": "工作待办",
         "status": "待处理", "reminder_status": "pending", "priority": "normal",
         "created_at": "2026-08-12T10:00:00+08:00", "updated_at": "2026-08-12T10:00:00+08:00",
         "tags": [], "needs_reminder": False, "remind_at": None, "source": "user", "metadata": {},
         "parent_id": "r1", "timeline": [{"date": "2026-08-12T10:00:00+08:00", "event": "创建回响"}]},
    ]}
    with open(os.path.join(td, "recall.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

    # 1. view：结构化摘要与时间线
    r = run(["view", "--output", "test_view.md"], td)
    check("view 返回 0", r.returncode == 0, r.stderr.strip()[:80])
    view_path = os.path.join(td, "test_view.md")
    v = open(view_path, encoding="utf-8").read()
    check("汇总含等待反馈统计", "等待反馈: 1" in v)
    check("memory 摘要：类型", "📌task" in v)
    check("memory 摘要：重要度", "🔥high" in v)
    check("memory 摘要：实体", "@邹总/少轩" in v)
    check("memory 摘要：等待对象", "⏳等邹总" in v)
    check("悬空关联标记", "⚠悬空:ghost" in v)
    check("父子链标记", "⬆r1" in v)
    check("时间线视图", "🕐" in v and "创建回响" in v and "状态更新：待处理→等待反馈" in v)

    # 2. search 按实体命中
    r = run(["search", "邹总"], td)
    check("search 按实体命中", r.returncode == 0 and "r1" in r.stdout and "确认上牌进度" in r.stdout, r.stdout[:60])

    # 3. stats 记忆类型统计
    r = run(["stats"], td)
    check("stats 记忆类型统计", "记忆类型" in r.stdout and "task: 1" in r.stdout, r.stdout[-120:])

    # 4. get 详情 JSON 含新字段
    r = run(["get", "r1"], td)
    check("get 返回 0", r.returncode == 0)
    got = json.loads(r.stdout)
    check("get 含 memory/timeline/parent 信息", got["memory"]["waiting_for"] == "邹总" and len(got["timeline"]) == 2)

print()
print("ALL PASS" if not fails else f"{len(fails)} FAILED: {fails}")
sys.exit(1 if fails else 0)
