# -*- coding: utf-8 -*-
"""第 4 章 · Plan-and-Solve 启动器

教程原文件 Hello-Agents/code/chapter4/Plan_and_solve.py 一个字都没改 ——
这里只是把它 import 进来跑，另外给你一个改问题的地方（下面的 QUESTION）。

跑法:
    Hello-Agents\\.venv\\Scripts\\python.exe chapter4/plan_solve.py

它和教程原文件的区别只有三点：每步带已运行秒数、输出保证 UTF-8、
问题集中在 QUESTION 一处。Planner / Executor / PlanAndSolveAgent 全是原版的。
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
from Plan_and_solve import PlanAndSolveAgent

say("依赖就绪")

# ============================================================
# 要改就改这一行。Plan-and-Solve 的表现差别全在题目上：
#   - 一步能算完的题（原题）→ 计划阶段就把答案写进去了，执行阶段走过场
#   - 需要分工的题（例：「帮我规划杭州三日游，预算 3000 元」）→ 才看得出计划的价值
# ============================================================
QUESTION = "一个水果店周一卖出了15个苹果。周二卖出的苹果数量是周一的两倍。周三卖出的数量比周二少了5个。请问这三天总共卖出了多少个苹果？"


if __name__ == "__main__":
    say("初始化 LLM 客户端 ...")
    agent = PlanAndSolveAgent(HelloAgentsLLM())
    agent.run(QUESTION)
    say("结束")
