# Hermes Recall（回响）

本地智能备忘录与个人记忆模块。用户说人话，Hermes 自动理解语义、分类、打标签、设提醒，并在指定时间通过飞书推送。JSON 为唯一事实来源，Markdown 仅作展示层。

> Recall = Hermes 对用户过去想法、计划和信息的回响。

## 项目文档

正式项目文档位于 `docs/`：

- [项目总览与当前状态](docs/01-project-overview.md)
- [系统架构](docs/02-system-architecture.md)
- [数据模型](docs/03-data-model.md)
- [开发路线图](docs/04-development-roadmap.md)
- [测试计划](docs/05-test-plan.md)
- [产品需求](docs/06-product-requirements.md)
- [Reminder 与 Notification 设计](docs/07-reminder-notification.md)
- [部署与运维](docs/08-deployment-operations.md)
- [架构决策记录](docs/adr/README.md)
- [历史设计原稿归档](docs/archive/README.md)

正式文档区分 `Current`、`Target`、`Idea` 和 `Historical`。原始 Word 文档只作为历史输入，不代表当前功能已经实现。

## 功能特性

- 📝 **语义理解**：自动分类（工作待办/生活日常/想法灵感/学习笔记/收藏）+ 自动标签，理解上下文而非关键词匹配
- ⏰ **智能提醒**：识别"明天上午9点""8月20日前"等明确时间，到期自动推送；无明确时间不打扰（宁缺毋滥）
- 📊 **结构化存储**：JSON 单一事实源 + 完整历史记录（创建/修改/完成/删除/提醒全留痕）
- 📄 **Markdown 展示层**：一键生成人类可读视图（recall_view.md / daily.md），展示层与数据层完全解耦
- 🔄 **数据迁移**：旧 Markdown 备忘录一键迁入（source=migration 标记）
- 📈 **版本化管理**：记录级 schema_version + upgrade 命令，为未来数据库迁移铺路
- 🔔 **飞书推送**：经 Hermes Gateway 通道直达飞书 DM（可选，两种通道）

## 安装

方式一：通过 Hermes skill 机制安装

```
hermes skills search recall
hermes skills install <identifier>
```

方式二：手动安装（克隆到 profile 的 skills 目录）

```
git clone <repo-url> <HERMES_HOME>/skills/<category>/hermes-recall
```

方式三：SkillHub（国内源，更快）

```
skillhub search hermes-recall
skillhub install hermes-recall --namespace user_deef713e --dir <HERMES_HOME>/skills
```

## 多平台发布

- GitHub（国际）：https://github.com/Vegetableadog/hermes-recall
- SkillHub（国内）：skillhub.cn · skillId 149046（含评论区，欢迎反馈意见）
- 双平台更新保持同步：GitHub 走 git push，SkillHub 走 skillhub publish

## 配置

### 数据目录（可选，默认即可用）

数据目录解析优先级：
1. 环境变量 `HERMES_RECALL_DIR`（显式指定，推荐）
2. Windows 既有部署 `E:\HermesData\recall`（兼容早期版本）
3. 通用默认 `~/HermesData/recall`

首次使用时自动创建，内含：
- `recall.json` —— 唯一事实来源
- `recall_history.json` —— 历史事件
- `recall_view.md` —— 展示层（自动生成，禁止手改）
- `config.json` —— 配置（飞书 webhook 备用通道）

### 飞书提醒（可选）

- 方式 A（推荐）：Hermes Gateway 飞书通道 → `hermes setup gateway` 配置，cron 投递到 DM（排障见 skill 内 `references/feishu-gateway.md`）
- 方式 B：群机器人 webhook，填入 `config.json` 的 `feishu_webhook_url`

### 创建统一提醒调度（可选）

先将通用 wrapper 复制到 `<HERMES_HOME>/scripts/recall_scheduler.py`，再创建任务：

```
hermes cron create "every 15m" --script recall_scheduler.py --no-agent --deliver local
```

平台投递、显式目标和本机部署步骤见 [部署与运维](docs/08-deployment-operations.md)。

## 快速上手

```
# 记录（AI 语义分析：分类/标签/提醒时间）
python <skill_dir>/scripts/recall.py add "周三之前完成产品 PRD" --category 工作待办 --tags PRD,截止 --remind-at 2026-08-12T09:00:00+08:00

# 查询
python <skill_dir>/scripts/recall.py list                 # 全部（默认隐藏已归档）
python <skill_dir>/scripts/recall.py list --category 工作待办
python <skill_dir>/scripts/recall.py search 客户          # 关键字搜索

# 状态管理
python <skill_dir>/scripts/recall.py done <id>            # 标记完成
python <skill_dir>/scripts/recall.py delete <id>          # 删除（留历史）

# 视图与校验
python <skill_dir>/scripts/recall.py view --output daily.md
python <skill_dir>/scripts/validate_recall.py             # 数据完整性检查
```

完整命令表见 skill 内 SKILL.md 或 `python recall.py --help`。

## 测试

当前仓库已有可重复执行的基础检查：

- `validate_recall.py`：JSON、ID、分类、状态和提醒字段基础校验；
- `py_compile`：三个 Python 脚本语法检查。

历史设计阶段曾经执行过 CRUD、分类、Reminder、Markdown View、Migration 和 Schema upgrade 的人工验收，但仓库当前还没有 `pytest` 测试目录、CI 或完整可重复回归套件。因此历史验收不能等同于当前自动化测试覆盖。

完整测试范围、版本专项回归、执行状态和发布门禁见 [测试计划](docs/05-test-plan.md)。真实 Feishu 端到端测试需要隔离测试数据和用户明确同意。

## 目录结构

```
hermes-recall/
├── SKILL.md                    # 操作规范（Agent 用）
├── README.md                   # 本文件（人类用）
├── LICENSE
├── references/
│   └── feishu-gateway.md       # 飞书通道排障指南
├── docs/                       # 正式项目文档、ADR 和历史原稿归档
└── scripts/
    ├── recall.py               # 核心 CLI（纯标准库）
    ├── recall_scheduler.py     # 提醒调度包装（cron no_agent 用）
    └── validate_recall.py      # 数据完整性校验
```

## 版本

Recall 分别管理三类版本：

- 产品基线版本：`v1.0`，表示用户可使用的功能阶段；
- Skill 发布版本：`1.0.3`，表示 GitHub/SkillHub 安装包版本；
- 数据 Schema 版本：`1.01`，表示 `recall.json` 数据结构版本。

三者不要求每次同时变化。升级数据格式时，更新 Schema、迁移逻辑和测试，并运行 `recall.py upgrade`；只修改文档或发布说明时，不自动升级产品或 Schema 版本。

## License

MIT（见 LICENSE 文件）
