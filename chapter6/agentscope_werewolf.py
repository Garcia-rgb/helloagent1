# -*- coding: utf-8 -*-
"""
三国狼人杀 —— 基于 AgentScope 的单文件完整版

这份文件是教程第 6 章 6.3 节「三国狼人杀」案例的补全版。
文档里给的是一堆代码片段（werewolf_phase、结构化模型、角色提示词、白天投票），
这里把缺的部分补齐，合成一个可以直接跑起来的单文件。

和教程原版的四处差别，都是为了能在本机跑通：

  1. 模型走 DeepSeek，不需要 DASHSCOPE_API_KEY
       OpenAIChatModel + client_args={"base_url": ...}（OpenAI 兼容协议）
       formatter 用 DeepSeekMultiAgentFormatter（AgentScope 1.0.2 自带）

  2. 角色提示词里不再要求「正文输出 JSON」
       AgentScope 1.0.2 的结构化输出走的是工具调用（finish function = generate_response），
       在正文里手写 JSON 反而会让模型不去调那个工具，metadata 永远是空的。

  3. 结构化字段都给了默认值，模型少填一个字段不会整轮失败。

  4. 目标名做了一次对齐（模型写「关羽（狼人）」也能匹配到「关羽」），
     对不上就随机兜底，避免因为一个错字让整晚空过。

一条已知的无害噪音，别被它骗到：

    运行时会刷很多行  Error in block input ['response']
                     Error in block input ['target']   之类

  这不是报错。那是 AgentScope 自己的一个「打印钩子」
  （agentscope/agent/_react_agent.py:20 的 finish_function_pre_print_hook），
  它的作用是：当模型调用 generate_response 时，把这次工具调用显示成一段普通发言，
  而不是一个工具调用框。实现方式是取 block["input"].get("response") —— 但在流式
  输出过程中 block["input"] 还没有拼成字典，取 .get 就抛异常，于是它自己 print 一行。
  实测：工具调用完全成功、metadata 也正常回填的情况下，这行照样会打（每次调用打两遍）。
  所以看到它就当没看见。真正需要留意的是 pydantic 的
  "Arguments Validation Error: ..."，那才是模型填错了字段、被要求重填。

跑法（用 venv，不要用系统 python）：

    Hello-Agents\\.venv\\Scripts\\python.exe chapter6/agentscope_werewolf.py        # 默认 6 人局
    Hello-Agents\\.venv\\Scripts\\python.exe chapter6/agentscope_werewolf.py 8      # 8 人局

模型配置读 Hello-Agents/.env 里的 LLM_MODEL_ID / LLM_API_KEY / LLM_BASE_URL。
"""

import asyncio
import os
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Sequence, cast

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from agentscope.agent import AgentBase, ReActAgent
from agentscope.formatter import (
    DeepSeekMultiAgentFormatter,
    OpenAIMultiAgentFormatter,
)
from agentscope.message import Msg
from agentscope.model import OpenAIChatModel
from agentscope.pipeline import MsgHub, fanout_pipeline, sequential_pipeline

# ============================================================ 环境与常量

HERE = Path(__file__).resolve().parent.parent   # 仓库根（本文件在 chapter6/ 下）
load_dotenv(HERE / "Hello-Agents" / ".env")

MAX_GAME_ROUND = 10         # 最多打几轮（一般 2~3 轮就分出胜负）
MAX_DISCUSSION_ROUND = 3    # 每晚狼人内部讨论几轮
REACT_MAX_ITERS = 3         # 单次发言最多让模型来回几次，防止一句话烧十次调用

CHINESE_NAMES = [
    "刘备", "关羽", "张飞", "诸葛亮", "赵云",
    "曹操", "司马懿", "典韦", "许褚", "夏侯惇",
    "孙权", "周瑜", "陆逊", "甘宁", "太史慈",
    "吕布", "貂蝉", "董卓", "袁绍", "袁术",
]

