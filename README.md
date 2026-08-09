# Hermes Recall（回响）

本地智能备忘录与个人记忆模块。用户说人话，Hermes 自动理解语义、分类、打标签、设提醒，并在指定时间通过飞书推送。JSON 为唯一事实来源，Markdown 仅作展示层。

> Recall = Hermes 对用户过去想法、计划和信息的回响。

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

```
hermes cron add --schedule "every 15m" --script <skill_dir>/scripts/recall_scheduler.py --deliver local
```

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

已通过验收测试（详见设计文档）：
- Test 01 数据结构：CRUD 生命周期、Schema 合规
- Test 02 智能分类：5 用例 + 边界测试（100% 语义判定）
- Test 03 提醒系统：时间语义 + Scheduler 端到端（飞书实收）
- Test 04 Markdown View：渲染 + 数据层解耦验证
- Test 05 数据迁移：旧格式 → JSON（字段完整率 100%）
- Schema 版本升级测试：新记录全字段 / 历史数据自动补齐

## 目录结构

```
hermes-recall/
├── SKILL.md                    # 操作规范（Agent 用）
├── README.md                   # 本文件（人类用）
├── LICENSE
├── references/
│   └── feishu-gateway.md       # 飞书通道排障指南
└── scripts/
    ├── recall.py               # 核心 CLI（纯标准库）
    ├── recall_scheduler.py     # 提醒调度包装（cron no_agent 用）
    └── validate_recall.py      # 数据完整性校验
```

## 版本

统一版本号：项目 = recall.json 顶层 version = 记录级 schema_version = **1.01**
（升级数据格式时同步递增三者并运行 `recall.py upgrade`）

## License

MIT（见 LICENSE 文件）
