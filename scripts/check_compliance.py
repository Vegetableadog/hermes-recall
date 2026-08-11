# -*- coding: utf-8 -*-
"""全仓合规扫描（规范 V1.6 收尾校准工具）。

检查项：
  1. 过时版本/状态残留（v1.0 作为当前、V1.1 Next、待综合、Contract 未冻结等）；
  2. 文档状态行缺失或与事实不符（归档后仍 In Progress 等）；
  3. 链接有效性（相对路径与 /docs/ 根路径）；
  4. 输入材料「是否已综合：否」登记回填检查。

用法：python scripts/check_compliance.py [仓库根目录]
退出码：0=全部通过；1=发现问题。
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 过时版本/状态模式（V1.1 完成后不应再作为当前事实出现；archive/ 下 Historical 内容除外）
STALE_PATTERNS = [
    ("当前产品基线：v1.0", "头部版本还是 v1.0"),
    ("适用产品基线：v1.0", "基线版本还是 v1.0"),
    ("Schema 版本：1.01", "Schema 版本还是 1.01"),
    ("数据 Schema 版本 | 1.01", "Schema 版本 1.01"),
    ("Skill 发布版本：`1.0.3`", "Skill 版本 1.0.3"),
    ("version: 1.0.3", "SKILL version 1.0.3"),
    ("待步骤 2 综合", "待综合残留"),
    ("是否已被综合：否", "整理版未回填综合状态"),
    ("保持 Next", "v1.1 还是 Next"),
    ("v1.1 保持 Next", "v1.1 Next"),
    ("Contract 尚未冻结", "Contract 未冻结（已冻结）"),
    ("属于 v1.1 候选范围", "v1.1 候选范围（已实现）"),
]

# 归档后不应再出现的中间态状态
IN_PROGRESS_AFTER_ARCHIVE = ["In Progress", "Proposed"]

VALID_STATES = ["Current", "Proposed", "Frozen", "Evidence", "Historical", "Input",
                "Superseded", "Completed", "Idea", "Target"]
# 无状态行豁免（入口/分发/参考/adr 文件）
STATE_EXEMPT = {
    "README.md", "SKILL.md", "docs/00_项目导航.md", "docs/adr/README.md",
    "references/publishing.md", "references/feishu-gateway.md",
    "docs/Project_Context/用户反馈.md",
}


def all_md(root):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for f in filenames:
            if f.endswith(".md"):
                out.append(os.path.join(dirpath, f))
    return out


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else REPO
    issues = []
    for p in sorted(all_md(root)):
        rel = os.path.relpath(p, root).replace("\\", "/")
        with open(p, encoding="utf-8-sig", errors="replace") as f:
            c = f.read()
        is_archive = "/archive/" in rel
        # 1. 过时版本/状态残留（archive/ 下 Historical 标注段内可豁免，仅检查非 archive）
        if not is_archive:
            for pat, desc in STALE_PATTERNS:
                if pat in c:
                    issues.append(f"{rel}: {desc}（{pat[:30]}）")
        # 2. 状态行缺失/归档后中间态
        if rel not in STATE_EXEMPT:
            m = re.search(r"(文档状态|状态)[：:]\s*([A-Za-z /+]+)", c[:400])
            if not m:
                issues.append(f"{rel}: 头部无状态行")
            elif is_archive and any(s in m.group(2) for s in IN_PROGRESS_AFTER_ARCHIVE):
                issues.append(f"{rel}: 归档后状态仍为中间态「{m.group(2).strip()}」")
        # 3. 链接有效性
        for mm in re.finditer(r"\]\(([^)]+)\)", c):
            link = mm.group(1)
            if link.startswith(("http", "#", "mailto:")):
                continue
            target = (os.path.join(root, link.lstrip("/")) if link.startswith("/docs/")
                      else os.path.normpath(os.path.join(os.path.dirname(p), link)))
            if not os.path.exists(target):
                issues.append(f"{rel}: 链接失效「{link}」")
    if issues:
        print(f"发现 {len(issues)} 个问题：")
        for i in issues:
            print(" -", i)
        return 1
    print("全仓合规检查通过：无版本残留、状态行齐全、链接有效、登记已回填。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
