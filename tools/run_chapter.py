# -*- coding: utf-8 -*-
"""
Hello-Agents 学习用 · 教程代码批量运行器

不修改教程原文件，直接在 code/chapterN/ 目录下逐个执行指定文件，
捕获 stdout / stderr / 退出码 / 耗时，汇总写入报告文件。

用法（在任意终端）:
    python tools/run_chapter.py 3                          # 跑第3章默认清单
    python tools/run_chapter.py 3 N_gram.py BPE.py         # 只跑指定文件
    python tools/run_chapter.py 4 --all                    # 跑该章全部 .py
    python tools/run_chapter.py 1 FirstAgentTest.py --timeout 600

说明:
    - 工作目录设为该章 code 目录，保证相对路径读写正常
    - 强制 UTF-8，避免中文输出在 Windows 控制台乱码
    - HF_HOME 指向仓库内的 .hf-cache，不污染用户目录
"""
import argparse
import os
import subprocess
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TUTORIAL = os.path.join(REPO_ROOT, "Hello-Agents")
REPORT = os.path.join(REPO_ROOT, "_run_report.txt")


def build_env():
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    env["HF_HOME"] = os.path.join(REPO_ROOT, ".hf-cache")
    return env


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("chapter", help="章节号，如 3")
    ap.add_argument("files", nargs="*", help="要运行的文件名；留空则用默认清单")
    ap.add_argument("--all", action="store_true", help="运行该章全部 .py")
    ap.add_argument("--timeout", type=int, default=1800, help="单文件超时秒数")
    ap.add_argument("--out", default=REPORT, help="报告输出路径")
    args = ap.parse_args()

    code_dir = os.path.join(TUTORIAL, "code", f"chapter{args.chapter}")
    if not os.path.isdir(code_dir):
        print(f"目录不存在: {code_dir}")
        return 2

    if args.all:
        targets = sorted(f for f in os.listdir(code_dir) if f.endswith(".py"))
    elif args.files:
        targets = args.files
    else:
        targets = ["N_gram.py", "BPE.py", "Word_Embedding.py", "Transformer.py"]

    lines = []

    def w(s=""):
        lines.append(str(s))

    w("=" * 70)
    w(f"章节      : chapter{args.chapter}")
    w(f"代码目录  : {code_dir}")
    w(f"运行时间  : {time.strftime('%Y-%m-%d %H:%M:%S')}")
    w("=" * 70)

    env = build_env()
    summary = []

    for name in targets:
        path = os.path.join(code_dir, name)
        w("")
        w("=" * 70)
        w(f"运行: code/chapter{args.chapter}/{name}")
        w("=" * 70)
        if not os.path.exists(path):
            w(f"  文件不存在: {path}")
            summary.append((name, "MISSING", 0.0))
            continue
        t0 = time.time()
        try:
            r = subprocess.run([sys.executable, path], cwd=code_dir, env=env,
                               capture_output=True, timeout=args.timeout)
            rc = r.returncode
            out = r.stdout.decode("utf-8", errors="replace")
            err = r.stderr.decode("utf-8", errors="replace")
        except subprocess.TimeoutExpired as e:
            rc = "TIMEOUT"
            out = (e.stdout or b"").decode("utf-8", errors="replace")
            err = f"超过 {args.timeout} 秒未结束"
        dt = time.time() - t0

        w(f"  exit code : {rc}")
        w(f"  耗时      : {dt:.2f} 秒")
        w("  ---- stdout ----")
        for ln in out.splitlines():
            w("  " + ln)
        if not out.strip():
            w("  (空)")
        if err.strip():
            w("  ---- stderr ----")
            for ln in err.splitlines():
                w("  " + ln)
        summary.append((name, rc, dt))

    w("")
    w("=" * 70)
    w("汇总")
    w("=" * 70)
    for name, rc, dt in summary:
        w(f"  {name:<28} exit={rc!s:<8} {dt:8.2f}s")

    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"报告已写入 -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
