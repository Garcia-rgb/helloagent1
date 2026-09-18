"""
第 6 章 AutoGen 案例 —— 可运行验证版

教程原文件（Hello-Agents/code/chapter6/AutoGenDemo/autogen_software_team.py）
的代码逻辑一行没动，这里用 importlib 直接加载它，只做三件事：

  1. 显式加载 Hello-Agents/.env
  2. 把 UserProxyAgent 换成自动应答 —— 否则跑到第四轮会卡在
     "Enter your response: " 等人工输入
  3. 压掉 "Resolved model mismatch: deepseek-chat != deepseek-flash"
     这个每次模型调用都刷一遍的良性警告

跑完会打印四人团队从需求分析到代码审查的完整对话。

用 venv 跑（不要用系统 python，系统里没装 autogen）：
    Hello-Agents\\.venv\\Scripts\\python.exe chapter6/autogen_team.py
"""

import asyncio
import importlib.util
import sys
import warnings
from pathlib import Path
from typing import Any, cast

from autogen_agentchat.agents import UserProxyAgent
from dotenv import load_dotenv

try:
    # 运行时 sys.stdout 是 TextIOWrapper，有 reconfigure；
    # 但 typeshed 把它标注成 TextIO（没这个方法），所以静态检查会拦一下。
    cast(Any, sys.stdout).reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = Path(__file__).resolve().parent.parent   # 仓库根（本文件在 chapter6/ 下）
TUTORIAL = (
    HERE / "Hello-Agents" / "code" / "chapter6" / "AutoGenDemo"
    / "autogen_software_team.py"
)

# ---- 1. 加载环境变量 ----
load_dotenv(HERE / "Hello-Agents" / ".env")

# ---- 2. 压掉良性警告 ----
warnings.filterwarnings("ignore", message="Resolved model mismatch.*")

# ---- 3. 加载教程原文件 ----
# 原文件有 if __name__ == "__main__" 保护，加载进来不会自动开跑
if not TUTORIAL.exists():
    print(f"找不到教程文件：{TUTORIAL}")
    sys.exit(1)

_spec = importlib.util.spec_from_file_location("tut_autogen_team", TUTORIAL)
if _spec is None:
    raise RuntimeError(f"无法把教程文件当作 Python 模块解析：{TUTORIAL}")

# 转成 Any：模块是运行时动态加载的，静态分析看不到里面定义的函数
mod = cast(Any, importlib.util.module_from_spec(_spec))
sys.modules[_spec.name] = mod      # 登记进 sys.modules，模块内自省时要用

_loader = _spec.loader
if _loader is None:
    raise RuntimeError(f"教程文件没有可用的加载器：{TUTORIAL}")
_loader.exec_module(mod)

print(f"已加载教程模块：{TUTORIAL.name}", flush=True)

# ---- 4. 把 UserProxy 换成自动应答 ----
USER_PROXY_DESCRIPTION = """用户代理，负责以下职责：
1. 代表用户提出开发需求
2. 执行最终的代码实现
3. 验证功能是否符合预期
4. 提供用户反馈和建议

完成测试后请回复 TERMINATE。"""

_seen = {"n": 0}


def auto_input(prompt: str) -> str:
    """本来应该等人敲键盘，这里自动回一句。"""
    _seen["n"] += 1
    n = _seen["n"]
    if n <= 2:
        reply = "收到。请工程师按需求开始实现，实现完成后请代码审查员检查。"
    else:
        reply = "测试通过，功能符合预期。TERMINATE"
    print(f"\n[auto-input #{n}] 提示语：{prompt.strip()}", flush=True)
    print(f"[auto-input #{n}] 自动回复：{reply}", flush=True)
    return reply


def patched_create_user_proxy() -> Any:
    return UserProxyAgent(
        name="UserProxy",
        description=USER_PROXY_DESCRIPTION,
        input_func=auto_input,
    )


mod.create_user_proxy = patched_create_user_proxy

# ---- 5. 开跑 ----
if __name__ == "__main__":
    asyncio.run(mod.run_software_development_team())
