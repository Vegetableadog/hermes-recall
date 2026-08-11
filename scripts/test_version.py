# -*- coding: utf-8 -*-
"""切片 7 测试：版本统一显示（产品/Skill/Schema 三版本）+ v2 标识清理。

运行：python scripts/test_version.py
"""
import os
import re
import subprocess
import sys
import tempfile

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recall.py")
SKILL_MD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SKILL.md")
fails = []


def check(name, ok, detail=""):
    print(("PASS" if ok else "FAIL"), "-", name, detail)
    if not ok:
        fails.append(name)


def run(args, env_dir):
    env = dict(os.environ)
    env["HERMES_RECALL_DIR"] = env_dir
    return subprocess.run([sys.executable, SCRIPT] + args, capture_output=True, text=True, encoding="utf-8", env=env)


# 1. --version 输出三版本
with tempfile.TemporaryDirectory(prefix="recall-ver-") as td:
    r = run(["--version"], td)
    check("--version 退出码 0", r.returncode == 0, f"exit={r.returncode}")
    out = r.stdout
    check("产品版本 1.1", "产品版本: 1.1" in out, out.strip().replace("\n", " | "))
    check("Skill 版本读取", "Skill 版本: 1.0.3" in out)
    check("Schema 版本 2.0", "Schema 版本: 2.0" in out)

    # 2. 子命令不受影响
    r = run(["list"], td)
    check("list 命令正常", r.returncode == 0)

    # 3. 既有功能正常（add + stats）
    r = run(["add", "版本测试"], td)
    check("add 正常", r.returncode == 0)

# 4. v2 标识清理（docstring/description 无残留）
with open(SCRIPT, encoding="utf-8") as f:
    src = f.read()
head = src[:40]
check("docstring 无 v2 残留", "核心模块 v2" not in src and "（回响）v2" not in src)
check("description 无 v2 残留", 'description="Hermes Recall（回响）——本地智能备忘录"' in src)

# 5. SKILL.md 版本单源一致性
with open(SKILL_MD, encoding="utf-8") as f:
    sm = f.read()
m = re.search(r"^version:\s*([\w.]+)", sm, re.M)
check("SKILL.md version 存在且为 1.0.3", m is not None and m.group(1) == "1.0.3", str(m.group(1) if m else None))

print()
print("ALL PASS" if not fails else f"{len(fails)} FAILED: {fails}")
sys.exit(1 if fails else 0)
