# -*- coding: utf-8 -*-
"""Hermes Recall 统一提醒 Scheduler 包装脚本（供 cron no_agent 调用）。

语义：
  - 无到期提醒 -> 空输出，退出 0（cron 静默）
  - 有到期提醒 -> 输出友好提醒文本（由 cron deliver 投递到配置的目标），脚本侧置 sent
  - 出错 -> 非零退出（cron 发错误提醒）

要求：本脚本与 recall.py 位于同一目录（skill 的 scripts/ 下）。
"""
import subprocess
import sys
from pathlib import Path

RECALL = str(Path(__file__).resolve().parent / "recall.py")

r = subprocess.run(
    [sys.executable, RECALL, "send-reminders", "--quiet"],
    capture_output=True, text=True, encoding="utf-8", errors="replace",
)
if r.stdout:
    print(r.stdout, end="")
if r.stderr:
    print(r.stderr, end="", file=sys.stderr)
sys.exit(r.returncode)
