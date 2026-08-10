# Hermes Recall 历史设计原稿

> 文档状态：Historical
>
> 归档日期：2026-08-10

本目录保存 Hermes Recall 正式项目文档建立前的原始设计资料。

这些文件：

- 保留原始内容和原始文件字节；
- 作为项目设计历史与需求来源；
- 不再承担 Current 技术规范职责；
- 不应直接修改；
- 需要修正或扩展时，应更新正式 Markdown 文档或创建新的 ADR；
- 与当前源码或正式文档冲突时，按项目文档状态规则处理。

## 归档文件

| 文件 | 历史定位 | 主要内容 |
|---|---|---|
| `Hermes_Recall_v1.0_设计文档.docx` | 初始总体设计 | 项目定位、核心原则、初始数据模型、Reminder、Scheduler、Notification 和测试方向 |
| `Hermes_Recall_v1.4_多平台通知生态升级提示词文档.docx` | Notification 专项输入 | Provider、Identity、Routing、多渠道、配置和健康检查方向 |
| `Hermes_Recall_产品化方向与多模式架构升级文档.docx` | 产品化专项输入 | Experience Layer、Simple Mode、Personal Mode、Setup Wizard 和产品化路线 |
| `Hermes_Recall_未来升级路线与迭代提示词规划文档.docx` | 路线规划输入 | v1.1-v3.0、Weekly Review、智能 Reminder、SQLite 和 Vector Memory 方向 |

## 当前规范对应关系

| 历史主题 | 当前正式文档 |
|---|---|
| 项目定位与当前状态 | `../01-project-overview.md` |
| 系统边界与分层 | `../02-system-architecture.md` |
| 当前 Schema 与 Target 数据方向 | `../03-data-model.md` |
| 版本和阶段路线 | `../04-development-roadmap.md` |
| 测试体系 | `../05-test-plan.md` |
| 用户、场景和产品需求 | `../06-product-requirements.md` |
| Reminder 与 Notification | `../07-reminder-notification.md` |
| 安装、运维和发布 | `../08-deployment-operations.md` |
| 重大架构取舍 | `../adr/README.md` |

## 冲突处理顺序

发生冲突时按以下顺序核实：

1. 当前数据与真实运行结果；
2. 当前源码和可执行测试；
3. 标记为 Current 的正式项目文档；
4. 标记为 Target 的正式设计；
5. 本目录中的 Historical 原稿。

Historical 原稿中的未来能力不能仅因出现在文档中就被认定为已实现。

## 完整性

归档时已检查：

- 正文可以完整提取；
- 无批注、脚注、页眉、页脚或嵌入附件；
- 文档属性没有真实作者、公司或修改者信息；
- `customXml` 仅包含空 Word bibliography 模板；
- 归档副本使用 SHA-256 与桌面源文件逐项比对。

SHA-256 仅用于验证复制完整性，不作为内容版本号。桌面源文件继续保留，未移动、未覆盖、未修改。
