# -*- coding: utf-8 -*-
"""第 7 章 · 教程代码运行器

教程第 7 章的代码在
    Hello-Agents\\code\\chapter7\\
一共 13 个文件，每个基本都能独立跑（自带 __main__），但有两个不便：
  1. 必须用 venv 里的 python（系统那个 3.12 没装 hello_agents）
  2. 中文 + emoji 在 GBK 终端会糊成乱码

这个脚本包一层，顺便把每次输出存一份 UTF-8 记录。

用法（在仓库根目录敲）:

    python chapter7\\run.py list                  # 本章有哪些文件
    python chapter7\\run.py quickstart            # 跑 chapter7\\quickstart.py
    python chapter7\\run.py my_llm                # 跑教程的 my_llm.py
    python chapter7\\run.py test_simple_agent     # 跑教程的测试
    python chapter7\\run.py my_llm --mine         # 跑 chapter7\\ 下你自己写的那份

查找顺序：不加 --mine 时先找教程目录，再找 chapter7\\ 自己的；
加了 --mine 就只找 chapter7\\ 下的。两边同名时用这个开关切换。
"""
import argparse
import datetime
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent                  # chapter7/
REPO_ROOT = HERE.parent
TUTORIAL_CH7 = REPO_ROOT / "Hello-Agents" / "code" / "chapter7"
VENV_PY = REPO_ROOT / "Hello-Agents" / ".venv" / "Scripts" / "python.exe"
ENV_FILE = REPO_ROOT / "Hello-Agents" / ".env"
RUNS_DIR = HERE / "runs"


def child_env():
    """给子进程一份干净的环境变量。"""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"     # 不加这句，重定向时 stdout 会退回 GBK
    env["PYTHONUNBUFFERED"] = "1"
    # 让教程的测试文件能 import 到 chapter7\ 下你自己写的 my_*.py
    env["PYTHONPATH"] = str(HERE) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY"):
        env.pop(key, None)               # 本机直连即可，代理会干扰 api.deepseek.com

    try:
        from dotenv import dotenv_values
        if ENV_FILE.exists():
            for k, v in dotenv_values(ENV_FILE).items():
                if v is not None:
                    env.setdefault(k, v)
    except Exception:
        pass
    return env


def candidates(name, mine):
    name = name.strip()
    if name.endswith(".py"):
        name = name[:-3]
    local = HERE / f"{name}.py"
    tutorial = TUTORIAL_CH7 / f"{name}.py"
    return [local] if mine else [tutorial, local]


def warn_missing_imports(path):
    """教程有两个测试文件依赖「该你自己写」的模块，先提醒一声再跑。"""
    text = path.read_text(encoding="utf-8", errors="replace")
    missing = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("from my_") and " import " in line:
            mod = line.split()[1]
            here_ok = (path.parent / f"{mod}.py").exists() or (HERE / f"{mod}.py").exists()
            if not here_ok:
                missing.append(mod)
    if missing:
        print(f"[提示] 该文件依赖 {', '.join(missing)}.py，教程里没有提供 —— "
              f"它属于「你自己写」的那部分（见文档 7.4.3 / 7.4.4）。")
        print("       写好后放在 chapter7\\ 下，运行器会自动把它加进 import 路径。")
        print()
    return missing


def cmd_list():
    print("教程自带（Hello-Agents\\code\\chapter7\\）：")
    for p in sorted(TUTORIAL_CH7.glob("*.py")):
        print(f"    {p.name[:-3]:<24} {p.stat().st_size:>6} B")
    print()
    print("chapter7\\ 自己的：")
    for p in sorted(HERE.glob("*.py")):
        if p.name != Path(__file__).name:
            print(f"    {p.name[:-3]:<24} {p.stat().st_size:>6} B")
    print()
    print("跑法：python chapter7\\run.py <名字>")


def cmd_run(name, mine):
    target = None
    for cand in candidates(name, mine):
        if cand.exists():
            target = cand
            break
    if target is None:
        print(f"找不到 {name}.py。试试：python chapter7\\run.py list", file=sys.stderr)
        return 1
    if not VENV_PY.exists():
        print(f"找不到 venv 的 python：{VENV_PY}", file=sys.stderr)
        return 1

    RUNS_DIR.mkdir(exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = RUNS_DIR / f"{target.stem}-{stamp}.txt"

    warn_missing_imports(target)

    print(f"[run] {target}")
    print(f"[out] {out_path}")
    print("-" * 68, flush=True)

    t0 = time.time()
    with open(out_path, "w", encoding="utf-8", buffering=1) as fh:
        fh.write(f"$ {VENV_PY}\n  {target}\n\n")
        proc = subprocess.Popen(
            [str(VENV_PY), str(target)],
            cwd=str(target.parent),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=child_env(),
        )
        for raw in proc.stdout:
            line = raw.decode("utf-8", errors="replace")
            sys.stdout.write(line)
            sys.stdout.flush()
            fh.write(line)
        code = proc.wait()

    print("-" * 68)
    print(f"[exit] {code}   用时 {time.time() - t0:.1f}s")
    return code


def main():
    ap = argparse.ArgumentParser(description="第 7 章教程代码运行器")
    ap.add_argument("name", nargs="?", help="要跑的文件名（不带 .py）")
    ap.add_argument("--mine", action="store_true", help="只找 chapter7\\ 下自己写的那份")
    ap.add_argument("--list", action="store_true", help="列出本章所有可跑文件")
    args = ap.parse_args()

    if args.list or args.name in (None, "list", "ls"):
        cmd_list()
        return 0
    return cmd_run(args.name, args.mine)


if __name__ == "__main__":
    sys.exit(main())
