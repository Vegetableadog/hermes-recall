---
name: hermes-recall
slug: hermes-recall
displayName: Hermes Recall（回响）
version: 1.0.1
description: Use when 记/查/搜备忘录（回响）。AI 做语义分类与提醒时间解析，经 recall.py 操作。
---

# Hermes Recall（回响）操作规范

本地智能备忘录模块。JSON 是唯一事实来源，Markdown 只是展示层。

## 何时使用
- 用户说「记一下 / 记住 / 记一条 / 帮我记 XX」
- 用户说「看看备忘录 / 回响 / 记录 / 待办」
- 用户搜索过去的记录（「搜索 XX」「我之前记过 XX 吗」）
- 用户改状态（「XX 做完了」「删掉 XX」）
- 用户提到需要定时提醒的事项

## 发布与维护（已开源）
- 开源仓库：https://github.com/Vegetableadog/hermes-recall（公开，MIT）；本 skill 目录即 git 仓库（.git 存在，不影响加载）
- 维护动作：改完 skill 内容后 `git add -A && git commit -m "说明" && git push`（在 skill 目录内执行）
- 别人安装：`hermes skills install github.com:Vegetableadog/hermes-recall`
- 发布/更新流程与 gh 认证坑见 skill `skill-publishing`
- **本 skill 双平台发布实例细节**（GitHub 仓库 + SkillHub skillId 149046、SkillHub frontmatter 字段要求、LICENSE 排除、Windows 打包坑、token 安全）见 `references/publishing.md`

## 安装与配置
- 本 skill 自带完整工具：`scripts/recall.py`（核心 CLI）、`scripts/recall_scheduler.py`（提醒调度包装）、`scripts/validate_recall.py`（数据校验）；Python 3.10+ 标准库即可，无第三方依赖
- 本 skill 为可分发包：README.md（安装/配置/上手）与 LICENSE（MIT）随包；分发化改造与 GitHub 发布流程见 skill `hermes-skill-publishing`
- 数据目录解析优先级：
  1. 环境变量 `HERMES_RECALL_DIR`（显式指定，推荐）
  2. 本机既有部署 `E:\HermesData\recall`（Windows 兼容早期版本）
  3. 通用默认 `~/HermesData/recall`（新用户）
- 数据目录首次使用时自动创建；内含 `recall.json`（唯一事实源）/ `recall_history.json` / `recall_view.md`（展示层）/ `config.json`
- 飞书提醒（可选）：两种通道（Hermes Gateway 投递 或 群机器人 webhook），排障细节见 `references/feishu-gateway.md`

## 记录流程（用户说「记一下 XX」）
1. **AI 语义分析**（这是 AI 的职责，脚本不做）：
   - `category`：五分类判断（见下）
   - `tags`：2~4 个关键词，逗号分隔
   - `needs_reminder`：内容含**明确时间**才为 true，否则 false
   - `remind_at`：换算 ISO 8601（+08:00）
2. 调用:
   ```
   python <skill_dir>/scripts/recall.py add "用户原话" --category 工作待办 --tags 客户,会议 --remind-at 2026-08-12T15:00:00+08:00
   ```
   （`<skill_dir>` 为本 skill 所在目录；本机为 `E:\HermesAgent\skills\productivity\hermes-recall`）
3. 看到 `[回响] 已记录 recall_YYYYMMDD_xxxxxx` 即成功。

## 分类规则（固定五类）
- **工作待办**：项目任务、工作安排、截止日期、开会、报告、客户
- **生活日常**：购物、日常安排、个人事务、家务
- **想法灵感**：创意、创业想法、随想、产品构思
- **学习笔记**：知识记录、学习内容、技术资料、研究
- **收藏**：文章、资源、推荐内容、链接

拿不准时默认「想法灵感」。**理解上下文语义，不机械匹配关键词**（如"想到一个 AI Agent 整理会议纪要的创业方向"→ 想法灵感，不是工作待办）。

