# -*- coding: utf-8 -*-
"""
第 2 章 · ELIZA 逐轮拆解演示
================================
教程原文件: Hello-Agents/code/chapter2/ELIZA.py  (85 行, 只用标准库 re / random)

这个脚本做四件事:
  1. 加载教程原文件 —— 不复制、不修改它
  2. 复刻一份带"内部轨迹"的 respond_traced(), 并校验它与原版 respond() 输出完全一致
  3. 用它跑: 教程示例对话 / 随机性对照 / 边界用例 / 死代码验证
  4. 告诉你原版怎么自己跑

用法:
    python chapter2/demo.py            # 跑脚本化演示
    python chapter2/demo.py --chat     # 直接进交互模式(等价于跑原版)
"""

import importlib.util
import random
import string
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent   # 本文件在 chapter2/ 下，仓库根是上一层
SRC = REPO_ROOT / "Hello-Agents" / "code" / "chapter2" / "ELIZA.py"

# 让中文输出在各终端下一致(不改用户环境, 只影响本进程)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def load_eliza():
    """从教程原文件加载模块(顶层有 __main__ 保护, 不会启动聊天循环)"""
    spec = importlib.util.spec_from_file_location("eliza_src", SRC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- 轨迹版
def respond_traced(mod, user_input):
    """
    与 mod.respond() 逻辑完全相同, 只是把每一步中间值都留下来。
    用于教学: 让你看见"命中了哪条规则、捕获到了什么、代词怎么换的"。
    """
    for pattern, responses in mod.rules.items():
        match = mod.re.search(pattern, user_input, mod.re.IGNORECASE)
        if match:
            captured = match.group(1) if match.groups() else ""
            swapped = mod.swap_pronouns(captured)
            template = random.choice(responses)
            return {
                "pattern": pattern,
                "has_group": bool(match.groups()),
                "captured": captured,
                "swapped": swapped,
                "template": template,
                "response": template.format(swapped),
            }
    return {"pattern": "(兜底)", "has_group": False, "captured": "",
            "swapped": "", "template": "", "response": ""}


def line(ch="-", n=78):
    print(ch * n)


def show(text, t, indent="    "):
    print(f"{indent}命中规则 : {t['pattern']}")
    print(f"{indent}捕获组   : {t['captured']!r}   (规则里有捕获组: {t['has_group']})")
    print(f"{indent}代词转换 : {t['swapped']!r}")
    print(f"{indent}模板     : {t['template']!r}")
    print(f"{indent}最终回应 : {t['response']}")


# ---------------------------------------------------------------- 1
TUTORIAL_DIALOG = [
    "I am feeling sad today.",
    "I need some help with my project.",
    "My mother is not happy with my work.",
]


def check_equivalence(mod, inputs):
    print("【1】一致性校验: 轨迹版 vs 教程原版")
    line()
    ok = 0
    for text in inputs:
        random.seed(20260916)
        a = mod.respond(text)
        random.seed(20260916)
        b = respond_traced(mod, text)["response"]
        ok += (a == b)
    print(f"  输入 {len(inputs)} 条, 输出一致 {ok} 条")
    print(f"  => {'一致, 下面的轨迹可信' if ok == len(inputs) else '不一致, 轨迹版有问题!'}")
    print()


# ---------------------------------------------------------------- 2
def run_tutorial_dialog(mod):
    print("【2】复现教程 2.2.3 的示例对话")
    line()
    print("Therapist: Hello! How can I help you today?")
    for text in TUTORIAL_DIALOG:
        print(f"You: {text}")
        random.seed(20260916)
        t = respond_traced(mod, text)
        show(text, t)
        print(f"Therapist: {t['response']}")
    print("You: quit")
    print("Therapist: Goodbye. It was nice talking to you.")
    print()


# ---------------------------------------------------------------- 3
def run_randomness(mod):
    print("【3】同一个输入连跑 5 次 (random.choice 在起作用)")
    line()
    print("  教程示例里那两句回应, 只是某一次抽样的结果, 不是固定答案:")
    print()
    for text in TUTORIAL_DIALOG:
        print(f"  输入: {text!r}")
        for i in range(5):
            random.seed(1000 + i)
            t = respond_traced(mod, text)
            print(f"    {i + 1}. {t['template']!r}")
            print(f"       -> {t['response']}")
        print()


# ---------------------------------------------------------------- 4
EDGE_CASES = [
    ("I am not happy", "否定词 not 被当成普通内容, 回应语义不通"),
    ("I am Feeling SAD", "捕获组被 tolower() 了, 大小写丢失"),
    ("mother is worried", "句首的 mother: 规则要求前后各有一个空格"),
    ("My mother is worried", "同样的意思, 换成 My 开头就命中了"),
    ("I am worried about my father", "同时含 I am 和 father, 看谁优先"),
    ("I need", "I need 后面什么都不写"),
    ("Why don't you help me?", "带问号的规则, 验证 \\? 转义"),
    ("hello", "完全不含关键词"),
]


def run_edge_cases(mod):
    print("【4】边界用例 (规则法的裂缝都在这)")
    line()
    for text, note in EDGE_CASES:
        random.seed(20260916)
        t = respond_traced(mod, text)
        print(f"  输入 : {text!r}")
        print(f"  说明 : {note}")
        show(text, t)
        print()


# ---------------------------------------------------------------- 5
def dead_code_check(mod):
    print("【5】respond() 末尾那句兜底 return 会执行吗?")
    line()
    pool = [c[0] for c in EDGE_CASES] + TUTORIAL_DIALOG + ["", " ", "\n", "。", "12345"]
    random.seed(1)
    for _ in range(2000):
        n = random.randint(0, 30)
        pool.append("".join(random.choice(string.printable) for _ in range(n)))
    unmatched = [t for t in pool if mod.re.search(r".*", t, mod.re.IGNORECASE) is None]
    print(f"  样本 {len(pool)} 个(含 2000 个随机字符串), 无法匹配 r'.*' 的: {len(unmatched)} 个")
    print("  因为 r'.*' 排在字典最后, 且在任何输入上都匹配,")
    print("  所以 for 循环必然在这里 return —— 末尾那句兜底 return 是死代码, 永远走不到。")
    print()


# ---------------------------------------------------------------- 6
def how_to_chat(mod):
    print("【6】想自己跟它聊")
    line()
    print(f'  python "{SRC}"')
    print("  输入 quit / exit / bye 退出。")
    print()
    print("  注意: 跑原版时每一轮的回应都是随机挑的, 和上面演示不会完全相同。")


def main():
    mod = load_eliza()
    print()
    line("=")
    print("第 2 章 · ELIZA 内部机制拆解")
    print(f"源文件   : {SRC}")
    print(f"规则条数 : {len(mod.rules)}    代词映射: {len(mod.pronoun_swap)} 项")
    line("=")
    print()

    check_equivalence(mod, [c[0] for c in EDGE_CASES] + TUTORIAL_DIALOG)
    run_tutorial_dialog(mod)
    run_randomness(mod)
    run_edge_cases(mod)
    dead_code_check(mod)
    how_to_chat(mod)


def chat():
    import runpy
    runpy.run_path(str(SRC), run_name="__main__")


if __name__ == "__main__":
    if "--chat" in sys.argv:
        chat()
    else:
        main()
