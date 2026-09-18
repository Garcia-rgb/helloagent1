# -*- coding: utf-8 -*-
"""第 7 章 7.3 · 三个核心接口（带详细注解版）

这份文件是把装好的包里那三个文件原样搬过来、逐行加注解：

    Hello-Agents\\.venv\\Lib\\site-packages\\hello_agents\\core\\message.py   (34 行)
    Hello-Agents\\.venv\\Lib\\site-packages\\hello_agents\\core\\config.py    (36 行)
    Hello-Agents\\.venv\\Lib\\site-packages\\hello_agents\\core\\agent.py     (46 行)

代码一字未改，只加了注释；另外在 3 处加了 `# type: ignore`，原因是框架源码本身
有类型瑕疵（pyright 会报红线），加注释只是让 IDE 安静，不影响运行。三处都在注解里标明了。

三个东西的关系，一句话：

    Message  聊天记录里的一条，最小单位
    Config   一堆默认值，理论上是全局配置（实际上目前没人读它，见下文）
    Agent    所有智能体的父类，规定了「必须有个 run()」

跑法：

    python chapter7\\run.py core_interfaces --mine
"""

import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel

# 下面这两个是「用」的时候才需要的，类定义本身不依赖它们：
#   os             → Config.from_env() 读环境变量
#   HelloAgentsLLM → Agent 基类的类型标注，以及演示里造实例
from hello_agents import HelloAgentsLLM


# ============================================================================
# 一、Message —— 一条消息
# ============================================================================
#
# 为什么要有这么个类，不直接用 {"role": "user", "content": "..."} 字典？
#
#   1. role 只能是四种，写成 Literal 后写错会被类型检查器当场抓住，
#      不用等发请求被服务端拒绝
#   2. 可以挂额外信息（metadata），比如这轮花了多少 token、是谁调的工具
#   3. 可以挂时间戳，方便回溯一局对话的顺序
#   4. 需要发给模型时再 to_dict() 转成 OpenAI 认的格式
#
# 继承 pydantic 的 BaseModel，意味着字段类型会被强制校验：
# 你给 content 传个数字进去，pydantic 会尝试转字符串，转不了就报错。

MessageRole = Literal["user", "assistant", "system", "tool"]
#          ↑ 四种角色，对应 OpenAI 那套：
#            user       用户说的
#            assistant  模型说的
#            system     人设 / 系统指令
#            tool       工具返回的结果（第 7.5 节的函数调用会用到）


class Message(BaseModel):
    """消息类 —— 对话历史里的一条记录"""

    content: str
    #       正文。就是你看到的那句「你好！我是一个AI助手」

    role: MessageRole
    #     谁说的。上面那四种之一，写别的会报错

    timestamp: datetime = None  # type: ignore[assignment]
    #          这条消息产生的时间。
    #          注意这里的写法有个小瑕疵：类型标的是 datetime，默认值却给了 None。
    #          pyright 会在这一行报红线（第 1 处 type: ignore）——
    #          严格说类型不一致，但因为下面的 __init__ 被重写了，
    #          实际创建时一定会传真正的 datetime 进来，所以永远不会取到 None。
    #          这是框架源码自己的问题，不是你写错了。

    metadata: Optional[Dict[str, Any]] = None
    #         额外信息的口袋，装什么都行（dict），默认空字典。
    #         框架自己目前没往里放东西，是留给你扩展用的。

    def __init__(self, content: str, role: MessageRole, **kwargs):
        # 为什么要重写 __init__？
        # 因为 pydantic 的 BaseModel 不会自动帮你填「当前时间」——
        # 字段默认值必须在类定义时就写死一个值，而 datetime.now() 每时每刻都不一样。
        # 所以作者手动重写，在每次创建时现取时间。
        super().__init__(
            content=content,
            role=role,
            timestamp=kwargs.get("timestamp", datetime.now()),
            #       没传就自动填当前时间，传了就用你的
            metadata=kwargs.get("metadata", {}),
            #       没传就填空字典
        )

    def to_dict(self) -> Dict[str, Any]:
        """转成 OpenAI API 认的格式"""
        return {
            "role": self.role,
            "content": self.content,
        }
        # 注意：只带这两个键。
        # timestamp 和 metadata 是你自己记着用的，发给模型没意义（它还多占 token）。

    def __str__(self) -> str:
        return f"[{self.role}] {self.content}"
        # 这就是你跑 c7_1_hello.py 时看到的那个历史列表格式：
        #   1. [user] 你好！请用一句话介绍你自己。
        #   2. [assistant] 你好！我是一个AI助手...


# ============================================================================
# 二、Config —— 配置
# ============================================================================
#
# 一个纯数据类，就是一堆带默认值的字段。
#
# 但有个要说清楚的事实：我把整个 hello_agents 包 grep 了一遍，
# `self.config.xxx` 这个写法一次都没出现过。也就是说——
#
#     Config 在 0.1.1 版本里是个空壳，基类收下存着，没有任何代码真的读它。
#
# 真正在生效的配置其实是两条独立的路：
#     模型 / 密钥 / 地址  →  HelloAgentsLLM.__init__ 里直接读环境变量
#     temperature 等      →  HelloAgentsLLM.__init__ 的形参默认值
#
# 所以你不用花时间研究 Config 每个字段是什么意思，
# 知道有这么个东西、基类签名里有它就行。它更像是作者预留的位置。


