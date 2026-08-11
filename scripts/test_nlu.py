# -*- coding: utf-8 -*-
"""切片 5 测试：V11-NLU——回响式自然语言 Intent 解析 + talk 端到端 + 确认门。

运行：python scripts/test_nlu.py（临时数据目录）
"""
import json
import os
import subprocess
import sys
import tempfile

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recall.py")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from recall import parse_intent  # noqa: E402

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


# ============ 1. parse_intent 用例（25 条） ============
NLU = [
    # add 普通
    ("记一下明天见邹总", "add", lambda a: a.content[0].startswith("明天见邹总") and a.remind_at is not None),
    ("记录：买牛奶", "add", lambda a: "买牛奶" in a.content[0]),
    ("添加待办：交报表", "add", lambda a: "交报表" in a.content[0]),
    ("收藏这篇文章", "add", lambda a: a.content[0] == "这篇文章"),
    ("备注：少轩电话13800000000", "add", lambda a: "少轩电话" in a.content[0]),
    # remind 带提醒
    ("提醒我明天9点交报表", "add", lambda a: a.remind_at is not None and "交报表" in a.content[0] and "T09:00" in a.remind_at),
    ("提醒我后天开会", "add", lambda a: a.remind_at is not None),
    ("记得下周一给客户打电话", "add", lambda a: a.remind_at is not None),
    ("明天下午3点去车管所", "add", lambda a: a.remind_at is not None and "T15:00" in a.remind_at),
    ("提醒我", None, None),
    # search
    ("找上牌的记录", "search", lambda a: "上牌" in a.keyword[0]),
    ("搜索德银还款", "search", lambda a: "德银还款" in a.keyword[0]),
    ("看看有什么待办", "search", lambda a: True),
    ("有没有关于报废车的", "search", lambda a: "报废车" in a.keyword[0]),
    ("什么时候交报表", "search", lambda a: "交报表" in a.keyword[0]),
    # list
    ("列出所有待办", "list", lambda a: True),
    ("全部回响", "list", lambda a: True),
    ("待办清单", "list", lambda a: True),
    # done
    ("完成 recall_001", "done", lambda a: a.id == "recall_001"),
    ("搞定 r2", "done", lambda a: a.id == "r2"),
    ("做完了 recall_003", "done", lambda a: a.id == "recall_003"),
    # delete
    ("删除 recall_004", "delete", lambda a: a.id == "recall_004"),
    ("删掉 r1", "delete", lambda a: a.id == "r1"),
    ("移除 recall_005", "delete", lambda a: a.id == "recall_005"),
    # update_status
    ("把 recall_001 改为进行中", "update_status", lambda a: a.id == "recall_001" and a.status == "进行中"),
    ("将 r2 标记为已完成", "update_status", lambda a: a.status == "已完成"),
    ("把 recall_003 归档", "update_status", lambda a: a.status == "已归档"),
    # waiting
    ("还在等邹总回复", "waiting", lambda a: a.waiting_for == "邹总" and a.id is None),
    ("等少轩的消息", "waiting", lambda a: a.waiting_for.startswith("少轩")),
    ("recall_001 等邹总回复", "waiting", lambda a: a.id == "recall_001" and a.waiting_for == "邹总"),
    # 未识别
    ("你好", None, None),
]

nlu_pass = 0
for text, want_intent, param_check in NLU:
    intent, a = parse_intent(text)
    if intent == want_intent and (param_check is None or (a is not None and param_check(a))):
        nlu_pass += 1
    else:
        check(f"NLU: {text} → {want_intent}", False, f"实际 intent={intent}")

check("V11-NLU parse_intent 30 条全对", nlu_pass == len(NLU), f"{nlu_pass}/{len(NLU)}")


# ============ 2. talk 端到端（临时目录） ============
with tempfile.TemporaryDirectory(prefix="recall-nlu-") as td:
    # add
    r = run(["talk", "记一下", "测试回响"], td)
    check("talk 记一下 → add 成功", r.returncode == 0 and "已记录" in r.stdout, r.stdout[:40])
    data = json.load(open(os.path.join(td, "recall.json"), encoding="utf-8"))
    rid = data["recalls"][0]["id"]
    # remind
    r = run(["talk", "提醒我", "明天9点", "测试提醒"], td)
    check("talk 提醒我 → add+remind_at", r.returncode == 0)
    data = json.load(open(os.path.join(td, "recall.json"), encoding="utf-8"))
    rec2 = data["recalls"][1]
    check("remind_at 已写入", rec2.get("remind_at") is not None and "T09:00" in rec2["remind_at"])
    # waiting 无 id → 零写入
    r = run(["talk", "还在等", "邹总回复"], td)
    check("waiting 无 id → 拒绝零写入", r.returncode == 2 and "需指定" in r.stderr, r.stderr[:40])
    # 完成
    r = run(["talk", "完成", rid], td)
    check("talk 完成 → done", r.returncode == 0 and "已标记完成" in r.stdout)
    # 删除确认门：非交互无 --yes → 拒绝（Windows isatty 对 DEVNULL 返回 True，走 EOFError 分支同样安全）
    r = run(["talk", "删除", rid], td)
    check("删除确认门（拒绝+零写入）", r.returncode == 1 and ("需确认" in r.stderr or "已取消" in r.stderr), r.stderr[:60])
    data = json.load(open(os.path.join(td, "recall.json"), encoding="utf-8"))
    check("确认门拒绝后零删除", any(x["id"] == rid for x in data["recalls"]))
    # 删除 --yes → 成功
    r = run(["talk", "--yes", "删除", rid], td)
    check("talk --yes 删除成功", r.returncode == 0 and "已删除" in r.stdout)
    data = json.load(open(os.path.join(td, "recall.json"), encoding="utf-8"))
    check("删除生效", not any(x["id"] == rid for x in data["recalls"]))
    # 未识别
    r = run(["talk", "你好"], td)
    check("talk 未识别 → 2 零写入", r.returncode == 2 and "未能理解" in r.stderr)

print()
print("ALL PASS" if not fails else f"{len(fails)} FAILED: {fails}")
sys.exit(1 if fails else 0)
