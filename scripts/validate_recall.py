#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Hermes Recall 数据完整性检查（对应验收测试 TC5）。

用法: python validate_recall.py [recall.json 路径]
默认: 数据目录优先级 HERMES_RECALL_DIR > 本机既有部署 E:\\HermesData\\recall > ~/HermesData/recall
退出码: 0 全部通过; 1 存在问题

检查项: JSON 有效、id 唯一、created_at 存在、category/status/reminder_status 合法、
needs_reminder=true 时 remind_at 必填。
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
STATUSES = ["待处理", "进行中", "已完成", "已归档"]
REMINDER_STATUSES = ["pending", "sent", "failed", "cancelled"]


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
    checks = [
        ("JSON 格式", True),
        ("id 唯一性", len(ids) == len(set(ids))),
        ("created_at 存在", all(r.get("created_at") for r in recalls)),
        ("category 合法", all(r.get("category") in CATEGORIES for r in recalls)),
        ("status 合法", all(r.get("status") in STATUSES for r in recalls)),
        ("reminder_status 合法", all(r.get("reminder_status") in REMINDER_STATUSES for r in recalls)),
        ("提醒字段一致性", all(not (r.get("needs_reminder") and not r.get("remind_at")) for r in recalls)),
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