class Config(BaseModel):
    """HelloAgents 配置类"""

    # ---- LLM 配置（注意：这几个字段目前没人读）----
    default_model: str = "gpt-3.5-turbo"
    #                    默认模型名。实际生效的是环境变量 LLM_MODEL_ID，
    #                    你 .env 里写的是 deepseek-chat，跟这里无关。

    default_provider: str = "openai"
    #                       默认服务商。实际生效的是 _auto_detect_provider() 的返回值，
    #                       你机器上是 deepseek。

    temperature: float = 0.7
    #                   温度。HelloAgentsLLM 自己也有一份同名参数，默认也是 0.7，
    #                   两边没打通 —— 改这里不会影响模型调用。

    max_tokens: Optional[int] = None
    #                          最大输出 token 数，不限制就 None。同样没人读。

    # ---- 系统配置 ----
    debug: bool = False
    #            调试开关。下面 from_env() 会去读环境变量 DEBUG

    log_level: str = "INFO"
    #                日志级别。from_env() 会去读环境变量 LOG_LEVEL

    # ---- 其他 ----
    max_history_length: int = 100
    #                        历史记录最多存多少条。
    #                        看着应该要截断 _history，但 Agent 基类里没实现这个逻辑，
    #                        所以目前写 100 和写 10000 效果一样。

    @classmethod
    def from_env(cls) -> "Config":
        """从环境变量创建配置"""
        # @classmethod 意味着不用先造实例，直接 Config.from_env() 就能调，
        # 它内部自己 cls(...) 造一个新实例返回。
        return cls(
            debug=os.getenv("DEBUG", "false").lower() == "true",
            #      读不到就当 false；.lower() 是为了兼容写成 "True" / "TRUE"
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            temperature=float(os.getenv("TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("MAX_TOKENS")) if os.getenv("MAX_TOKENS") else None,  # type: ignore[arg-type]
            #          这行的三元写法是为了处理「没设置就不填」，
            #          直接 int(None) 会崩。
            #          pyright 在这里报红线（第 2 处 type: ignore）：
            #          os.getenv() 的类型是 str | None，它看不出前面
            #          `if os.getenv(...)` 已经挡住了 None（两次调用被当成两个值）。
            #          同样是框架源码的类型瑕疵，运行时没问题。
        )
        # 注意：这里只读了 4 个环境变量，
        # default_model 和 default_provider 不从环境读，所以它们永远是写死的那些值。

    def to_dict(self) -> Dict[str, Any]:
        """转成字典"""
        return self.dict()
        #          ↑ pydantic v2 里 .dict() 已经标记废弃，推荐写 .model_dump()。
        #            目前还能用，只是会有一条 DeprecationWarning。


# ============================================================================
# 三、Agent —— 所有智能体的父类
# ============================================================================
#
# 这是本章最核心的一个类。它做三件事：
#
#   1. 规定子类必须实现 run()        ← 用 @abstractmethod 强制
#   2. 替所有子类保管对话历史         ← _history + 三个方法
#   3. 统一持有 llm / name / 人设     ← 子类不用各自再写一遍
#
# 它唯一不做的，是「具体怎么回答」——那是 7.4 五个子类各自的事。


class Agent(ABC):
    """Agent 基类"""

    # ABC = Abstract Base Class，抽象基类。
    # 继承它的类，只要还有 @abstractmethod 没实现，就不能被实例化。

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
    ):
        self.name = name
        #          智能体的名字。只用于显示和日志，框架内部不靠它做事。

        self.llm = llm
        #         重点：这里收的是**已经造好的** HelloAgentsLLM 实例，
        #         不是让你传个模型名进来让基类自己去造。
        #         所以顺序永远是：你先 HelloAgentsLLM()，再把它塞给 Agent。

        self.system_prompt = system_prompt
        #                    人设 / 系统提示词，可以没有。
        #                    注意基类只是存着，怎么用是子类 run() 的事。

        self.config = config or Config()
        #                      没传就造个默认的。前面说了，这份 config 目前没人读。

        self._history: list[Message] = []
        #             对话历史，元素是 Message。
        #             下划线开头是 Python 的约定：内部用的，别从外面直接改。
        #             要读写请用下面那三个方法。

    @abstractmethod
    def run(self, input_text: str, **kwargs) -> str:
        """运行 Agent —— 子类必须重写这个方法"""
        pass
        # 这里只有 pass，没有任何实现。
        # 子类不重写就实例化，Python 会直接抛：
        #     TypeError: Can't instantiate abstract class Xxx
        #     with abstract method run
        #
        # 签名是死的：输入一个字符串，输出一个字符串。
        # 中间是调一次模型、还是循环十次、还是先搜再答，基类一概不管。

    # ---- 历史管理三件套 ----

    def add_message(self, message: Message):
        """往历史里追加一条消息"""
        self._history.append(message)

    def clear_history(self):
        """清空历史"""
        self._history.clear()

    def get_history(self) -> list[Message]:
        """取历史记录"""
        return self._history.copy()
        #                    ↑ 返回副本，不是本体。
        #                      这样你在外面随便改这个列表，都影响不到智能体内部。
        #                      不这么做的话，外部一句 .clear() 就把历史清空了。

    def __str__(self) -> str:
        return f"Agent(name={self.name}, provider={self.llm.provider})"
        #                                         ↑ 直接从 llm 上取，
        #                                           所以打印一个 Agent 就能看出它连的是哪家

    def __repr__(self) -> str:
        return self.__str__()


# ============================================================================
# 四、三者怎么串起来（可运行演示）
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("7.3 三个核心接口 · 演示")
    print("=" * 60)

    # ---- 演示 1：Message ----
    print("\n【1】Message —— 一条消息")
    print("-" * 60)

    m1 = Message(content="你好！请用一句话介绍你自己。", role="user")
    m2 = Message(content="你好！我是一个AI助手。", role="assistant")

    print(f"m1 = {m1}")
    print(f"m2 = {m2}")
    print(f"\nm1 的角色     : {m1.role}")
    print(f"m1 的时间戳   : {m1.timestamp}")
    print(f"m1 的附加信息 : {m1.metadata}")
    print(f"\n发给模型的格式: {m1.to_dict()}")
    print("              ↑ 只有 role 和 content，timestamp / metadata 不会发出去")

    # 演示 role 写错会怎样
    try:
        bad = Message(content="写错了", role="guest")  # type: ignore[arg-type]
        print(f"\nrole=guest 居然通过了？{bad}")
    except Exception as e:
        print(f"\nrole 写成 'guest' → {type(e).__name__}")
        print("（pydantic 在运行时也会校验 Literal，运行时同样拦得住）")

    # ---- 演示 2：Config ----
    print("\n【2】Config —— 配置")
    print("-" * 60)

    cfg = Config()
    print("（下一行前会冒出一条 PydanticDeprecatedSince20 警告，")
    print("  那是 pydantic 在提醒 .dict() 已废弃、该写 .model_dump()，")
    print("  属于框架自己的代码问题，不是你写错了）")
    print(f"默认配置: {cfg.to_dict()}")
    print("\n注意 default_model 是 gpt-3.5-turbo，但你实际用的是 deepseek-chat ——")
    print("因为真正生效的是环境变量 LLM_MODEL_ID，Config 这几个字段没人读。")

    # ---- 演示 3：Agent 基类 + 自己实现 run() ----
    print("\n【3】Agent 基类 —— 继承并实现 run()")
    print("-" * 60)

    class EchoAgent(Agent):
        """一个最简单的子类：不调模型，原样把输入包一层返回。

        这样演示是为了零成本——不烧 API 调用，也能看清基类的历史机制。
        """

        def run(self, input_text: str, **kwargs) -> str:
            # 第一步：把用户这句话记进历史
            self.add_message(Message(content=input_text, role="user"))

            # 第二步：干活（这里用假实现代替真正的模型调用）
            reply = f"[{self.name} 收到] 你说的是：{input_text}"

            # 第三步：把回复也记进历史
            self.add_message(Message(content=reply, role="assistant"))

            # 第四步：返回字符串
            return reply

    # 造一个假的 llm 传进去（基类只是存着，EchoAgent 不用它）
    fake_llm = HelloAgentsLLM()
    agent = EchoAgent(name="小回", llm=fake_llm, system_prompt="你是个回声")

    print(f"智能体: {agent}")
    print("        ↑ __str__ 直接把 llm.provider 打出来了，能看出连的是哪家\n")

    print(agent.run("你好"))
    print(agent.run("我刚才说了什么？"))

    print(f"\n历史共 {len(agent.get_history())} 条：")
    for i, msg in enumerate(agent.get_history(), 1):
        print(f"  {i}. {msg}")

    # get_history 返回的是副本，验证一下
    h = agent.get_history()
    h.clear()
    print(f"\n外部把拿到的列表 clear() 之后，智能体内部还剩 {len(agent.get_history())} 条")
    print("↑ 因为 get_history() 返回的是 .copy()，改外面的不影响里面")

    agent.clear_history()
    print(f"调用 clear_history() 之后：{len(agent.get_history())} 条")

    # ---- 演示 4：忘了实现 run() 会怎样 ----
    print("\n【4】如果子类忘了写 run()")
    print("-" * 60)

    class BrokenAgent(Agent):
        pass  # 故意不实现 run

    try:
        BrokenAgent(name="坏的", llm=fake_llm)  # type: ignore[abstract]
        # ↑ 第 3 处 type: ignore：这里是**故意**要它报错的，
        #   pyright 在写代码时就能看出这个类缺 run()，所以标红是正确行为。
        print("居然造出来了？不应该")
    except TypeError as e:
        print(f"TypeError: {e}")
        print("\n这就是抽象基类的作用——把「必须实现什么」变成硬约束。")

    print("\n" + "=" * 60)
    print("演示结束。7.4 你要写的五个 Agent，都是继承这个基类、只重写 run()。")
    print("=" * 60)
