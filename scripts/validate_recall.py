#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Hermes Recall 数据完整性检查（对应验收测试 TC5）。

用法: python validate_recall.py [recall.json 路径]
默认: 数据目录优先级 HERMES_RECALL_DIR > 本机既有部署 E:\\HermesData\\recall > ~/HermesData/recall
退出码: 0 全部通过; 1 存在问题

检查项: JSON 有效、id 唯一、created_at 存在、category/status/reminder_status 合法、
needs_reminder=true 时 remind_at 必填；Schema v2 可选字段（memory/timeline/parent_id）合法、
悬空关联检测、waiting_for 与 status 联动（切片 2）。
"""
import json
import os
import sys
from pathlib import Path


def _default_recall_dir() -> Path:
    env = os.environ.get("HERMES_RECALL_DIR")
    if env:
        return Path(env)
    legacy = Path(r"E:\HermesData\recall")
    if legacy.exists():
        return legacy
    return Path.home() / "HermesData" / "recall"


DATA_FILE = _default_recall_dir() / "recall.json"
CATEGORIES = ["工作待办", "生活日常", "想法灵感", "学习笔记", "收藏"]
STATUSES = ["待处理", "进行中", "等待反馈", "已完成", "已归档"]
REMINDER_STATUSES = ["pending", "reminded", "waiting_response", "completed", "archived", "failed", "cancelled"]
MEMORY_TYPES = ["task", "idea", "fact", "preference", "experience", "unknown"]
IMPORTANCES = ["low", "normal", "high"]


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DATA_FILE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[失败] JSON 解析错误: {e}")
        return 1
    recalls = data.get("recalls", [])
    issues = []
    ids = [r.get("id") for r in recalls]
    if len(ids) != len(set(ids)):
        issues.append("存在重复 id")
    for r in recalls:
        rid = r.get("id", "?")
        if not r.get("created_at"):
            issues.append(f"{rid} 缺 created_at")
        if r.get("category") not in CATEGORIES:
            issues.append(f"{rid} category 非法: {r.get('category')}")
        if r.get("status") not in STATUSES:
            issues.append(f"{rid} status 非法: {r.get('status')}")
        if r.get("reminder_status") not in REMINDER_STATUSES:
            issues.append(f"{rid} reminder_status 非法: {r.get('reminder_status')}")
        if r.get("needs_reminder") and not r.get("remind_at"):
            issues.append(f"{rid} needs_reminder=true 但缺 remind_at")
        # ---- Schema v2 可选字段校验（切片 2）----
        mem = r.get("memory")
        if mem is not None:
            if not isinstance(mem, dict):
                issues.append(f"{rid} memory 必须是对象")
            else:
                mt = mem.get("memory_type")
                if mt and mt not in MEMORY_TYPES:
                    issues.append(f"{rid} memory.memory_type 非法: {mt}")
                imp = mem.get("importance")
                if imp and imp not in IMPORTANCES:
                    issues.append(f"{rid} memory.importance 非法: {imp}")
                ent = mem.get("entities")
                if ent is not None:
                    if not isinstance(ent, list) or any(not isinstance(e, str) or not e.strip() for e in ent):
                        issues.append(f"{rid} memory.entities 必须是非空字符串数组")
                rel = mem.get("related_ids")
                if rel is not None:
                    if not isinstance(rel, list) or any(not isinstance(x, str) for x in rel):
                        issues.append(f"{rid} memory.related_ids 必须是字符串数组")
                    else:
                        for x in rel:
                            if x not in ids:
                                issues.append(f"{rid} memory.related_ids 悬空: {x}")
                wf = mem.get("waiting_for")
                if wf and r.get("status") != "等待反馈":
                    issues.append(f"{rid} waiting_for 非空但 status 不是等待反馈: {wf}")
        # 悬空 parent_id
        pid = r.get("parent_id")
        if pid and pid not in ids:
            issues.append(f"{rid} parent_id 悬空: {pid}")
        # timeline 结构
        tl = r.get("timeline")
        if tl is not None:
            if not isinstance(tl, list) or not tl:
                issues.append(f"{rid} timeline 必须是非空数组")
            else:
                for i, ev in enumerate(tl):
                    if not isinstance(ev, dict) or not ev.get("date") or not isinstance(ev.get("event"), str):
                        issues.append(f"{rid} timeline[{i}] 需含 date 与 event")
    checks = [
        ("JSON 格式", True),
        ("id 唯一性", len(ids) == len(set(ids))),
        ("created_at 存在", all(r.get("created_at") for r in recalls)),
        ("category 合法", all(r.get("category") in CATEGORIES for r in recalls)),
        ("status 合法（五状态）", all(r.get("status") in STATUSES for r in recalls)),
        ("reminder_status 合法（七状态）", all(r.get("reminder_status") in REMINDER_STATUSES for r in recalls)),
        ("提醒字段一致性", all(not (r.get("needs_reminder") and not r.get("remind_at")) for r in recalls)),
        ("memory 结构合法", all(
            not isinstance(r.get("memory"), dict)
            or (r["memory"].get("memory_type") in (None,) + tuple(MEMORY_TYPES)
                and r["memory"].get("importance") in (None,) + tuple(IMPORTANCES))
            for r in recalls)),
        ("无悬空关联（related_ids/parent_id）", all(
            (not (r.get("memory") or {}).get("related_ids") or all(x in ids for x in r["memory"]["related_ids"]))
            and (not r.get("parent_id") or r["parent_id"] in ids)
            for r in recalls)),
        ("waiting_for 联动", all(
            not (r.get("memory") or {}).get("waiting_for") or r.get("status") == "等待反馈"
            for r in recalls)),
        ("timeline 结构合法", all(
            not r.get("timeline") or (isinstance(r["timeline"], list) and r["timeline"]
                                      and all(isinstance(e, dict) and e.get("date") and isinstance(e.get("event"), str)
                                              for e in r["timeline"]))
            for r in recalls)),
    ]
    print(f"总记录: {len(recalls)}")
    for label, ok in checks:
        print(f"  {label}: {'通过' if ok else '失败'}")
    if issues:
        print("问题项:")
        for i in issues:
            print(f"  - {i}")
        return 1
    print("问题项: 无 ✓ 全绿")
    return 0


if __name__ == "__main__":
    sys.exit(main())
