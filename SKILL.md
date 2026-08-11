---
name: hermes-recall
slug: hermes-recall
displayName: Hermes Recall（回响）
version: 1.1.1
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
- **skill 生态运维**：双平台发布实例细节（SkillHub frontmatter 要求/LICENSE 排除/token 安全）+ **安装第三方 skill 绕行**（skills.sh 索引失效/URL 安装报错 → GitHub API 定位 + zip 解压）见 `references/publishing.md`

## 安装与配置
- 本 skill 自带完整工具：`scripts/recall.py`（核心 CLI）、`scripts/recall_scheduler.py`（提醒调度包装）、`scripts/validate_recall.py`（数据校验）；Python 3.10+ 标准库即可，无第三方依赖
- 本 skill 为可分发包：README.md（安装/配置/上手）与 LICENSE（MIT）随包；分发化改造与 GitHub 发布流程见 skill `hermes-skill-publishing`
- 正式项目文档：`docs/正式基线/01-项目总览.md` 至 `docs/正式基线/08-部署与运维.md`；项目唯一入口见 `docs/00_项目导航.md`；重大架构决策见 `docs/adr/README.md`；历史原稿见 `docs/archive/README.md`
- **文档治理规范**：`docs/Project_Context/个人项目升级流程与文档留存规范.md`（V1.6 已生效：版本归 git、状态归文档、文件名只承担职责；动数据一刀切分级；元规范不走五件套；设计后须模拟推演；收尾全仓合规扫描（scripts/check_compliance.py）+ 需求变动必查 06 + 综合结论逐条回填；档案内互链相对路径、档案外 /docs/ 根路径；暂缓项留「明确不做」去向；项目文档一律 md）。改项目文档/推进升级前先读它；方法论详见 skill `project-documentation-governance`
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

## 收藏类记录（用户发「收藏 URL」）
- **先验证链接再记录**（用户明确要求过「检查链接」）：curl 查 HTTP 状态（`curl -sS -L -o /dev/null -w '%{http_code}' URL`，git-bash 下 `curl: (23)` 写 /dev/null 噪音可忽略，用 `-I` HEAD 复核）；GitHub 仓库用 `gh repo view owner/repo --json nameWithOwner,isArchived,licenseInfo,stargazerCount,url` 核验；第三方服务类站点（模型中转/检测站）用 agent-reach 的 Exa 搜索公开评价与隐私条款
- 报告验证结果（可达/失效/风险提示）后再调用 add；URL 失效或站方隐私政策有明显风险（如中转站会留存请求/响应内容、第三方检测站数据非官方认证）时先提示用户
- 同一 URL 先 `recall.py search` 查重，避免重复收藏
- 用户原话里的 URL 必须原样保留在 content

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
python recall.py search <关键词>       # 全库搜索（内容+标签+涉及实体）
python recall.py done <id>            # 标记已完成
python recall.py update <id> --status 进行中 --tags a,b --remind-at ISO --waiting-for 邹总 --timeline-event 进展 --memory-type task [--reminder-status pending|reminded|waiting_response|completed|archived|failed|cancelled]   # 五状态：待处理/进行中/等待反馈/已完成/已归档；只更新 updated_at；id/created_at 不可修改
python recall.py delete <id>          # 删除（留历史）
python recall.py view [--output daily.md]  # 生成 Markdown 视图，默认 recall_view.md（展示层，JSON 是唯一事实源；V1.1 视图含时间线演化/父子回响链/悬空关联标记）
python recall.py due [--json]         # 查看到期未发提醒
python recall.py send-reminders [--dry-run]   # 手动触发提醒发送
python recall.py migrate [--file 旧文件.md] [--dry-run]   # 迁移旧 Markdown 到 JSON（source=migration）
python recall.py upgrade              # Schema v1→v2 迁移：自动备份→迁移（sent→reminded）→校验
python recall.py restore <备份文件>        # 从备份恢复（迁移/故障回滚）
python recall.py --version                # 显示产品/Skill/Schema 三版本
python recall.py stats                # 统计（含 V1.1 记忆类型分布）
python recall.py talk 记一下明天见邹总      # 回响式自然语言入口：记一下…/提醒我…/找…/完成 recall_xxx/删掉…/还在等邹总回复（删除需确认）
```

## 提醒系统（统一 Scheduler，不逐条建 cron）
1. 创建统一调度任务（每 15 分钟检查）：
   - 先将 `scripts/recall_scheduler.py` 部署到 `<HERMES_HOME>/scripts/recall_scheduler.py`；
   - 再创建 no-agent cron：
   ```
   hermes cron create "every 15m" --script recall_scheduler.py --no-agent --deliver <平台>:<chat_id>
   ```
   （无提醒平台可先 `--deliver local`，配置飞书后再改；完整步骤见 `docs/正式基线/08-部署与运维.md`）
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
- V1.1 已实现：`update` 支持 `--timeline-event/--waiting-for/--memory-type/--importance/--entities/--related-ids/--parent-id`；五状态（待处理/进行中/等待反馈/已完成/已归档）与 Reminder 七状态；`talk` 回响式交互（记一下/提醒我…/找…/完成…/删掉…/等…回复，删除需确认）；`--version` 统一显示产品/Skill/Schema 三版本
- `recall.json` 顶层结构是 `{"version": ..., "recalls": [...]}`，不是 `records`；`list` 输出截断长内容且无 `--json` 参数，要读完整内容直接取 `data['recalls']` 字段
- read_file 读 `docs/*.md` 可能误报 `Binary file`（编码问题），改用 `sed -n '起,止p'` 经 terminal 读取即可
- V1.1 设计输入（用户真实使用总结）：四类处理规则（完结→已完成+备注；动作完成事未了→进行中+最新进展；等外部反馈→保持+等待反馈；持续关注→保持+关注），80%更新原记录/20%新建（判据=未来回顾是否同一件事）；多阶段演进可能重复多次推进（如 5月→8月 项目）；V1.1 已完成并归档（docs/archive/upgrades/V1.1/）；Project_Context 与基线重叠文件已标 Superseded（权威见 01-08 正式基线）
- 任务 `status`（待处理/进行中/已完成/已归档）与 `reminder_status`（pending/sent/failed/cancelled）是两个独立状态，不要混
- 绝不直接编辑 recall.json / recall_view.md；所有修改走 recall.py
- id 格式 `recall_YYYYMMDD_xxxxxx`（随机 6 位 hex），由脚本生成，不要自定义；旧版序号格式 id 保留不变；id/created_at 不可修改（update 无对应参数）
- 版本分为产品基线 `v1.1`、Skill 发布版本 `1.1.0` 和数据 Schema `2.0`；三者含义不同，数据格式升级时更新 Schema、迁移逻辑和测试并运行 `recall.py upgrade`
- 提醒时间判断宁缺毋滥：没有明确时间就不设 needs_reminder
- `reminder_status` Schema 允许值仅 pending/sent/failed/cancelled——非提醒记录的默认值也必须是 `pending`（无 "none" 值）；存量数据出现非法值用 `update <id> --reminder-status pending` 修复，手动取消提醒用 `--reminder-status cancelled`
- git-bash 里调 Windows python 传脚本/文件路径须用 `E:/...` 形式；`/e/...` 会被 python 误解析成 `C:\e\...` 报 No such file
- cron 投递目标用显式 chat_id（`feishu:oc_xxx`），勿用 bare 平台名（依赖执行进程环境变量）
- 手动 `cronjob run` 在 CLI 会话进程执行（可能缺 .env 凭据而投递失败），生产路径是 gateway 自然 tick
