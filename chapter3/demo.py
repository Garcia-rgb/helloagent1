# -*- coding: utf-8 -*-
"""
第3章 · 本地部署 Qwen1.5-0.5B-Chat 演示

对照教程 `Hello-Agents/code/chapter3/Qwen.py`，**只改了一处**：
    原版  model_id = "Qwen/Qwen1.5-0.5B-Chat"     → 走 HF 网络下载
    本版  MODEL_DIR = 本地 models/Qwen1.5-0.5B-Chat  → 纯离线加载

其余逻辑（chat_template 渲染 → 编码 → generate → 截掉输入 → 解码）与教程逐行一致。
教程原文件一个字没动。

跑法:
    D:\\NewFolder\\hello-agents-main\\Hello-Agents\\.venv\\Scripts\\python.exe ^
        D:\\NewFolder\\hello-agents-main\\chapter3/demo.py

耗时（2026-09-17 实测，同一台机器的两种环境）:
                        用户真机    沙箱
    import torch            4 s      15 s
    import transformers    10 s      67 s
    load tokenizer          1 s       3 s
    load model (fp32)       3 s      11 s
    ----------------------------------------
    到第一行输出           14 s    ~100 s
    生成速度约 9 tok/s（单进程独占 CPU 时）

    快的十几秒、慢的一分多钟都可能，期间屏幕全无输出，都不是卡死。

**不要同时开两个终端跑本脚本**：两个进程共抢 12 核 CPU 和各自 1.8 GB 内存，
速度会掉到 1 tok/s 以下，而且两者都会用 "w" 模式打开同一个输出文件互相覆盖。
"""
import os
import sys
import time

# ---- 只此一处与教程不同：切断联网，强制用本地权重 ----
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))     # chapter3/
REPO_ROOT = os.path.dirname(SCRIPT_DIR)                     # 仓库根
RUNS_DIR = os.path.join(SCRIPT_DIR, "runs")
os.makedirs(RUNS_DIR, exist_ok=True)
MODEL_DIR = os.path.join(REPO_ROOT, "models", "Qwen1.5-0.5B-Chat")
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
# 教程那行 os.environ["HF_ENDPOINT"] = "https://hf-mirror.com" 在这里没用了，删掉


class _Tee:
    """Windows 控制台默认 GBK，中文输出会糊。

    这里把 stdout 同时写进一个 UTF-8 文件，控制台看着乱就直接看文件。
    """

    def __init__(self, path):
        # buffering=1 → 行缓冲，避免输出卡在内存里一直不落盘
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


sys.stdout = _Tee(os.path.join(RUNS_DIR, "demo-latest.txt"))

T0 = time.time()


def say(msg):
    """每行都带「已运行秒数」并立即 flush，卡在哪一步一眼能看出来。"""
    print(f"[{time.time()-T0:6.1f}s] {msg}", flush=True)


say("进程已启动，开始 import torch（十几秒，期间无输出属正常）")

import torch

say("torch 就绪，开始 import transformers（十几秒到一分多钟，仍然无输出属正常）")

from transformers import AutoModelForCausalLM, AutoTokenizer

say("两个库都就绪，开始干活")

model_id = MODEL_DIR

device = "cuda" if torch.cuda.is_available() else "cpu"
say(f"Using device: {device}")
say(f"模型来源: {model_id}")

# 加载分词器
say("加载分词器中 ...")
t0 = time.time()
tokenizer = AutoTokenizer.from_pretrained(model_id)
say(f"分词器加载完成，用时 {time.time()-t0:.2f}s")

# 加载模型，并将其移动到指定设备
# 教程是 from_pretrained(model_id) 默认 bfloat16；CPU 上 bf16 运算慢，
# 这里显式转 float32，精度不降、速度更快，代价是内存翻倍（约 1.8 GB）
say("加载模型权重中（读盘 1.2 GB，转 fp32 后占内存约 1.8 GB）...")
t0 = time.time()
model = AutoModelForCausalLM.from_pretrained(model_id, dtype=torch.float32).to(device)
model.eval()
say(f"模型加载完成，用时 {time.time()-t0:.2f}s")

say("模型和分词器加载完成！")

# 准备对话输入
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "你好，请介绍你自己。"}
]

# 使用分词器的模板格式化输入
text = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True
)

# 编码输入文本
model_inputs = tokenizer([text], return_tensors="pt").to(device)

say("编码后的输入文本:")
print(model_inputs, flush=True)

# 使用模型生成回答
say("开始生成（CPU 推理，本机约 9 tok/s，慢是正常的）...")
t0 = time.time()
with torch.no_grad():
    generated_ids = model.generate(
        model_inputs.input_ids,
        attention_mask=model_inputs.attention_mask,
        max_new_tokens=512
    )
dt = time.time() - t0

# 将生成的 Token ID 截取掉输入部分
generated_ids = [
    output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
]

# 解码生成的 Token ID
response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]

n_new = len(generated_ids[0])
say(f"生成 {n_new} 个新 token，用时 {dt:.1f}s（{n_new/max(dt,1e-9):.1f} tok/s）")
print("\n模型的回答:", flush=True)
print(response, flush=True)
