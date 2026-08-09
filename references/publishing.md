# 发布与分发维护（GitHub + SkillHub）

Hermes Recall 已双平台发布。修改 skill 内容后按本文件同步，保持两平台与本地一致。

## GitHub（国际）

- 仓库: https://github.com/Vegetableadog/hermes-recall（公开，MIT）
- skill 目录本身就是 git 仓库: `E:\HermesAgent\skills\productivity\hermes-recall`（.git 在其中，Hermes 加载不受影响）
- 更新流程: `cd <skill目录> && git add -A && git commit -m "说明" && git push`
- gh CLI: `C:\Program Files\GitHub CLI`（登录态存 keyring，账号 Vegetableadog，git 协议 https）
- 新手用户登录 gh 走 `gh auth login` 交互流程（GitHub.com → HTTPS → Yes → web browser → 设备码授权）；**浏览器登录 ≠ gh CLI 登录**，两者独立

## SkillHub（国内，腾讯）

- CLI: `~/.local/bin/skillhub`（登录态在 `~/.skillhub/config.json`，账号 @user_deef713e，skillId 149046）
- 更新流程: `skillhub publish <skill目录或zip> [--changelog "本次变更"]`
- 平台要求（实测踩坑）:
  * SKILL.md frontmatter **必须含** `slug` / `displayName` / `version`（Hermes 的 `name` 不被识别；逐个补字段直到 dry-run 通过）
  * **不允许 LICENSE 文件**（报 400 "不允许的文件类型"）→ 发布时用 zip 方式排除 LICENSE 和 .git：
    ```
    python -c "import zipfile; ..."  # 或用 tar --exclude 打包后转 zip
    ```
  * 发布前预检: `skillhub publish --dry-run <路径>`（不需要 token）
  * 签名验证: `skillhub verify "<slug>@<version>" --zip <zip>`；发布后平台索引同步有延迟，立即 verify/search 可能查不到，属正常
  * 收集用户反馈: `skillhub comment`（平台自带评论区）

## Windows 特定坑（本机已验证的修复）

- skillhub 包装脚本（~/.local/bin/skillhub）原版把 MSYS 路径传给 Windows python 报错 → 本机版已修复为显式 `D:/exploitation/python3.12/python.exe` + `C:/Users/Administrator/.skillhub/...`（Windows 风格路径）
- git-bash 里 `curl -o <MSYS路径>` 报 `exit 23`（写入失败）→ 用重定向 `curl ... > 文件` 即可；skillhub 安装脚本内部用 `curl -o` + mktemp 的 MSYS 临时路径会失败 → 手动下载 latest.tar.gz 解压出 `cli/` 目录后重跑脚本走"本地 kit"路径
- 平台版本号用点分隔（frontmatter `version: 1.0.1`），与系统统一版本号 1.01 对应

## 用户账号信息（用于发布）

- GitHub: Vegetableadog（gh 已登录）
- SkillHub: user_deef713e（token 存本地 ~/.skillhub/config.json，**不要**让用户再次粘贴 token；token 是敏感凭证不进记忆/日志）
