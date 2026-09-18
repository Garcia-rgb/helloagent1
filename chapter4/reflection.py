# -*- coding: utf-8 -*-
"""第 4 章 · Reflection 启动器

教程原文件 Hello-Agents/code/chapter4/Reflection.py 一个字都没改 ——
这里只是把它 import 进来跑，另外给你两个改参数的地方（TASK / MAX_ITERATIONS）。

跑法:
    Hello-Agents\\.venv\\Scripts\\python.exe chapter4/reflection.py

注意：用教程默认的素数任务，它会在第 1 轮就停下（初始代码直接给的就是筛法，
评审认为无需改进）。想看到真正的「反思 → 优化」迭代，把 TASK 换掉 ——
下面注释里给了几个初始解容易写差的题。
"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # 仓库根（chapter4/ 的上一层）
CH4 = os.path.join(ROOT, "Hello-Agents", "code", "chapter4")
ENV_FILE = os.path.join(ROOT, "Hello-Agents", ".env")

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, CH4)

_T0 = time.time()


def say(msg: str):
    print(f"[{time.time() - _T0:6.1f}s] {msg}", flush=True)


say("开始 import（很快，只有 openai / dotenv）...")

from dotenv import load_dotenv

load_dotenv(ENV_FILE)

from llm_client import HelloAgentsLLM
from Reflection import ReflectionAgent

say("依赖就绪")

# ============================================================
# 要改就改这两个。
#
# TASK：挑「初始版本几乎一定写得不够好」的题，才看得到多轮迭代。例如：
#   - "编写一个Python函数，计算第n个斐波那契数 (Fibonacci number)。"
#     （初始多半给朴素递归 → 评审会说指数复杂度 → 才会进第二轮）
#   - "编写一个Python函数，判断一个字符串是否为另一个字符串的字母异位词 (anagram)。"
#   - "编写一个Python函数，找出一个列表中和最大的连续子数组。"（最大子段和）
#
# MAX_ITERATIONS：反思轮数上限，每轮最多产出一个新版本。给 3 比教程默认的 2 更能看到东西。
# ============================================================
TASK = "编写一个Python函数，找出1到n之间所有的素数 (prime numbers)。"
MAX_ITERATIONS = 2


if __name__ == "__main__":
    say("初始化 LLM 客户端 ...")
    agent = ReflectionAgent(HelloAgentsLLM(), max_iterations=MAX_ITERATIONS)
    agent.run(TASK)
    say("结束")
