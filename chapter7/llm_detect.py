# -*- coding: utf-8 -*-
"""7.2 HelloAgentsLLM 扩展 —— 两件事的可视化

[1] provider 是怎么被自动检测出来的（纯判断，不发任何网络请求）
[2] 继承 + 重写 __init__ 是怎么加进一个自己的 provider 的

跑法（仓库根目录）：

    python chapter7\\run.py llm_detect --mine

或直接：

    Hello-Agents\\.venv\\Scripts\\python.exe chapter7\\llm_detect.py
"""
import os
from pathlib import Path
from typing import Any, Optional, cast

from dotenv import load_dotenv
from openai import OpenAI
from hello_agents import HelloAgentsLLM

ENV_FILE = Path(__file__).resolve().parent.parent / "Hello-Agents" / ".env"
load_dotenv(ENV_FILE, override=False)

LINE = "-" * 68
# 判定第一优先级会读的专属环境变量（见 hello_agents/core/llm.py:84-99）
PROVIDER_ENV_KEYS = [
    "OPENAI_API_KEY", "DEEPSEEK_API_KEY", "DASHSCOPE_API_KEY", "MODELSCOPE_API_KEY",
    "KIMI_API_KEY", "MOONSHOT_API_KEY", "ZHIPU_API_KEY", "GLM_API_KEY",
    "OLLAMA_API_KEY", "OLLAMA_HOST", "VLLM_API_KEY", "VLLM_HOST",
]


def head(num: str, title: str) -> None:
    print(f"\n[{num}] {title}")
    print(LINE)


def suspend_provider_env() -> dict:
    """暂时摘掉所有 provider 专属环境变量，让后面几组判定能走到 base_url 那一层。

    只在进程内动 os.environ，退出前 restore 会原样放回去。
    """
    saved = {k: os.environ.pop(k) for k in PROVIDER_ENV_KEYS if k in os.environ}
    return saved


def restore_provider_env(saved: dict) -> None:
    os.environ.update(saved)


head("1", "当前实例：一个参数都不传，框架自己填了什么")
llm = HelloAgentsLLM()
print(f"provider    = {llm.provider}")
print(f"model       = {llm.model}")
print(f"base_url    = {llm.base_url}")
print(f"temperature = {llm.temperature}")
print(f"timeout     = {llm.timeout}")

present = [k for k in PROVIDER_ENV_KEYS if os.getenv(k)]
print()
print(f"命中了专属环境变量：{present or '（无）'}")
print("判定顺序：专属环境变量 > 密钥格式 > base_url 域名 > 默认 auto")
print("只要第一层命中，后面几层根本不会执行。")


CASES = [
    (None, "https://api.deepseek.com/v1"),
    (None, "https://api.openai.com/v1"),
    (None, "https://api-inference.modelscope.cn/v1/"),
    (None, "https://open.bigmodel.cn/api/paas/v4/"),
    (None, "https://dashscope.aliyuncs.com/compatible-mode/v1"),
    (None, "http://localhost:11434/v1"),
    (None, "http://127.0.0.1:8000/v1"),
    (None, "http://localhost:9000/v1"),
    ("ms-abc123", None),
    ("ollama", None),
    (None, None),
]


def show_cases(detector) -> None:
    print(f"{'api_key':<12} {'base_url':<48} -> provider")
    for key, url in CASES:
        print(f"{str(key):<12} {str(url):<48} -> {detector(key, url)}")


head("2", "A 组：当前环境 —— 第一层就命中，全被压成同一个结果")
show_cases(llm._auto_detect_provider)

head("3", "B 组：临时摘掉专属环境变量 —— 才看得到下面几层")
saved = suspend_provider_env()
os.environ["OLLAMA_HOST"] = "http://localhost:11434"   # 演示环境变量依旧最优先
print("(另外临时设了 OLLAMA_HOST)")
print()
show_cases(llm._auto_detect_provider)

del os.environ["OLLAMA_HOST"]
print()
print("只摘环境变量、不额外设 OLLAMA_HOST：")
print()
show_cases(llm._auto_detect_provider)
restore_provider_env(saved)
print()
print("（环境变量已还原，后面的调用回到 A 组的状态）")


head("4", "继承扩展：不动库的源码，加一个自己的 provider")


class MyLLM(HelloAgentsLLM):
    """只接管 provider == 'mycompany'，其余一律丢回父类。"""

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        provider: Optional[str] = None,
        **kwargs,
    ):
        if provider == "mycompany":
            print("  [MyLLM] 命中自定义分支，父类逻辑完全不执行")
            self.provider = "mycompany"
            self.api_key = api_key or os.getenv("MYCOMPANY_API_KEY") or "dummy"
            self.base_url = base_url or "http://10.0.0.1:9000/v1"
            self.model = model or os.getenv("LLM_MODEL_ID") or "internal-7b"
            self.temperature = kwargs.get("temperature", 0.7)
            self.max_tokens = kwargs.get("max_tokens")
            self.timeout = kwargs.get("timeout", 60)
            self.kwargs = kwargs
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        else:
            print("  [MyLLM] 不是 mycompany，走 super().__init__() 交还父类")
            # 父类的 provider 参数是 Literal 联合类型，这里的值可能是任意字符串，
            # cast 一下让静态检查放过（运行时不影响）
            super().__init__(
                model=model,
                api_key=api_key,
                base_url=base_url,
                provider=cast(Any, provider),
                **kwargs,
            )


print()
print("a) 用自己新加的 provider：")
mine = MyLLM(provider="mycompany")
print(f"   provider={mine.provider}  model={mine.model}  base_url={mine.base_url}")

print()
print("b) 用内置的 deepseek，invoke 是从父类继承来的、一行没重写：")
real = MyLLM(provider="deepseek")
answer = real.invoke([{"role": "user", "content": "只回答一个数字，不要解释：365 * 2 ="}])
print(f"   回答：{answer}")

print()
print("c) 不传 provider，让它自己检测：")
auto = MyLLM()
print(f"   检测到 provider = {auto.provider}")

print()
print("d) 对照：教程 my_llm.py 把默认值写成 provider='auto' 会怎样：")


class TutorialLLM(HelloAgentsLLM):
    """照抄教程那份的签名：provider 默认 'auto'。"""

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        provider: Optional[str] = "auto",
        **kwargs,
    ):
        super().__init__(
            model=model,
            api_key=api_key,
            base_url=base_url,
            provider=cast(Any, provider),
            **kwargs,
        )


tut = TutorialLLM()
print(f"   provider = {tut.provider}   <- 父类写的是 `provider or 自动检测()`")
print("   'auto' 是非空字符串，被当成真值，自动检测那条路被短路了。")
print("   想保留自动检测，默认值要写 None。")

print()
print(LINE)
print("要点：MyLLM 只写了 20 行，内置的全部能力（自动检测、凭证解析、")
print("invoke / think / stream_invoke）一个都没丢 —— 全靠 else 分支那句 super()。")
