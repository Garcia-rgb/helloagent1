"""
第7章 第一步：30 秒体验 hello-agents 框架

这是教程 7.1.3 那段「快速开始」的可运行版。
它直接用 pip 装好的包，建一个最小对话智能体，看看框架替你做了什么。

跑法（在仓库根目录）：
    Hello-Agents\\.venv\\Scripts\\python.exe chapter7/quickstart.py
"""

from pathlib import Path

from dotenv import load_dotenv

# 显式指向你在前几章配好的 .env（Hello-Agents/ 下那一份）
ENV_FILE = Path(__file__).resolve().parent.parent / "Hello-Agents" / ".env"
load_dotenv(ENV_FILE)

from hello_agents import SimpleAgent, HelloAgentsLLM

# ---- 1. 建 LLM 实例：不传任何参数，看框架能不能自己认出来 ----
llm = HelloAgentsLLM()

print("=" * 56)
print("框架自动检测到的配置：")
print(f"  provider   = {llm.provider}")
print(f"  model      = {llm.model}")
print(f"  base_url   = {llm.base_url}")
print(f"  temperature= {llm.temperature}")
print("=" * 56)
print()

# ---- 2. 建一个最简智能体 ----
agent = SimpleAgent(
    name="AI助手",
    llm=llm,
    system_prompt="你是一个有用的AI助手，回答请简洁，不超过两句话。",
)

# ---- 3. 问它一句 ----
print("[第 1 轮]")
answer = agent.run("你好！请用一句话介绍你自己。")
print(f"回答：{answer}")
print()

# ---- 4. 再问一句，这次它会带上历史 ----
print("[第 2 轮]  注意这次它记得上一轮说了什么")
answer2 = agent.run("我刚才问了你什么？")
print(f"回答：{answer2}")
print()

# ---- 5. 看它自己维护的对话历史 ----
print("=" * 56)
print(f"对话历史共 {len(agent.get_history())} 条：")
for i, msg in enumerate(agent.get_history(), 1):
    preview = msg.content.replace("\n", " ")[:50]
    print(f"  {i}. [{msg.role}] {preview}...")
print("=" * 56)
