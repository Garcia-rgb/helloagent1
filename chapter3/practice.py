# -*- coding: utf-8 -*-
"""
第3章 · 动手实践（对应章末习题 4 + 3.3.2 节「模型幻觉」）

三个实验，全部用本地 Qwen1.5-0.5B-Chat 跑，不联网：

  A. 采样参数：同一个问题，只改 temperature，看输出怎么变
  B. 提示策略：同一个任务，Zero-shot / Few-shot / CoT 三种问法对比
  C. 模型幻觉：问一个它知识截止之后的事，看它会不会一本正经地编

跑法:
    Hello-Agents\\.venv\\Scripts\\python.exe chapter3/practice.py

控制台若显示乱码，直接看同目录生成的 chapter3/runs/practice-latest.txt（UTF-8）。
到第一行输出的等待时间视机器而定，快的十几秒，慢的一分多钟都算正常
（import torch + transformers 本身就占大头，期间无输出不是卡死）。
"""
import os
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))     # chapter3/
REPO_ROOT = os.path.dirname(SCRIPT_DIR)                     # 仓库根
RUNS_DIR = os.path.join(SCRIPT_DIR, "runs")
os.makedirs(RUNS_DIR, exist_ok=True)
MODEL_DIR = os.path.join(REPO_ROOT, "models", "Qwen1.5-0.5B-Chat")
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"


class _Tee:
    """stdout 同时写一份 UTF-8 文件，绕开 Windows 控制台的 GBK。"""

    def __init__(self, path):
        self._f = open(path, "w", encoding="utf-8", buffering=1)

    def write(self, s):
        try:
            sys.__stdout__.write(s)
            sys.__stdout__.flush()
        except Exception:
            pass
        self._f.write(s)

    def flush(self):
        try:
            sys.__stdout__.flush()
        except Exception:
            pass
        self._f.flush()

    def isatty(self):
        return False

    def close(self):
        self._f.close()


sys.stdout = _Tee(os.path.join(RUNS_DIR, "practice-latest.txt"))

T0 = time.time()


def say(msg=""):
    print(f"[{time.time()-T0:6.1f}s] {msg}" if msg else "", flush=True)


say("进程已启动，开始 import torch（十几秒，无输出属正常）")

import torch

say("torch 就绪，开始 import transformers（视机器十几秒到一分多钟，仍然无输出属正常）")

from transformers import AutoModelForCausalLM, AutoTokenizer

device = "cuda" if torch.cuda.is_available() else "cpu"
say(f"device = {device}")

say("加载分词器与模型权重 ...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
model = AutoModelForCausalLM.from_pretrained(MODEL_DIR, dtype=torch.float32).to(device)
model.eval()
say("模型就绪")
say()


def ask(question, max_new_tokens=64, system="You are a helpful assistant.", **gen_kwargs):
    """向本地模型问一句话，返回 (回答文本, 新生成 token 数, 耗时秒)。

    注意：do_sample=True 时 temperature 必须严格大于 0，填 0.0 会直接抛 ValueError。
    想要确定性输出请改用 do_sample=False，不要用 temperature=0 表达。
    """
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": question},
    ]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer([text], return_tensors="pt").to(device)

    t0 = time.time()
    with torch.no_grad():
        out = model.generate(
            inputs.input_ids,
            attention_mask=inputs.attention_mask,
            max_new_tokens=max_new_tokens,
            pad_token_id=tokenizer.eos_token_id,
            **gen_kwargs,
        )
    dt = time.time() - t0

    new_ids = [o[len(i):] for i, o in zip(inputs.input_ids, out)]
    answer = tokenizer.batch_decode(new_ids, skip_special_tokens=True)[0].strip()
    return answer, len(new_ids[0]), dt


# ============================================================
say("=" * 66)
say("实验 A · 采样参数")
say("问题固定，只改 temperature。温度越高，候选词被选中的随机性越大。")
say("=" * 66)

QUESTION = "请用一句话介绍杭州。"
say(f"问题：{QUESTION}")
say(f"（这段输入会被切成 {len(tokenizer(QUESTION).input_ids)} 个 token）")
say()

for T in (0.1, 0.5, 1.0, 1.5, 2.0):
    # 只传 temperature：transformers 4.57 会忽略直接塞进 generate() 的 top_p
    ans, n, dt = ask(QUESTION, max_new_tokens=48, do_sample=True, temperature=T)
    say(f"  temperature = {T}")
    say(f"  {ans}")
    say(f"  —— {n} tok / {dt:.1f}s")
    say()


# ============================================================
say("=" * 66)
say("实验 B · 提示策略")
say("任务固定（情感二分类），只改问法。这里用贪心解码，固定随机性。")
say("=" * 66)

REVIEW = "这家店的服务态度很好，但是菜上得特别慢，等了一个小时。"
say(f"待判断的评论：{REVIEW}")
say()

ZERO_SHOT = f"判断下面这条评论的情感是正面还是负面，只回答一个词：\n{REVIEW}"

FEW_SHOT = (
    "判断评论的情感是正面还是负面，只回答一个词。\n\n"
    "评论：味道不错，就是有点贵。\n情感：负面\n\n"
    "评论：环境很安静，适合看书。\n情感：正面\n\n"
    f"评论：{REVIEW}\n情感："
)

COT = (
    "先逐条列出下面这条评论里让人满意的点和让人不满意的点，"
    f"再判断整体情感是正面还是负面：\n{REVIEW}"
)

# CoT 要预留更多 token：把推理过程写出来本身就占长度
for name, prompt in (("Zero-shot", ZERO_SHOT), ("Few-shot", FEW_SHOT), ("CoT", COT)):
    ans, n, dt = ask(prompt, max_new_tokens=160, do_sample=False)
    say(f"  [{name}]")
    say(f"  {ans}")
    say(f"  —— {n} tok / {dt:.1f}s")
    say()


# ============================================================
say("=" * 66)
say("实验 C · 模型幻觉")
say("问一件发生在它知识截止之后的事。它没有『不知道』这个按钮。")
say("=" * 66)

HALLUCINATION_Q = "2024年诺贝尔物理学奖颁给了谁？请说明他们的主要贡献。"
say(f"问题：{HALLUCINATION_Q}")
say()

ans, n, dt = ask(HALLUCINATION_Q, max_new_tokens=140, do_sample=False)
say(f"  {ans}")
say(f"  —— {n} tok / {dt:.1f}s")
say()

say("=" * 66)
say(f"全部完成，总耗时 {time.time()-T0:.1f}s")
say("=" * 66)
