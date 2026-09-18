# -*- coding: utf-8 -*-
"""第 4 章 · ReAct 可运行版（搜索工具用 Tavily）

教程原文件 Hello-Agents/code/chapter4/ReAct.py、tools.py 一个字都没改。
这里只做一件事：把 tools.py 里的 search（SerpApi 版，需要 SERPAPI_API_KEY）
在运行时替换成 Tavily 实现，其余全部沿用原版 —— ToolExecutor 用原版的，
ReActAgent 用原版的，提示词也是原版的。

跑法:
    Hello-Agents\\.venv\\Scripts\\python.exe chapter4/react.py

没配 SERPAPI_API_KEY 也能跑，因为搜索这条路已经换成本机已有的 TAVILY_API_KEY。
"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # 仓库根（chapter4/ 的上一层）
CH4 = os.path.join(ROOT, "Hello-Agents", "code", "chapter4")
ENV_FILE = os.path.join(ROOT, "Hello-Agents", ".env")

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, CH4)

from dotenv import load_dotenv

load_dotenv(ENV_FILE)

# ---- 先把教程的 tools 模块加载进来，再把它的 search 换成 Tavily 版 ----
import tools as tutorial_tools


def tavily_search(query: str) -> str:
    """与 tools.py 的 search 同签名、同返回类型，底层换成 Tavily。

    原版返回的是一段可读文本（优先直接答案，其次前三条摘要），这里保持一致。
    """
    print(f"🔍 正在执行 [Tavily] 网页搜索: {query}")
    try:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            return "错误：TAVILY_API_KEY 未在 .env 文件中配置。"

        from tavily import TavilyClient

        client = TavilyClient(api_key=api_key)
        results_json = client.search(
            query=query,
            max_results=3,
            search_depth="basic",
            include_answer=True,
        )

        # 优先返回直接答案
        answer = results_json.get("answer")
        if answer:
            return answer

        results = results_json.get("results") or []
        if not results:
            return f"对不起，没有找到关于 '{query}' 的信息。"

        snippets = [
            f"[{i + 1}] {r.get('title', '')}\n{(r.get('content') or '')[:300]}"
            for i, r in enumerate(results[:3])
        ]
        return "\n\n".join(snippets)

    except Exception as e:
        return f"搜索时发生错误: {e}"


tutorial_tools.search = tavily_search  # ← 关键一行

# ---- 现在再加载教程的 ReAct，它 from tools import ... 时拿到的已是 Tavily 版 ----
from llm_client import HelloAgentsLLM  # noqa: E402
from ReAct import ReActAgent  # noqa: E402


if __name__ == "__main__":
    t0 = time.time()
    print(f"[{time.time() - t0:5.1f}s] 初始化 LLM 客户端 ...", flush=True)

    llm = HelloAgentsLLM()
    print(f"[{time.time() - t0:5.1f}s] LLM 客户端就绪", flush=True)

    tool_executor = tutorial_tools.ToolExecutor()
    tool_executor.registerTool(
        "Search",
        "一个网页搜索引擎。当你需要回答关于时事、事实以及在你的知识库中找不到的信息时，应使用此工具。",
        tavily_search,
    )

    agent = ReActAgent(llm_client=llm, tool_executor=tool_executor)
    question = "华为最新的手机是哪一款？它的主要卖点是什么？"

    print(f"\n--- 问题: {question} ---")
    agent.run(question)
    print(f"\n[{time.time() - t0:5.1f}s] 结束")