## 时间换算（以当前会话日期为基准）
- 「明天」「后天」「下周一」「8月15日」→ 具体日期
- 无具体时刻时默认: 上午 09:00、中午 12:00、下午 14:00、晚上 20:00
- 有具体时刻（「下午3点」「9点半」）用具体时刻
- 截止期限（「8月20日前完成」）提前一天提醒，留缓冲
- 格式必须为 `2026-08-09T09:00:00+08:00`（ISO 8601 带时区）

## 查询与管理命令
```
python recall.py list                 # 查看全部（默认隐藏已归档）
python recall.py list --category 工作待办
python recall.py list --remind        # 只看带提醒的
python recall.py get <id>             # 单条详情（JSON）
python recall.py search <关键词>       # 全库搜索（内容+标签）
python recall.py done <id>            # 标记已完成
python recall.py update <id> --status 进行中 --tags a,b --remind-at ISO [--reminder-status pending|cancelled]   # 只更新 updated_at；id/created_at 不可修改
python recall.py delete <id>          # 删除（留历史）
python recall.py view [--output daily.md]  # 生成 Markdown 视图，默认 recall_view.md（展示层，JSON 是唯一事实源）
python recall.py due [--json]         # 查看到期未发提醒
python recall.py send-reminders [--dry-run]   # 手动触发提醒发送
python recall.py migrate [--file 旧文件.md] [--dry-run]   # 迁移旧 Markdown 到 JSON（source=migration）
python recall.py upgrade              # Schema 升级：历史数据补齐 schema_version 等字段
python recall.py stats                # 统计
```

## 提醒系统（统一 Scheduler，不逐条建 cron）
1. 创建统一调度任务（每 15 分钟检查）：
   ```
   hermes cron add --schedule "every 15m" --script <skill_dir>/scripts/recall_scheduler.py --deliver <平台>:<chat_id>
   ```
   （无提醒平台可先 `--deliver local`，配置飞书后再改）
2. 调度语义：脚本输出友好提醒文本 → cron deliver 投递 → 置 `reminder_status=sent`；无到期提醒时零输出（静默）
3. 筛选条件：`needs_reminder=true` AND `remind_at <= 当前时间` AND `reminder_status=pending`
4. **投递验证**：cron `Result: ok` 不代表送达——查 cron 的 `last_delivery_error`（null 才算送达）；失败时 `update <id> --reminder-status pending` 重置重试
5. 提醒消息格式：
   ```
   ⏰ Hermes Recall 提醒
   【工作待办】提交项目方案
   提醒时间: 2026-08-10T09:00:00+08:00
   记录于: 2026-08-09 00:38
   ```

## Pitfalls
- `content` 必须保留用户原话，不总结、不修改；需要概括放 `metadata` 或另存 summary 字段
- 任务 `status`（待处理/进行中/已完成/已归档）与 `reminder_status`（pending/sent/failed/cancelled）是两个独立状态，不要混
- 绝不直接编辑 recall.json / recall_view.md；所有修改走 recall.py
- id 格式 `recall_YYYYMMDD_xxxxxx`（随机 6 位 hex），由脚本生成，不要自定义；旧版序号格式 id 保留不变；id/created_at 不可修改（update 无对应参数）
- 版本号统一：项目版本 = recall.json 顶层 version = 记录级 schema_version（当前 1.01）；数据格式升级时同步递增三者并跑 `recall.py upgrade`
- 提醒时间判断宁缺毋滥：没有明确时间就不设 needs_reminder
- `reminder_status` Schema 允许值仅 pending/sent/failed/cancelled——非提醒记录的默认值也必须是 `pending`（无 "none" 值）；存量数据出现非法值用 `update <id> --reminder-status pending` 修复，手动取消提醒用 `--reminder-status cancelled`
- git-bash 里调 Windows python 传脚本/文件路径须用 `E:/...` 形式；`/e/...` 会被 python 误解析成 `C:\e\...` 报 No such file
- cron 投递目标用显式 chat_id（`feishu:oc_xxx`），勿用 bare 平台名（依赖执行进程环境变量）
- 手动 `cronjob run` 在 CLI 会话进程执行（可能缺 .env 凭据而投递失败），生产路径是 gateway 自然 tick
