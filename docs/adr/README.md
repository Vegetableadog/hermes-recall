# Hermes Recall 架构决策记录

本目录保存 Hermes Recall 的 Architecture Decision Records（ADR）。

ADR 用于记录会长期影响系统结构、数据兼容、运维方式或产品边界的重大决策。ADR 解释“为什么这样决定”，不代替系统架构、数据模型、测试计划或运维手册。

## 状态

| 状态 | 含义 |
|---|---|
| `Proposed` | 已提出，等待评审 |
| `Accepted` | 已确认，当前有效 |
| `Superseded` | 已被后续 ADR 替代 |
| `Rejected` | 已评审但未采用 |

## 编号规则

- 文件名格式：`ADR-NNN-short-title.md`；
- 编号按创建顺序递增；
- 编号分配后不复用；
- ADR 被替代时保留原文件；
- 新 ADR 通过 `Supersedes` 指向旧 ADR；
- 旧 ADR 通过 `Superseded by` 指向新 ADR。

## 何时创建 ADR

适合记录：

- 主存储技术选择；
- 数据事实来源；
- Scheduler 模式；
- Reminder 与 Notification 的边界；
- 重大 Schema 兼容策略；
- 模块拆分或平台依赖；
- 隐私、安全和多用户隔离策略；
- 会产生长期迁移成本的技术选择。

不适合记录：

- 普通缺陷修复；
- 临时任务进度；
- 单次发布结果；
- 可从代码直接看出的局部实现；
- 尚未形成明确取舍的随想；
- 操作步骤和排障命令。

## ADR 结构

每份 ADR 至少包含：

1. 元数据；
2. 背景；
3. 决策；
4. 决策理由；
5. 考虑过的替代方案；
6. 正面后果；
7. 负面后果与风险；
8. 实施约束；
9. 复审触发条件；
10. 相关文档。

## 变更规则

- Proposed 阶段可以修改内容；
- Accepted 后只允许修正错别字、链接和不改变含义的澄清；
- 如果决策本身发生变化，应创建新 ADR 并将旧 ADR 标记为 Superseded；
- ADR 不删除历史理由；
- ADR 状态变化需经过用户确认并单独提交。

## 索引

| ADR | 标题 | 状态 | 决策日期 |
|---|---|---|---|
| [ADR-001](ADR-001-json-as-current-storage.md) | 当前阶段继续使用 JSON 作为主存储 | Accepted | 2026-08-10 |
