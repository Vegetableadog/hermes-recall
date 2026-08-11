# 发布与分发维护（GitHub + SkillHub）

Hermes Recall 使用同一个 Git 仓库作为源码和正式文档的事实来源，并同步发布到 GitHub 与 SkillHub。

本文档只记录可公开复用的维护流程，不保存账号登录态、Token 路径、真实 namespace、用户数据或本机凭据。

## 1. 版本边界

Recall 分别管理：

- 产品基线版本，例如 `v1.1`；
- Skill 发布版本，例如当前 `1.1.1`；
- 数据 Schema 版本，例如当前 `2.0`。

SkillHub 使用 `SKILL.md` frontmatter 的 Skill 发布版本。它不等同于产品版本或数据 Schema。

只修改文档、安装说明或发布配置时，可以提升 Skill patch 版本，但不自动提升产品或 Schema 版本。

## 2. 发布前门禁

发布前确认：

- `SKILL.md` frontmatter 有效；
- `name`、`slug`、`displayName`、`version` 和 `description` 正确；
- README、SKILL 和正式文档中的当前版本一致；
- Python 脚本编译通过；
- 基础 validator 通过；
- `git diff --check` 通过；
- 用户数据、History、`.env`、Webhook、Token 和平台身份未被 Git 跟踪；
- 发布包不包含 `.git`、缓存或本地部署文件；
- 变更已经完成人工验收。

完整发布门禁见 `../docs/正式基线/05-测试计划.md` 和 `../docs/正式基线/08-部署与运维.md`。

## 3. GitHub 发布

公开仓库：

```text
https://github.com/Vegetableadog/hermes-recall
```

提交前：

```bash
git status --short --branch
git diff --check
git diff --cached --check
```

只 stage 当前任务文件：

```bash
git add -- <file...>
git commit -m "<change-summary>"
git push origin main
```

推送后确认：

```bash
git rev-parse HEAD
git rev-parse origin/main
```

两者必须一致。

### GitHub 认证

浏览器登录 GitHub 不等于 `gh` CLI 已登录。需要使用：

```bash
gh auth login
gh auth status
```

Token 属于敏感凭据，不写入仓库、文档、Issue 或终端日志。

## 4. SkillHub 发布

### 4.1 Frontmatter

当前 SkillHub 发布要求 `SKILL.md` frontmatter 至少包含：

```yaml
name: hermes-recall
slug: hermes-recall
displayName: Hermes Recall（回响）
version: 1.1.1
description: Use when ...
```

发布要求可能变化，应以当前 SkillHub dry-run 结果为准。

### 4.2 发布包

发布包应包含：

- `SKILL.md`；
- `README.md`；
- `scripts/`；
- `references/`；
- 需要随 Skill 分发的正式文档。

发布包不得包含：

- `.git/`；
- 用户数据；
- `.env`；
- 本机 cron job；
- 本机绝对路径配置；
- 缓存和临时文件；
- Token 或登录配置。

当前维护经验表明 SkillHub 可能拒绝 `LICENSE` 等文件类型。不要从 GitHub 仓库删除 LICENSE；只在 SkillHub 发布包中按平台要求排除。

### 4.3 Dry-run

```bash
skillhub publish --dry-run <package-or-skill-dir>
```

通过后再发布：

```bash
skillhub publish <package-or-skill-dir> \
  --changelog "<change-summary>"
```

发布后可使用平台提供的 verify、search 或安装命令检查。索引同步可能有延迟，不能只凭发布后立即搜索不到就判断失败。

## 5. Windows 与 MSYS 路径

Git Bash 中调用 Windows 程序时：

- shell 内部可以使用 `/e/...`；
- 传给 Windows Python 或其他 Windows CLI 时优先使用 `E:/...`；
- 包装脚本应根据当前环境解析路径，不在公开文档中固化用户名或解释器安装位置；
- `curl -o` 写入 MSYS 临时路径失败时，可以改用 shell 重定向并检查退出码；
- 打包前列出 archive 内容，确认没有多余根目录或本机文件。

## 6. 安装第三方 Skill 的故障绕行

`hermes skills install <identifier>` 可能因为注册源索引过期、仓库结构变化或 URL 处理限制而失败。

### 6.1 先做安全检查

安装第三方 Skill 前应：

- 确认仓库所有者和许可证；
- 查看 `SKILL.md` 和脚本；
- 检查是否读取凭据、执行网络请求或修改系统文件；
- 使用 Skill 安全审查流程；
- 不因安装失败直接使用 `--force` 绕过安全结论。

### 6.2 GitHub API 定位真实路径

注册源路径与仓库真实结构不一致时，可以查询仓库树，定位 `SKILL.md`：

```bash
curl -s \
  "https://api.github.com/repos/OWNER/REPO/git/trees/main?recursive=1"
```

不要把未经审查的远程文件直接执行。

### 6.3 下载并提取目标 Skill

1. 下载仓库归档；
2. 列出归档内容，确认根目录名称和大小写；
3. 只提取目标 Skill 目录；
4. 跳过 `.git`、CI、缓存和无关文件；
5. 安装到当前 `<HERMES_HOME>/skills/<category>/<name>/`；
6. 使用 `hermes skills list` 和 `hermes skills audit` 检查；
7. 在隔离环境完成烟测。

不要在不确认目标目录内容时直接清空或覆盖已有 Skill。

### 6.4 SkillHub 安装

通用形式：

```bash
skillhub install <slug> \
  --namespace <namespace> \
  --dir <HERMES_HOME>/skills
```

namespace 和版本以发布页为准，不在通用文档中固化个人账号。

## 7. 双平台同步顺序

建议顺序：

1. 本地修改；
2. 测试和隐私扫描；
3. 用户验收；
4. Git commit；
5. GitHub push；
6. 远端核验；
7. SkillHub dry-run；
8. SkillHub publish；
9. 隔离安装烟测；
10. 记录发布结果。

GitHub 是源码事实来源。SkillHub 是分发渠道，不单独维护另一份代码。

## 8. 常见问题

### `Could not fetch ... from any source`

可能是注册源索引路径过期或仓库结构变化。先定位真实 `SKILL.md`，再走安全审查和手动安装流程。

### SkillHub 报不允许的文件类型

按 dry-run 错误调整发布包，不删除 GitHub 仓库中的许可证和必要源文件。

### 发布成功但搜索不到

等待索引同步，再使用 verify 或直接安装指定版本检查。

### GitHub 可以 push，但 `gh auth status` 未登录

Git 凭据和 `gh` CLI 凭据是两套状态。push 成功不代表 `gh` API 命令可用。

### 本地 Skill 可用，分发安装失败

检查：

- 是否硬编码本机路径；
- 是否依赖本机环境变量或凭据；
- scheduler 是否错误引用 Skill 内脚本路径；
- 首次运行是否能创建数据目录；
- 发布包是否漏掉 scripts/references/docs；
- frontmatter 是否满足平台要求。
