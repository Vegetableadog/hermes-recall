#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Hermes Recall（回响）—— 本地智能备忘录核心模块 v2。

架构: JSON 为唯一事实来源, Markdown 仅作展示层, 统一 Scheduler 负责提醒。

数据目录: C:\\Users\\Administrator\\hermes-recall\\
  recall.json          主数据（Single Source of Truth）
  recall_history.json  历史记录（创建/修改/完成/删除/提醒）
  recall_view.md       Markdown 视图（自动生成，禁止手改）
  config.json          配置（飞书 webhook 等）

用法:
  python recall.py add <内容> [--category 分类] [--tags a,b] [--remind-at ISO] [--priority low|normal|high] [--source xxx]
  python recall.py list [--category C] [--status S] [--remind] [--all]
  python recall.py get <id>
  python recall.py search <关键词>
  python recall.py update <id> [--content ...] [--category C] [--tags a,b] [--status 待处理|进行中|已完成|已归档] [--priority p] [--remind-at ISO] [--needs-reminder true|false]
  python recall.py done <id>
  python recall.py delete <id>
  python recall.py view
  python recall.py due
  python recall.py send-reminders [--dry-run] [--quiet]
  python recall.py migrate [--dry-run]
  python recall.py stats
"""
import argparse
import json
import os
import secrets
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

# 数据目录解析优先级：
#   1. 环境变量 HERMES_RECALL_DIR（显式指定，推荐）
#   2. 本机既有部署目录 E:\HermesData\recall（兼容早期版本，仅 Windows）
#   3. 通用默认 ~/HermesData/recall（新用户）
def _default_recall_dir() -> Path:
    env = os.environ.get("HERMES_RECALL_DIR")
    if env:
        return Path(env)
    legacy = Path(r"E:\HermesData\recall")
    if legacy.exists():
        return legacy
    return Path.home() / "HermesData" / "recall"


RECALL_DIR = _default_recall_dir()
RECALL_DIR.mkdir(parents=True, exist_ok=True)  # 首次使用自动创建数据目录
DATA_FILE = RECALL_DIR / "recall.json"
HISTORY_FILE = RECALL_DIR / "recall_history.json"
VIEW_FILE = RECALL_DIR / "recall_view.md"
CONFIG_FILE = RECALL_DIR / "config.json"

SCHEMA_VERSION = "2.0"  # Schema v2：V1.1 结构化记忆（产品/Skill/Schema 版本治理见切片 7）

CATEGORIES = ["工作待办", "生活日常", "想法灵感", "学习笔记", "收藏"]
STATUSES = ["待处理", "进行中", "等待反馈", "已完成", "已归档"]
PRIORITIES = ["low", "normal", "high"]
REMINDER_STATUSES = ["pending", "reminded", "waiting_response", "completed", "archived", "failed", "cancelled"]
MEMORY_TYPES = ["task", "idea", "fact", "preference", "experience", "unknown"]
IMPORTANCES = ["low", "normal", "high"]

# 无 AI 参数时的启发式兜底分类（正常流程由 Hermes 语义判断后传入）
_KEYWORD_CATEGORY = [
    (["开会", "会议", "项目", "报告", "截止", "提交", "客户", "面试", "方案", "周报", "任务", "评审", "交付", "汇报"], "工作待办"),
    (["买", "购物", "超市", "家务", "体检", "理发", "快递", "缴费", "洗衣"], "生活日常"),
    (["想法", "灵感", "创意", "创业", "随想", "思路", "点子"], "想法灵感"),
    (["学习", "研究", "教程", "笔记", "阅读", "课程", "技术", "资料", "文档", "论文", "代码"], "学习笔记"),
    (["收藏", "文章", "链接", "资源", "推荐", "书单", "影单"], "收藏"),
]


# ---------- 基础读写 ----------

def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _default_data() -> dict:
    return {"version": SCHEMA_VERSION, "recalls": []}


def load_data() -> dict:
    if not DATA_FILE.exists():
        return _default_data()
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def save_data(data: dict) -> None:
    DATA_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_history() -> dict:
    if not HISTORY_FILE.exists():
        return {"events": []}
    return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))


def log_history(event: str, recall_id: str, detail: dict) -> None:
    hist = load_history()
    hist.setdefault("events", []).append({
        "event": event, "recall_id": recall_id,
        "at": now_iso(), "detail": detail,
    })
    HISTORY_FILE.write_text(
        json.dumps(hist, ensure_ascii=False, indent=2), encoding="utf-8")


def next_id(data: dict) -> str:
    """生成唯一 id：recall_YYYYMMDD_随机6位hex（如 recall_20260809_a83f91）。

    随机后缀天然唯一（循环查重兜底），未来 SQLite 迁移直接作为 primary key。
    已有旧格式 id（recall_YYYYMMDD_NN 序号）保持不变，不在此生成。
    """
    today = datetime.now().strftime("%Y%m%d")
    existing = {r.get("id") for r in data.get("recalls", [])}
    existing |= {ev.get("recall_id") for ev in load_history().get("events", [])}
    while True:
        rid = f"recall_{today}_{secrets.token_hex(3)}"
        if rid not in existing:
            return rid


def find_recall(data: dict, rid: str):
    for r in data.get("recalls", []):
        if r["id"] == rid:
            return r
    return None


def guess_category(content: str) -> str:
    for kws, cat in _KEYWORD_CATEGORY:
        if any(k in content for k in kws):
            return cat
    return "想法灵感"


def parse_remind_at(s: str):
    """解析 ISO 时间字符串为 datetime，失败返回 None。"""
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


# ---------- 子命令 ----------

def cmd_add(args) -> int:
    data = load_data()
    content = " ".join(args.content)
    rid = next_id(data)
    category = args.category or guess_category(content)
    if category not in CATEGORIES:
        print(f"[错误] 分类必须为: {'/'.join(CATEGORIES)}", file=sys.stderr)
        return 2
    priority = args.priority if args.priority else "normal"
    if priority not in PRIORITIES:
        print(f"[错误] priority 必须为: {'/'.join(PRIORITIES)}", file=sys.stderr)
        return 2

    needs_reminder = False
    remind_at = None
    if args.remind_at:
        dt = parse_remind_at(args.remind_at)
        if dt is None:
            print(f"[错误] remind_at 需为 ISO 8601 格式，如 2026-08-10T09:00:00+08:00", file=sys.stderr)
            return 2
        needs_reminder = True
        remind_at = args.remind_at

    rec = {
        "id": rid,
        "schema_version": SCHEMA_VERSION,
        "content": content,
        "category": category,
        "tags": [t.strip() for t in (args.tags.split(",") if args.tags else [])],
        "needs_reminder": needs_reminder,
        "remind_at": remind_at,
        "reminder_status": "pending",
        "status": "待处理",
        "priority": priority,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "source": args.source or "user",
        "metadata": {},
        "timeline": [{"date": now_iso(), "event": "创建回响"}],
    }
    if args.parent_id:
        rec["parent_id"] = args.parent_id
    if args.memory_type or args.importance or args.entities or args.related_ids:
        rec["memory"] = {
            "memory_type": args.memory_type or "unknown",
            "importance": args.importance or "normal",
            "entities": [e.strip() for e in args.entities.split(",") if e.strip()] if args.entities else [],
            "related_ids": [i.strip() for i in args.related_ids.split(",") if i.strip()] if args.related_ids else [],
        }
    data.setdefault("recalls", []).append(rec)
    save_data(data)
    log_history("create", rid, {"content": content, "category": category})
    print(f"[回响] 已记录 {rid} [{category}] {content}")
    if needs_reminder:
        print(f"       提醒将于 {remind_at} 发送")
    return 0


def _display_width(text: str) -> int:
    """近似计算终端显示宽度：中文/全角字符按 2 列计。"""
    import unicodedata
    return sum(2 if unicodedata.east_asian_width(ch) in "WFA" else 1 for ch in str(text))


def _fit_cell(value, width: int) -> str:
    """按终端列宽截断并补空格，避免中文表格错位。"""
    text = str(value or "")
    if _display_width(text) > width:
        suffix = "…"
        while _display_width(text + suffix) > width:
            text = text[:-1]
        text += suffix
    return text + " " * max(0, width - _display_width(text))


def _print_table(rows, headers, widths) -> None:
    sep = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    print(sep)
    print("| " + " | ".join(_fit_cell(h, w) for h, w in zip(headers, widths)) + " |")
    print(sep)
    for row in rows:
        print("| " + " | ".join(_fit_cell(v, w) for v, w in zip(row, widths)) + " |")
    print(sep)


def cmd_list(args) -> int:
    data = load_data()
    recalls = data.get("recalls", [])
    if not recalls:
        print("[回响] 暂无记录")
        return 0
    if not args.all:
        recalls = [r for r in recalls if r.get("status") != "已归档"]
    if args.category:
        recalls = [r for r in recalls if r.get("category") == args.category]
    if args.status:
        recalls = [r for r in recalls if r.get("status") == args.status]
    if args.remind:
        recalls = [r for r in recalls if r.get("needs_reminder")]
    if not recalls:
        print("[回响] 没有符合条件的记录")
        return 0
    recalls.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    flags = {"待处理": "○", "进行中": "◐", "等待反馈": "◑", "已完成": "●", "已归档": "×"}
    rows = []
    for r in recalls:
        remind = r.get("remind_at", "")[:16].replace("T", " ") if r.get("needs_reminder") else "—"
        tags = " ".join("#" + t for t in r.get("tags", [])) or "—"
        rows.append([
            flags.get(r.get("status"), "○"),
            r.get("id", "").replace("recall_", "")[:15],
            r.get("category", ""),
            r.get("priority", "normal"),
            r.get("content", ""),
            remind,
            tags,
        ])
    _print_table(rows, ["状态", "编号", "分类", "优先级", "内容", "提醒", "标签"],
                 [4, 15, 8, 6, 42, 16, 24])
    print(f"共 {len(recalls)} 条（○待处理 ◐进行中 ●已完成；默认隐藏已归档）")
    return 0


def cmd_get(args) -> int:
    data = load_data()
    r = find_recall(data, args.id)
    if r is None:
        print(f"[回响] 未找到 {args.id}", file=sys.stderr)
        return 1
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0


def cmd_search(args) -> int:
    data = load_data()
    kw = " ".join(args.keyword)
    hits = [r for r in data.get("recalls", [])
            if kw in r.get("content", "") or any(kw in t for t in r.get("tags", []))
            or kw in " ".join((r.get("memory") or {}).get("entities", []))]
    if not hits:
        print(f"[回响] 未找到包含「{kw}」的记录")
        return 0
    print(f"[回响] 找到 {len(hits)} 条:")
    for r in hits:
        remind = f" ⏰{r['remind_at']}" if r.get("needs_reminder") else ""
        print(f"  · [{r['id']}] ({r.get('category')}) {r.get('content')}{remind}")
    return 0


def _append_timeline(r: dict, event: str) -> None:
    r.setdefault("timeline", []).append({"date": now_iso(), "event": event})


def cmd_update(args) -> int:
    data = load_data()
    r = find_recall(data, args.id)
    if r is None:
        print(f"[回响] 未找到 {args.id}", file=sys.stderr)
        return 1
    before = dict(r)
    if args.content:
        r["content"] = " ".join(args.content)
    if args.category:
        if args.category not in CATEGORIES:
            print(f"[错误] 分类必须为: {'/'.join(CATEGORIES)}", file=sys.stderr)
            return 2
        r["category"] = args.category
    if args.tags:
        r["tags"] = [t.strip() for t in args.tags.split(",")]
    if args.status:
        if args.status not in STATUSES:
            print(f"[错误] status 必须为: {'/'.join(STATUSES)}", file=sys.stderr)
            return 2
        before_status = r.get("status")
        if args.status != before_status:
            _append_timeline(r, f"状态更新：{before_status}→{args.status}")
            # waiting_for 联动：离开等待反馈时先固化到 timeline 再清空
            mem = r.get("memory") or {}
            if before_status == "等待反馈" and mem.get("waiting_for"):
                wf = mem["waiting_for"]
                r["timeline"][-1]["event"] += f"（等待对象：{wf}）"
                mem.pop("waiting_for", None)
        r["status"] = args.status
    if args.priority:
        if args.priority not in PRIORITIES:
            print(f"[错误] priority 必须为: {'/'.join(PRIORITIES)}", file=sys.stderr)
            return 2
        r["priority"] = args.priority
    if args.remind_at:
        if parse_remind_at(args.remind_at) is None:
            print(f"[错误] remind_at 需为 ISO 8601 格式", file=sys.stderr)
            return 2
        r["remind_at"] = args.remind_at
        r["needs_reminder"] = True
        if not r.get("reminder_status"):
            r["reminder_status"] = "pending"
    if args.needs_reminder is not None:
        r["needs_reminder"] = args.needs_reminder.lower() == "true"
    if args.parent_id is not None:
        r["parent_id"] = args.parent_id or None
    if args.memory_type or args.importance or args.entities or args.related_ids:
        mem = r.setdefault("memory", {})
        if args.memory_type:
            mem["memory_type"] = args.memory_type
        if args.importance:
            mem["importance"] = args.importance
        if args.entities is not None:
            mem["entities"] = [e.strip() for e in args.entities.split(",") if e.strip()]
        if args.related_ids is not None:
            mem["related_ids"] = [i.strip() for i in args.related_ids.split(",") if i.strip()]
    if args.waiting_for:
        # 显式设置等待对象：自动进入等待反馈状态并写入
        if r.get("status") != "等待反馈":
            _append_timeline(r, f"状态更新：{r.get('status')}→等待反馈")
            r["status"] = "等待反馈"
        r.setdefault("memory", {})["waiting_for"] = args.waiting_for
    if args.timeline_event:
        _append_timeline(r, args.timeline_event)
    if args.reminder_status:
        if args.reminder_status != r.get("reminder_status"):
            _append_timeline(r, f"提醒状态：{r.get('reminder_status')}→{args.reminder_status}")
        r["reminder_status"] = args.reminder_status
    r["updated_at"] = now_iso()  # 只更新 updated_at；id / created_at 不可修改
    save_data(data)
    log_history("update", args.id, {"before": before, "after": dict(r)})
    print(f"[回响] 已更新 {args.id}")
    return 0


def cmd_done(args) -> int:
    data = load_data()
    r = find_recall(data, args.id)
    if r is None:
        print(f"[回响] 未找到 {args.id}", file=sys.stderr)
        return 1
    before = r.get("status")
    if before != "已完成":
        _append_timeline(r, f"状态更新：{before}→已完成")
        mem = r.get("memory") or {}
        if mem.get("waiting_for"):
            wf = mem["waiting_for"]
            r["timeline"][-1]["event"] += f"（等待对象：{wf}）"
            mem.pop("waiting_for", None)
    r["status"] = "已完成"
    r["updated_at"] = now_iso()
    save_data(data)
    log_history("done", args.id, {"before": before, "after": "已完成"})
    print(f"[回响] {args.id} 已标记完成")
    return 0


def cmd_delete(args) -> int:
    data = load_data()
    r = find_recall(data, args.id)
    if r is None:
        print(f"[回响] 未找到 {args.id}", file=sys.stderr)
        return 1
    data["recalls"] = [x for x in data["recalls"] if x["id"] != args.id]
    save_data(data)
    log_history("delete", args.id, {"content": r.get("content")})
    print(f"[回响] 已删除 {args.id}")
    return 0


def cmd_view(args) -> int:
    data = load_data()
    target = RECALL_DIR / (args.output if args.output else "recall_view.md")
    recalls = [r for r in data.get("recalls", []) if r.get("status") != "已归档"]
    if not recalls:
        target.write_text("# Hermes Recall\n\n（暂无记录）\n", encoding="utf-8")
        print(f"[回响] 视图已生成（空）: {target}")
        return 0

    lines = [
        "# Hermes Recall",
        f"> 由 recall.json 自动生成 · {now_iso()}",
        "> 本文件为展示层，禁止手工修改；请通过 recall.py 操作数据",
        "",
        "## 汇总",
        f"- 总记录: {len(recalls)} | 待处理: {sum(1 for r in recalls if r.get('status') == '待处理')} | 进行中: {sum(1 for r in recalls if r.get('status') == '进行中')} | 等待反馈: {sum(1 for r in recalls if r.get('status') == '等待反馈')} | 已完成: {sum(1 for r in recalls if r.get('status') == '已完成')}",
        f"- 待提醒: {sum(1 for r in recalls if r.get('needs_reminder'))}",
        "",
    ]
    for cat in CATEGORIES:
        items = [r for r in recalls if r.get("category") == cat]
        if not items:
            continue
        items.sort(key=lambda r: r.get("created_at", ""))
        lines.append(f"## {cat}")
        for r in items:
            done = "[x]" if r.get("status") == "已完成" else "[ ]"
            state = f"（{r.get('status')}）" if r.get("status") != "待处理" else ""
            remind = f" ⏰ {r['remind_at']}" if r.get("needs_reminder") else ""
            tags = f" `{' '.join('#' + t for t in r.get('tags', []))}`" if r.get("tags") else ""
            created = r.get("created_at", "")[:16].replace("T", " ")
            meta = ""
            mem = r.get("memory")
            all_ids = {q.get("id") for q in data.get("recalls", [])}
            if mem:
                bits = []
                if mem.get("memory_type") and mem["memory_type"] != "unknown":
                    bits.append(f"📌{mem['memory_type']}")
                if mem.get("importance") and mem["importance"] != "normal":
                    bits.append(f"🔥{mem['importance']}")
                if mem.get("entities"):
                    bits.append("@" + "/".join(mem["entities"]))
                if mem.get("waiting_for"):
                    bits.append(f"⏳等{mem['waiting_for']}")
                if mem.get("related_ids"):
                    bad = [x for x in mem["related_ids"] if x not in all_ids]
                    if bad:
                        bits.append("⚠悬空:" + "/".join(bad))
                if bits:
                    meta = " " + " ".join(bits)
            if r.get("parent_id"):
                meta += f" ⬆{r['parent_id']}"
            lines.append(f"- {done} {r.get('content')} {state}{remind}{tags}{meta} · {created}")
            tl = r.get("timeline")
            if tl:
                for ev in tl:
                    d = (ev.get("date") or "")[:16].replace("T", " ")
                    lines.append(f"  - 🕐 {d} {ev.get('event')}")
        lines.append("")
    target.write_text("\n".join(lines), encoding="utf-8")
    print(f"[回响] 视图已生成: {target}")
    return 0


def cmd_due(args) -> int:
    data = load_data()
    now = datetime.now().astimezone()
    due = []
    for r in data.get("recalls", []):
        if not r.get("needs_reminder"):
            continue
        if r.get("reminder_status") != "pending":
            continue
        remind = parse_remind_at(r.get("remind_at", ""))
        if remind is None or remind <= now:
            due.append(r)
    due.sort(key=lambda r: r.get("remind_at", ""))
    if args.json:
        print(json.dumps(due, ensure_ascii=False, indent=2))
    elif due:
        for r in due:
            print(f"{r['id']} | {r['remind_at']} | [{r.get('category')}] {r.get('content')}")
    else:
        print("[回响] 暂无到期提醒")
    return 0


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        cfg = {"feishu_webhook_url": ""}
        CONFIG_FILE.write_text(
            json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        return cfg
    return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))


def send_feishu(webhook: str, text: str) -> bool:
    payload = json.dumps({
        "msg_type": "text",
        "content": {"text": text},
    }).encode("utf-8")
    req = urllib.request.Request(
        webhook, data=payload,
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8")
            return '"ok"' in body or '"StatusCode":0' in body or '"code":0' in body
    except Exception as e:
        print(f"[错误] 飞书发送失败: {e}", file=sys.stderr)
        return False


def cmd_send_reminders(args) -> int:
    cfg = load_config()
    webhook = cfg.get("feishu_webhook_url", "").strip()
    data = load_data()
    now = datetime.now().astimezone()
    due = []
    for r in data.get("recalls", []):
        if not r.get("needs_reminder") or r.get("reminder_status") != "pending":
            continue
        remind = parse_remind_at(r.get("remind_at", ""))
        if remind is not None and remind <= now:
            due.append(r)
    if not due:
        return 0  # 无到期提醒：静默

    if args.dry_run:
        print(f"[回响] (dry-run) 有 {len(due)} 条到期提醒待发送:")
        for r in due:
            print(f"  {r['id']} | {r['remind_at']} | {r.get('content')}")
        return 0

    if not webhook:
        # Hermes 通道模式：输出友好提醒文本（由 cron deliver 投递到飞书），输出即视为已投递
        for r in due:
            print(f"⏰ Hermes Recall 提醒\n【{r.get('category')}】{r.get('content')}\n"
                  f"提醒时间: {r['remind_at']}\n记录于: {r.get('created_at', '')[:16]}")
            r["reminder_status"] = "sent"
            r["updated_at"] = now_iso()
            log_history("remind_sent", r["id"], {"remind_at": r["remind_at"], "channel": "hermes"})
        save_data(data)
        return 0

    sent_ok = []
    sent_fail = []
    for r in due:
        text = (f"⏰ Hermes Recall 提醒\n"
                f"【{r.get('category')}】{r.get('content')}\n"
                f"提醒时间: {r['remind_at']}\n"
                f"记录于: {r.get('created_at', '')[:16]}")
        ok = send_feishu(webhook, text)
        if ok:
            r["reminder_status"] = "sent"
            r["updated_at"] = now_iso()
            log_history("remind_sent", r["id"], {"remind_at": r["remind_at"]})
            sent_ok.append(r["id"])
        else:
            r["reminder_status"] = "failed"
            r["updated_at"] = now_iso()
            sent_fail.append(r["id"])
    save_data(data)
    # webhook 直发模式下保持静默（错误走 stderr），避免内部日志污染 cron 投递输出
    for rid in sent_fail:
        print(f"[回响] 提醒发送失败(状态=failed): {rid}", file=sys.stderr)
    return 1 if sent_fail else 0


def cmd_migrate(args) -> int:
    """从旧 Markdown 文件迁移到 JSON（source=migration）。

    支持两种旧格式:
    - 旧版回响归档: "## YYYY-MM-DD HH:MM 周X" + 内容行
    - 普通列表: "# 标题" + "- 条目"（用 --file 指定，防误迁视图文件）
    """
    if args.file:
        old_files = [Path(args.file)]
    else:
        old_files = sorted(RECALL_DIR.glob("2*.md"))
    if not old_files:
        print("[回响] 没有找到旧 Markdown 数据文件")
        return 0
    data = load_data()
    migrated = 0
    for f in old_files:
        if not f.exists():
            print(f"[错误] 文件不存在: {f}", file=sys.stderr)
            return 2
        mtime_iso = datetime.fromtimestamp(f.stat().st_mtime).astimezone().isoformat(timespec="seconds")
        lines = f.read_text(encoding="utf-8").splitlines()
        entry_time, entry_lines = None, []
        for line in lines:
            s = line.strip()
            if line.startswith("## "):
                if entry_time and entry_lines:
                    migrated += _migrate_one(data, entry_time, entry_lines, args.dry_run)
                entry_time = line[3:].strip()
                entry_lines = []
            elif s.startswith("- "):
                migrated += _migrate_one(data, entry_time or mtime_iso, [s[2:].strip()], args.dry_run)
            elif s.startswith("# "):
                continue  # 文档标题，跳过
            elif s and entry_time is not None:
                entry_lines.append(s)
        if entry_time and entry_lines:
            migrated += _migrate_one(data, entry_time, entry_lines, args.dry_run)
    if not args.dry_run:
        save_data(data)
    print(f"[回响] 迁移完成: {migrated} 条" + ("（dry-run，未写入）" if args.dry_run else ""))
    return 0


def _migrate_one(data: dict, entry_time: str, lines: list, dry_run: bool) -> int:
    content = "；".join(lines)
    category = guess_category(content)
    needs_reminder = False
    remind_at = None
    # 简单启发：包含时间词视为需要提醒（具体时间由后续 update 校正）
    if any(k in content for k in ["提醒", "开会", "截止", "提交", "明天", "下周", "月", "日", "点"]):
        needs_reminder = True
    rid = next_id(data)
    rec = {
        "id": rid,
        "schema_version": SCHEMA_VERSION,
        "content": content,
        "category": category,
        "tags": [],
        "needs_reminder": needs_reminder,
        "remind_at": remind_at,
        "reminder_status": "pending",
        "status": "待处理",
        "priority": "normal",
        "created_at": entry_time,
        "updated_at": entry_time,
        "source": "migration",
        "metadata": {"migrated_from": "markdown"},
    }
    if dry_run:
        print(f"  [migrate] {rid} | {category} | {content}")
    else:
        data.setdefault("recalls", []).append(rec)
        log_history("create", rid, {"content": content, "source": "migration"})
    return 1


def _version_tuple(v) -> tuple:
    """版本号字符串转可比较元组："1.01" -> (1, 1)。"""
    try:
        return tuple(int(x) for x in str(v).split("."))
    except (ValueError, AttributeError):
        return (0,)


def cmd_upgrade(args) -> int:
    """Schema v1→v2 迁移：备份 → 预检 → 迁移（sent→reminded、版本提升）→ 校验。

    原则：不修改 content / category；缺失 memory / timeline 不补（合法，不得因读取写回）；
    reminder_status 映射：sent→reminded（七状态枚举），其余值保留。
    """
    import subprocess as _sp
    data = load_data()
    # 预检：id 唯一
    ids = [r.get("id") for r in data.get("recalls", [])]
    if len(ids) != len(set(ids)):
        print("[错误] 预检失败：存在重复 id，停止迁移", file=sys.stderr)
        return 1
    # 备份
    ts = now_iso().replace(":", "-").replace("+", "-")
    backup_path = DATA_FILE.with_name(f"recall.backup-{ts}.json")
    backup_path.write_text(DATA_FILE.read_text(encoding="utf-8"), encoding="utf-8")
    hist_path = RECALL_DIR / "recall_history.json"
    hist_backup = None
    if hist_path.exists():
        hist_backup = hist_path.with_name(f"recall_history.backup-{ts}.json")
        hist_backup.write_text(hist_path.read_text(encoding="utf-8"), encoding="utf-8")
    # 迁移
    changed = 0
    cur = _version_tuple(SCHEMA_VERSION)
    for r in data.get("recalls", []):
        before = dict(r)
        if not r.get("id"):
            r["id"] = next_id(data)
        sv = r.get("schema_version")
        if not sv or _version_tuple(sv) < cur:
            r["schema_version"] = SCHEMA_VERSION
        if r.get("reminder_status") == "sent":
            r["reminder_status"] = "reminded"
        if not r.get("created_at"):
            r["created_at"] = now_iso()
        if not r.get("updated_at"):
            r["updated_at"] = r.get("created_at") or now_iso()
        if dict(r) != before:
            changed += 1
            log_history("update", r["id"], {"before": before, "after": dict(r), "note": f"schema upgrade -> v{SCHEMA_VERSION}"})
    old_ver = data.get("version", "?")
    data["version"] = SCHEMA_VERSION
    save_data(data)
    print(f"[回响] 迁移完成: {changed} 条记录已升级（顶层 version {old_ver} -> {SCHEMA_VERSION}）")
    print(f"[回响] 备份: {backup_path}")
    if hist_backup:
        print(f"[回响] 历史备份: {hist_backup}")
    # 迁移后校验
    vr = _sp.run([sys.executable, str(Path(__file__).resolve().parent / "validate_recall.py")],
                 capture_output=True, text=True, encoding="utf-8")
    print(vr.stdout.strip())
    if vr.returncode != 0:
        print("[回响] ⚠ 迁移后校验未通过，可用 restore 恢复备份", file=sys.stderr)
        return 1
    print("[回响] 迁移后校验通过 ✓")
    return 0


def cmd_restore(args) -> int:
    """从备份文件恢复数据（复制覆盖 recall.json）。"""
    src = Path(args.backup_file)
    if not src.exists():
        print(f"[错误] 备份不存在: {src}", file=sys.stderr)
        return 1
    DATA_FILE.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"[回响] 已从备份恢复: {src} -> {DATA_FILE}")
    return 0


def cmd_stats(args) -> int:
    data = load_data()
    recalls = data.get("recalls", [])
    if not recalls:
        print("[回响] 暂无记录")
        return 0
    print(f"总记录: {len(recalls)}")
    from collections import Counter
    for cat, n in Counter(r.get("category") for r in recalls).most_common():
        print(f"  {cat}: {n}")
    mtypes = Counter((r.get("memory") or {}).get("memory_type") for r in recalls)
    if any(mtypes):
        print("记忆类型:")
        for mt, n in mtypes.most_common():
            print(f"  {mt or '(未标注)'}: {n}")
    hist = load_history().get("events", [])
    if hist:
        print(f"历史事件: {len(hist)} 条")
    return 0


# ---------- 入口 ----------

def main():
    parser = argparse.ArgumentParser(description="Hermes Recall（回响）v2")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add", help="记录一条")
    p_add.add_argument("content", nargs="+")
    p_add.add_argument("--category", default=None, help=f"分类: {'/'.join(CATEGORIES)}")
    p_add.add_argument("--tags", default=None, help="逗号分隔标签")
    p_add.add_argument("--remind-at", default=None, help="ISO 8601 提醒时间")
    p_add.add_argument("--priority", default=None, choices=PRIORITIES)
    p_add.add_argument("--source", default=None)
    p_add.add_argument("--parent-id", default=None, help="父回响 ID（不覆盖，建立关联）")
    p_add.add_argument("--memory-type", default=None, choices=MEMORY_TYPES, help=f"记忆类型: {'/'.join(MEMORY_TYPES)}")
    p_add.add_argument("--importance", default=None, choices=IMPORTANCES, help=f"记忆重要度: {'/'.join(IMPORTANCES)}")
    p_add.add_argument("--entities", default=None, help="涉及实体，逗号分隔")
    p_add.add_argument("--related-ids", default=None, help="关联记录 ID，逗号分隔")

    p_list = sub.add_parser("list", help="查看记录")
    p_list.add_argument("--category", default=None)
    p_list.add_argument("--status", default=None, choices=STATUSES)
    p_list.add_argument("--remind", action="store_true", help="只看带提醒的")
    p_list.add_argument("--all", action="store_true", help="含已归档")

    p_get = sub.add_parser("get", help="按 id 查看详情")
    p_get.add_argument("id")

    p_search = sub.add_parser("search", help="关键字搜索")
    p_search.add_argument("keyword", nargs="+")

    p_update = sub.add_parser("update", help="修改记录")
    p_update.add_argument("id")
    p_update.add_argument("--content", nargs="+")
    p_update.add_argument("--category", default=None)
    p_update.add_argument("--tags", default=None)
    p_update.add_argument("--status", default=None, choices=STATUSES)
    p_update.add_argument("--priority", default=None, choices=PRIORITIES)
    p_update.add_argument("--remind-at", default=None)
    p_update.add_argument("--needs-reminder", default=None, choices=["true", "false"])
    p_update.add_argument("--reminder-status", default=None, choices=REMINDER_STATUSES, help="提醒状态（如 cancelled 取消提醒）")
    p_update.add_argument("--parent-id", default=None, help="父回响 ID（传空清空）")
    p_update.add_argument("--memory-type", default=None, choices=MEMORY_TYPES)
    p_update.add_argument("--importance", default=None, choices=IMPORTANCES)
    p_update.add_argument("--entities", default=None, help="涉及实体，逗号分隔")
    p_update.add_argument("--related-ids", default=None, help="关联记录 ID，逗号分隔")
    p_update.add_argument("--waiting-for", default=None, help="设置等待反馈对象（自动进入等待反馈状态）")
    p_update.add_argument("--timeline-event", default=None, help="追加一条 timeline 事件")

    p_done = sub.add_parser("done", help="标记完成")
    p_done.add_argument("id")

    p_delete = sub.add_parser("delete", help="删除记录")
    p_delete.add_argument("id")

    p_view = sub.add_parser("view", help="生成 Markdown 视图")
    p_view.add_argument("--output", default=None, help="输出文件名（默认 recall_view.md，如 daily.md 生成到数据目录）")
    p_due = sub.add_parser("due", help="列出到期提醒")
    p_due.add_argument("--json", action="store_true")

    p_send = sub.add_parser("send-reminders", help="发送到期提醒（飞书）")
    p_send.add_argument("--dry-run", action="store_true")
    p_send.add_argument("--quiet", action="store_true")

    p_migrate = sub.add_parser("migrate", help="迁移旧 Markdown 数据")
    p_migrate.add_argument("--file", default=None, help="指定旧文件路径（支持列表格式）")
    p_migrate.add_argument("--dry-run", action="store_true")

    sub.add_parser("upgrade", help="Schema v1→v2 迁移：备份→迁移（sent→reminded）→校验")
    p_restore = sub.add_parser("restore", help="从备份文件恢复数据")
    p_restore.add_argument("backup_file", help="备份文件路径（如 recall.backup-*.json）")

    sub.add_parser("stats", help="统计")

    args = parser.parse_args()
    cmds = {
        "add": cmd_add, "list": cmd_list, "get": cmd_get,
        "search": cmd_search, "update": cmd_update, "done": cmd_done,
        "delete": cmd_delete, "view": cmd_view, "due": cmd_due,
        "send-reminders": cmd_send_reminders, "migrate": cmd_migrate,
        "upgrade": cmd_upgrade, "restore": cmd_restore, "stats": cmd_stats,
    }
    return cmds[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