CHARACTER_TRAITS = {
    "刘备": "仁德宽厚，善于团结众人，说话温和有礼",
    "关羽": "忠义刚烈，言辞直接，重情重义",
    "张飞": "性格豪爽，说话大声直接，容易冲动",
    "诸葛亮": "智慧超群，分析透彻，言辞谨慎",
    "赵云": "忠勇双全，话语简洁有力",
    "曹操": "雄才大略，善于权谋，话语犀利",
    "司马懿": "深谋远虑，城府极深，言辞含蓄",
    "周瑜": "才华横溢，略显傲气，分析精准",
    "孙权": "年轻有为，善于决断，话语果决",
}


# ============================================================ 角色定义

class GameRoles:
    """游戏角色管理类"""

    ROLES = {
        "狼人": {
            "description": "狼人",
            "ability": "夜晚可以击杀一名玩家",
            "team": "狼人阵营",
        },
        "预言家": {
            "description": "预言家",
            "ability": "每晚可以查验一名玩家的身份",
            "team": "好人阵营",
        },
        "女巫": {
            "description": "女巫",
            "ability": "拥有解药和毒药各一瓶，可以救人或杀人",
            "team": "好人阵营",
        },
        "猎人": {
            "description": "猎人",
            "ability": "出局时可以开枪带走一名玩家",
            "team": "好人阵营",
        },
        "村民": {
            "description": "村民",
            "ability": "无特殊技能，依靠推理和投票",
            "team": "好人阵营",
        },
        "守护者": {
            "description": "守护者",
            "ability": "每晚可以守护一名玩家免受狼人攻击",
            "team": "好人阵营",
        },
    }

    @classmethod
    def get_role_desc(cls, role: str) -> str:
        return cls.ROLES.get(role, {}).get("description", "未知角色")

    @classmethod
    def get_role_ability(cls, role: str) -> str:
        return cls.ROLES.get(role, {}).get("ability", "无特殊技能")

    @classmethod
    def is_werewolf(cls, role: str) -> bool:
        return role == "狼人"

    @classmethod
    def get_standard_setup(cls, player_count: int) -> List[str]:
        """标准局角色配置"""
        if player_count == 6:
            return ["狼人", "狼人", "预言家", "女巫", "村民", "村民"]
        if player_count == 8:
            return ["狼人", "狼人", "狼人", "预言家", "女巫", "猎人", "村民", "村民"]
        if player_count == 9:
            return ["狼人", "狼人", "狼人", "预言家", "女巫", "猎人", "守护者", "村民", "村民"]

        # 非标准人数：约 1/3 狼人，剩下的依次配神职，最后补村民
        werewolf_count = max(1, player_count // 3)
        roles = ["狼人"] * werewolf_count
        remaining = player_count - werewolf_count
        for role in ("预言家", "女巫", "猎人"):
            if remaining >= 1:
                roles.append(role)
                remaining -= 1
        roles.extend(["村民"] * remaining)
        return roles


# ============================================================ 角色提示词

def get_role_prompt(role: str, character: str) -> str:
    """获取角色提示词 - 融合游戏规则与人物性格"""
    trait = CHARACTER_TRAITS.get(character, "性格温和，说话得体")

    base_prompt = f"""你是{character}，在这场三国狼人杀游戏中扮演{role}。

    重要规则：
    1. 不要调用任何外部工具
    2. 需要提交结构化结果时调用 generate_response，只填下面列出的字段，
       不要传名为 response 的参数（传了会校验失败、白白多花一次调用）：
           狼人夜聊    speech / reach_agreement / confidence_level / key_evidence
           白天投票    vote / reason / suspicion_level
           狼人击杀    target / kill_strategy / team_coordination
           预言家查验  target / check_reason / priority_level
           女巫行动    use_antidote / use_poison / target_name / action_reason
       不要在正文里手写 JSON
    3. 每次发言都要简短，两三句话即可，以{character}的口吻说话

    你的性格：{trait}

    角色特点：
    """

    if role == "狼人":
        return base_prompt + f"""
    - 你是狼人阵营，目标是消灭所有好人
    - 夜晚可以与其他狼人协商击杀目标
    - 白天要隐藏身份，误导好人
    - 以{character}的性格说话和行动
    """
    if role == "预言家":
        return base_prompt + f"""
    - 你是好人阵营的预言家，目标是找出所有狼人
    - 每晚可以查验一名玩家的真实身份
    - 要合理公布查验结果，引导好人投票
    - 以{character}的智慧和洞察力分析局势
    """
    if role == "女巫":
        return base_prompt + f"""
    - 你是好人阵营的女巫，拥有解药和毒药各一瓶
    - 解药可以救活被狼人击杀的玩家，毒药可以毒杀一名玩家
    - 要谨慎使用道具，在关键时刻发挥作用
    - 以{character}的谨慎与果断行事
    """
    if role == "猎人":
        return base_prompt + f"""
    - 你是好人阵营的猎人
    - 被投票出局或被狼人击杀时可以开枪带走一名玩家
    - 要在关键时刻使用技能，带走狼人
    - 以{character}的勇猛和决断力行动
    """
    if role == "守护者":
        return base_prompt + f"""
    - 你是好人阵营的守护者
    - 每晚可以守护一名玩家免受狼人攻击
    - 优先守护你认为重要的好人
    - 以{character}的沉稳守护队友
    """

    # 村民
    return base_prompt + f"""
    - 你是好人阵营的村民
    - 没有特殊技能，只能通过推理和投票
    - 要仔细观察，找出狼人的破绽
    - 以{character}的性格参与讨论
    """


# ============================================================ 结构化输出模型

class DiscussionModelCN(BaseModel):
    """讨论阶段的输出格式"""
    reach_agreement: bool = Field(
        description="是否已达成一致意见",
        default=False,
    )
    speech: str = Field(
        description="你在讨论中要说的话（中文，两三句）",
        default="",
    )
    confidence_level: int = Field(
        description="对当前推理的信心程度(1-10)",
        ge=1, le=10,
        default=5,
    )
    key_evidence: Optional[str] = Field(
        description="支持你观点的关键证据",
        default=None,
    )


class WerewolfKillModelCN(BaseModel):
    """中文版狼人击杀模型"""
    target: str = Field(
        description="要击杀的玩家姓名，必须是存活玩家里的名字",
        default="",
    )
    kill_strategy: str = Field(
        description="击杀策略说明",
        default="",
    )
    team_coordination: Optional[str] = Field(
        description="与狼队友的配合计划",
        default=None,
    )


class WitchActionModelCN(BaseModel):
    """女巫行动的输出格式"""
    use_antidote: bool = Field(description="是否使用解药救人", default=False)
    use_poison: bool = Field(description="是否使用毒药杀人", default=False)
    target_name: Optional[str] = Field(
        description="毒药目标玩家姓名（不解药就留空）",
        default=None,
    )
    action_reason: Optional[str] = Field(description="行动理由", default=None)


def get_vote_model_cn(agents: Sequence[ReActAgent]) -> type[BaseModel]:
    """获取中文版投票模型（用 Literal 把可选目标钉死，模型不能乱写名字）"""

    class VoteModelCN(BaseModel):
        """中文版投票输出格式"""
        vote: Literal[tuple(_.name for _ in agents)] = Field(  # type: ignore
            description="你要投票淘汰的玩家姓名",
        )
        reason: str = Field(
            description="投票理由，简要说明为什么选择此人",
            default="",
        )
        suspicion_level: int = Field(
            description="对被投票者的怀疑程度(1-10)",
            ge=1, le=10,
            default=5,
        )

    return VoteModelCN


def get_seer_model_cn(agents: Sequence[ReActAgent]) -> type[BaseModel]:
    """获取中文版预言家模型"""

    class SeerModelCN(BaseModel):
        """中文版预言家查验格式"""
        target: Literal[tuple(_.name for _ in agents)] = Field(  # type: ignore
            description="要查验的玩家姓名",
        )
        check_reason: str = Field(description="查验此人的原因", default="")
        priority_level: int = Field(
            description="查验优先级(1-10)",
            ge=1, le=10,
            default=5,
        )

    return SeerModelCN


def get_hunter_model_cn(agents: Sequence[ReActAgent]) -> type[BaseModel]:
    """获取中文版猎人模型"""

    class HunterModelCN(BaseModel):
        """中文版猎人开枪格式"""
        shoot: bool = Field(description="是否使用开枪技能", default=False)
        target: Optional[str] = Field(
            description="开枪目标玩家姓名，放弃就留空",
            default=None,
        )
        shoot_reason: Optional[str] = Field(description="开枪理由", default=None)

    return HunterModelCN


# ============================================================ 工具函数

def get_chinese_name(character: Optional[str] = None) -> str:
    """获取中文角色名"""
    if character and character in CHINESE_NAMES:
        return character
    return random.choice(CHINESE_NAMES)


def format_player_list(players: Sequence[ReActAgent], show_roles: bool = False) -> str:
    """格式化玩家列表为中文显示"""
    if not players:
        return "无玩家"
    if show_roles:
        return "、".join(f"{p.name}" for p in players)
    return "、".join(p.name for p in players)


def as_agent_list(players: Sequence[ReActAgent]) -> List[AgentBase]:
    """转给 AgentScope 的 pipeline 用。

    它的签名写的是 list[AgentBase]，而 list 的类型参数是不变的（invariant），
    直接传 list[ReActAgent] 会被静态检查拦下。运行期本来就是子类，转一次即可。
    """
    return cast(List[AgentBase], list(players))


def format_player_list_str(players: Sequence[str]) -> str:
    """格式化玩家姓名列表"""
    if not players:
        return "无人"
    return "、".join(players)


def majority_vote_cn(votes: Dict[str, str]) -> tuple:
    """中文版多数投票统计，返回 (得票最高的目标, 票数)"""
    if not votes:
        return "无人", 0
    vote_counts = Counter(votes.values())
    most_voted = vote_counts.most_common(1)[0]
    return most_voted[0], most_voted[1]


def check_winning_cn(alive_players: Sequence[ReActAgent], roles: Dict[str, str]) -> Optional[str]:
    """检查中文版游戏胜利条件"""
    alive_roles = [roles.get(p.name, "村民") for p in alive_players]
    werewolf_count = alive_roles.count("狼人")
    villager_count = len(alive_roles) - werewolf_count

    if werewolf_count == 0:
        return "好人阵营胜利！所有狼人已被淘汰！"
    if werewolf_count >= villager_count:
        return "狼人阵营胜利！狼人数量已达到或超过好人！"
    return None


def resolve_target(raw: Any, candidates: List[str]) -> Optional[str]:
    """把模型写出的目标名对齐到真实玩家名。

    模型经常写「关羽（狼人）」「关羽 」甚至「我认为是关羽」，
    直接拿字符串去查表必然查不到，所以这里做一次模糊对齐：
    先精确匹配，再包含匹配，都对不上返回 None（由调用方决定兜底）。
    """
    if not raw or not candidates:
        return None

    text = str(raw).strip()
    if text in candidates:
        return text

    # 包含匹配：取最长的那个命中，避免「张」同时命中「张飞」「张辽」
    hits = [name for name in candidates if name in text]
    if hits:
        return max(hits, key=len)
    return None


def meta_of(msg: Optional[Msg]) -> Dict[str, Any]:
    """安全取出结构化输出。

    AgentScope 把结构化结果放在 Msg.metadata（dict）。
    模型没调 generate_response 时 metadata 是空的，这里统一成 {}，
    调用方用 .get(...) 就不会炸。
    """
    if msg is None:
        return {}
    metadata = getattr(msg, "metadata", None)
    return metadata if isinstance(metadata, dict) else {}


class GameModerator(AgentBase):
    """中文版游戏主持人"""

    def __init__(self) -> None:
        super().__init__()
        self.name = "游戏主持人"
        self.game_log: List[str] = []

    async def announce(self, content: str) -> Msg:
        """发布游戏公告"""
        msg = Msg(
            name=self.name,
            content=f"📢 {content}",
            role="system",
        )
        self.game_log.append(content)
        await self.print(msg)
        return msg

    async def night_announcement(self, round_num: int) -> Msg:
        return await self.announce(f"🌙 第{round_num}夜降临，天黑请闭眼...")

    async def day_announcement(self, round_num: int) -> Msg:
        return await self.announce(f"☀️ 第{round_num}天天亮了，请大家睁眼...")

    async def death_announcement(self, dead_players: List[str]) -> Msg:
        if not dead_players:
            content = "昨夜平安无事，无人死亡。"
        else:
            content = f"昨夜，{format_player_list_str(dead_players)}不幸遇害。"
        return await self.announce(content)

    async def vote_result_announcement(self, voted_out: str, vote_count: int) -> Msg:
        return await self.announce(f"投票结果：{voted_out}以{vote_count}票被淘汰出局。")

    async def game_over_announcement(self, winner: str) -> Msg:
        return await self.announce(f"🎉 游戏结束！{winner}")


# ============================================================ 模型工厂

def build_model() -> OpenAIChatModel:
    """按 .env 造模型客户端。

    OpenAIChatModel 走的是 OpenAI 兼容协议 —— 类名叫 OpenAI，但 base_url
    指向谁就发给谁。这里指向 DeepSeek，不需要 OpenAI 账号。
    """
    api_key = os.getenv("LLM_API_KEY")
    model_id = os.getenv("LLM_MODEL_ID", "deepseek-chat")
    base_url = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")

    if not api_key:
        raise ValueError(
            "没读到 LLM_API_KEY。请确认 Hello-Agents/.env 里有：\n"
            "  LLM_MODEL_ID=deepseek-chat\n"
            "  LLM_API_KEY=sk-你的密钥\n"
            "  LLM_BASE_URL=https://api.deepseek.com/v1"
        )

    print(f"🤖 模型：{model_id} @ {base_url}")
    return OpenAIChatModel(
        model_name=model_id,
        api_key=api_key,
        client_args={"base_url": base_url},
    )


def build_formatter():
    """DeepSeek 有专用 formatter（多智能体场景下消息合并规则不一样），其它走 OpenAI。"""
    base_url = (os.getenv("LLM_BASE_URL") or "").lower()
    if "deepseek" in base_url:
        return DeepSeekMultiAgentFormatter()
    return OpenAIMultiAgentFormatter()


# ============================================================ 游戏主类

class ThreeKingdomsWerewolfGame:
    """三国狼人杀游戏主类"""

    def __init__(self, player_count: int = 6) -> None:
        self.player_count = player_count

        self.players: Dict[str, ReActAgent] = {}
        self.roles: Dict[str, str] = {}
        self.moderator = GameModerator()
        self.alive_players: List[ReActAgent] = []
        self.werewolves: List[ReActAgent] = []
        self.villagers: List[ReActAgent] = []
        self.seer: List[ReActAgent] = []
        self.witch: List[ReActAgent] = []
        self.hunter: List[ReActAgent] = []

        # 女巫道具状态
        self.witch_has_antidote = True
        self.witch_has_poison = True

        self.model = build_model()

    # -------------------------------------------------- 初始化

    async def create_player(self, role: str, character: str) -> ReActAgent:
        """创建具有三国背景的玩家"""
        name = get_chinese_name(character)
        self.roles[name] = role

        agent = ReActAgent(
            name=name,
            sys_prompt=get_role_prompt(role, character),
            model=self.model,
            # formatter 每个 agent 给一份，避免并发发言时互相干扰
            formatter=build_formatter(),
            max_iters=REACT_MAX_ITERS,
        )

        # 角色身份确认
        await agent.observe(
            await self.moderator.announce(
                f"【{name}】你在这场三国狼人杀中扮演{GameRoles.get_role_desc(role)}，"
                f"你的角色是{character}。{GameRoles.get_role_ability(role)}"
            )
        )

        self.players[name] = agent
        return agent

    async def setup_game(self) -> None:
        """设置游戏"""
        print(f"🎮 开始设置三国狼人杀游戏（{self.player_count} 人局）...")

        roles = GameRoles.get_standard_setup(self.player_count)
        characters = random.sample(CHINESE_NAMES, self.player_count)

        for role, character in zip(roles, characters):
            agent = await self.create_player(role, character)
            self.alive_players.append(agent)

            if role == "狼人":
                self.werewolves.append(agent)
            elif role == "预言家":
                self.seer.append(agent)
            elif role == "女巫":
                self.witch.append(agent)
            elif role == "猎人":
                self.hunter.append(agent)
            else:
                self.villagers.append(agent)

        await self.moderator.announce(
            f"三国狼人杀游戏开始！参与者：{format_player_list(self.alive_players)}"
        )
        print(f"✅ 游戏设置完成，共{len(self.alive_players)}名玩家")

    # -------------------------------------------------- 容错调用

    async def ask(
        self,
        agent: ReActAgent,
        structured_model: Optional[type[BaseModel]] = None,
        prompt: Optional[Msg] = None,
    ) -> Optional[Msg]:
        """带容错的调用：某个 agent 报错就当他这轮没说话，不让整局游戏挂掉"""
        try:
            if prompt is None:
                return await agent(structured_model=structured_model)
            return await agent(prompt, structured_model=structured_model)
        except Exception as e:  # noqa: BLE001
            print(f"⚠️ {agent.name} 调用出错：{type(e).__name__}: {e}")
            return None

    # -------------------------------------------------- 夜晚阶段

    async def werewolf_phase(self, round_num: int) -> Optional[str]:
        """狼人阶段 - 展示消息驱动的协作模式"""
        if not self.werewolves:
            return None

        await self.moderator.announce("🐺 狼人请睁眼，选择今晚要击杀的目标...")

        # 通过消息中心建立狼人专属通信频道
        async with MsgHub(
            as_agent_list(self.werewolves),
            enable_auto_broadcast=True,
            announcement=await self.moderator.announce(
                f"狼人们，请讨论今晚的击杀目标。存活玩家：{format_player_list(self.alive_players)}"
            ),
        ) as werewolves_hub:
            # 讨论阶段：狼人通过消息交换策略
            for _ in range(MAX_DISCUSSION_ROUND):
                for wolf in self.werewolves:
                    await self.ask(wolf, structured_model=DiscussionModelCN)

            # 投票阶段：收集并统计狼人的击杀决策
            werewolves_hub.set_auto_broadcast(False)
            kill_votes = await fanout_pipeline(
                as_agent_list(self.werewolves),
                msg=await self.moderator.announce("请选择击杀目标"),
                structured_model=WerewolfKillModelCN,
                enable_gather=False,
            )

        # 统计票数：模型写错名字也不会让这一晚空过
        wolf_names = {w.name for w in self.werewolves}
        candidates = [p.name for p in self.alive_players if p.name not in wolf_names]

        votes: Dict[str, str] = {}
        for wolf, vote_msg in zip(self.werewolves, kill_votes):
            raw = meta_of(vote_msg).get("target")
            target = resolve_target(raw, candidates)
            if target is None:
                print(f"⚠️ {wolf.name} 没给出有效目标（原值：{raw!r}），本轮弃刀")
                continue
            votes[wolf.name] = target

        killed_player, _ = majority_vote_cn(votes)
        print(f"🐺 狼人投票：{votes} → 击杀 {killed_player}")
        return None if killed_player == "无人" else killed_player

    async def seer_phase(self) -> None:
        """预言家阶段"""
        if not self.seer:
            return

        seer_agent = self.seer[0]
        await self.moderator.announce("🔮 预言家请睁眼，选择要查验的玩家...")

        check_result = await self.ask(
            seer_agent,
            structured_model=get_seer_model_cn(self.alive_players),
        )

        meta = meta_of(check_result)
        target_name = resolve_target(meta.get("target"), [p.name for p in self.alive_players])
        if not target_name:
            print("⚠️ 预言家查验失败或未选择目标，跳过此阶段")
            return

        target_role = self.roles.get(target_name, "村民")
        result_msg = f"查验结果：{target_name}是{'狼人' if target_role == '狼人' else '好人'}"
        await seer_agent.observe(await self.moderator.announce(result_msg))

    async def witch_phase(self, killed_player: Optional[str]) -> tuple:
        """女巫阶段，返回 (最终被杀的玩家, 被毒杀的玩家)"""
        if not self.witch:
            return killed_player, None

        witch_agent = self.witch[0]
        await self.moderator.announce("🧙‍♀️ 女巫请睁眼...")

        # 告知女巫死亡信息
        death_info = f"今晚{killed_player}被狼人击杀" if killed_player else "今晚平安无事"
        await witch_agent.observe(await self.moderator.announce(death_info))

        witch_action = await self.ask(witch_agent, structured_model=WitchActionModelCN)
        meta = meta_of(witch_action)

        saved_player = None
        poisoned_player = None

        if not meta:
            print("⚠️ 女巫行动失败，视为不使用技能")
        else:
            if meta.get("use_antidote") and self.witch_has_antidote and killed_player:
                saved_player = killed_player
                self.witch_has_antidote = False
                await witch_agent.observe(
                    await self.moderator.announce(f"你使用解药救了{killed_player}")
                )

            if meta.get("use_poison") and self.witch_has_poison:
                poisoned_player = resolve_target(
                    meta.get("target_name"),
                    [p.name for p in self.alive_players],
                )
                if poisoned_player:
                    self.witch_has_poison = False
                    await witch_agent.observe(
                        await self.moderator.announce(f"你使用毒药毒杀了{poisoned_player}")
                    )
                else:
                    print(f"⚠️ 女巫想用毒但目标名无效（原值：{meta.get('target_name')!r}），视为不用")

        # 解药生效则狼人这一刀落空
        final_killed = None if saved_player else killed_player
        return final_killed, poisoned_player

    async def hunter_phase(self, shot_by_hunter: Optional[str]) -> Optional[str]:
        """猎人阶段：出局时可以开枪带走一名玩家"""
        if not self.hunter or not shot_by_hunter:
            return None

        hunter_agent = self.hunter[0]
        if hunter_agent.name != shot_by_hunter:
            return None

        await self.moderator.announce("🏹 猎人发动技能，可以带走一名玩家...")

        hunter_action = await self.ask(
            hunter_agent,
            structured_model=get_hunter_model_cn(self.alive_players),
        )
        meta = meta_of(hunter_action)

        if not meta.get("shoot"):
            print("⚠️ 猎人放弃开枪")
            return None

        target = resolve_target(
            meta.get("target"),
            [p.name for p in self.alive_players if p.name != hunter_agent.name],
        )
        if not target:
            print(f"⚠️ 猎人选择开枪但目标无效（原值：{meta.get('target')!r}），视为放弃")
            return None

        await self.moderator.announce(f"猎人{hunter_agent.name}开枪带走了{target}")
        return target

    # -------------------------------------------------- 白天阶段

    def update_alive_players(self, dead_players: Sequence[str]) -> None:
        """更新存活玩家列表"""
        for dead_name in dead_players:
            if not dead_name:
                continue
            self.alive_players = [p for p in self.alive_players if p.name != dead_name]
            self.werewolves = [p for p in self.werewolves if p.name != dead_name]
            self.villagers = [p for p in self.villagers if p.name != dead_name]
            self.seer = [p for p in self.seer if p.name != dead_name]
            self.witch = [p for p in self.witch if p.name != dead_name]
            self.hunter = [p for p in self.hunter if p.name != dead_name]

    async def day_phase(self, round_num: int) -> Optional[str]:
        """白天阶段：自由讨论 + 投票放逐"""
        await self.moderator.day_announcement(round_num)

        async with MsgHub(
            as_agent_list(self.alive_players),
            enable_auto_broadcast=True,
            announcement=await self.moderator.announce(
                f"现在开始自由讨论。存活玩家：{format_player_list(self.alive_players)}"
            ),
        ) as all_hub:
            # 每人发言一轮
            await sequential_pipeline(as_agent_list(self.alive_players))

            # 并行收集所有玩家的投票决策
            all_hub.set_auto_broadcast(False)
            vote_msgs = await fanout_pipeline(
                as_agent_list(self.alive_players),
                msg=await self.moderator.announce("请投票选择要淘汰的玩家"),
                structured_model=get_vote_model_cn(self.alive_players),
                enable_gather=False,
            )

        # 统计投票
        votes: Dict[str, str] = {}
        for player, vote_msg in zip(self.alive_players, vote_msgs):
            raw = meta_of(vote_msg).get("vote")
            target = resolve_target(raw, [p.name for p in self.alive_players])
            if target is None:
                print(f"⚠️ {player.name} 的投票无效（原值：{raw!r}），视为弃票")
                continue
            votes[player.name] = target

        voted_out, vote_count = majority_vote_cn(votes)
        await self.moderator.vote_result_announcement(voted_out, vote_count)
        return None if voted_out == "无人" else voted_out

    # -------------------------------------------------- 主循环

    async def run_game(self) -> None:
        """运行游戏主循环"""
        await self.setup_game()

        for round_num in range(1, MAX_GAME_ROUND + 1):
            print(f"\n🌙 === 第{round_num}轮游戏开始 ===")

            # ---------- 夜晚 ----------
            await self.moderator.night_announcement(round_num)

            killed_player = await self.werewolf_phase(round_num)
            await self.seer_phase()
            final_killed, poisoned_player = await self.witch_phase(killed_player)

            night_deaths = [p for p in [final_killed, poisoned_player] if p]
            self.update_alive_players(night_deaths)
            await self.moderator.death_announcement(night_deaths)

            # 猎人夜里出局也能开枪
            hunter_shot = await self.hunter_phase(final_killed)
            if hunter_shot:
                night_deaths.append(hunter_shot)
                self.update_alive_players([hunter_shot])

            winner = check_winning_cn(self.alive_players, self.roles)
            if winner:
                await self.moderator.game_over_announcement(winner)
                self.print_final_summary()
                return

            # ---------- 白天 ----------
            voted_out = await self.day_phase(round_num)

            day_deaths = [p for p in [voted_out] if p]
            self.update_alive_players(day_deaths)

            hunter_shot = await self.hunter_phase(voted_out)
            if hunter_shot:
                day_deaths.append(hunter_shot)
                self.update_alive_players([hunter_shot])

            if day_deaths:
                await self.moderator.announce(
                    f"白天出局：{format_player_list_str([p for p in day_deaths if p])}"
                )

            winner = check_winning_cn(self.alive_players, self.roles)
            if winner:
                await self.moderator.game_over_announcement(winner)
                self.print_final_summary()
                return

            print(f"第{round_num}轮结束，存活玩家：{format_player_list(self.alive_players)}")

        await self.moderator.announce(f"达到最大轮数 {MAX_GAME_ROUND}，游戏结束，无人获胜。")
        self.print_final_summary()

    def print_final_summary(self) -> None:
        """结束时公布身份。用英文标点，避免 Windows 控制台编码问题。"""
        print("\n" + "=" * 50)
        print("身份揭晓：")
        for name, role in self.roles.items():
            alive = "存活" if any(p.name == name for p in self.alive_players) else "出局"
            print(f"  {name:<6} {role:<4} {alive}")
        print("=" * 50)


# ============================================================ 入口

async def main() -> None:
    """主函数"""
    player_count = 6
    if len(sys.argv) > 1:
        try:
            player_count = int(sys.argv[1])
        except ValueError:
            print(f"⚠️ 参数 {sys.argv[1]!r} 不是人数，用默认的 6 人局")

    # 先把输出编码稳住：Windows 控制台默认 GBK，中文和 emoji 会炸
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except Exception:  # noqa: BLE001
        pass

    print("🎮 欢迎来到三国狼人杀！")

    game = ThreeKingdomsWerewolfGame(player_count=player_count)
    await game.run_game()


if __name__ == "__main__":
    asyncio.run(main())
