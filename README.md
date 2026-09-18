# Hello-Agents 学习笔记

跟着 Datawhale 开源教程 **《Hello-Agents · 从零开始构建智能体》** 逐章学习的过程记录。

仓库按章分目录：**一章一个文件夹**，里面放这一章自己的可运行脚本、说明和运行记录。教程本体不动，用 `importlib` 直接加载。

## 目录结构

```
hello-agents-main\
├─ README.md              本文件
├─ notes\                 各章笔记（01 起顺序编号）
├─ tools\                 跨章通用工具
│   ├─ check_api.py           环境自检：天气 / LLM / Tavily 三通道
│   ├─ fetch_model.py         从 ModelScope 下载模型权重（断点续传）
│   ├─ run_chapter.py         批量跑 code/chapterN/ 下的教程代码
│   ├─ run_capture_utf8.py    跑脚本并把 UTF-8 输出存文件（绕终端 GBK）
│   └─ fix_deepseek_hosts.bat 修复 DeepSeek DNS（管理员运行，可回滚）
├─ chapter1\  …  chapter7\  各章的可运行脚本与记录
├─ coze-plugin\           第 5 章用的 Coze 插件（新旧两套格式）
├─ models\                本地模型权重，**不入库**（1.2 GB 起）
├─ Hello-Agents\          **教程本体，独立 git 仓库，本仓库不跟踪**
└─ hello-agents-main\     早期 ZIP 快照，保留备用，不跟踪
```

每一章的 `runs\` 存运行输出，可以随时重跑生成，所以不入库。

## 笔记

| 文件 | 内容 |
|---|---|
| `notes\01-环境搭建与网络排障.md` | 从零搭好可运行环境；DeepSeek 连不通的根因与修复 |
| `notes\02-第1章-初识智能体.md` | 第 1 章知识笔记 |
| `notes\03-第1章代码逐项说明.md` | `get_weather` 工具函数逐块拆解 |
| `notes\04-第2章-智能体发展史与ELIZA.md` | 第 2 章知识笔记 + ELIZA 实测 |
| `notes\05-第3章-大语言模型基础.md` | 第 3 章知识笔记 + 5 个代码文件拆解 + 本地部署全过程 |
| `notes\06-第3章动手实践.md` | 章末实践题：采样参数 / 提示策略 / 幻觉，四个练习的操作清单 |

## 各章有什么

| 章 | 脚本 | 说明 |
|---|---|---|
| 1 | `chapter1\demo.py` | 「智能旅行助手」可运行版 |
| 2 | `chapter2\demo.py` | ELIZA 逐轮拆解（内部轨迹 + 边界用例 + 死代码探针） |
| 3 | `chapter3\demo.py` | 本地模型演示（对照教程 `Qwen.py`，纯离线） |
| 3 | `chapter3\practice.py` | 章末动手实践：采样参数、提示策略、模型幻觉 |
| 4 | `chapter4\react.py` | ReAct —— 搜索工具由 SerpApi 换成 Tavily，教程原文件未改 |
| 4 | `chapter4\plan_solve.py` | Plan-and-Solve 启动器（可改问题） |
| 4 | `chapter4\reflection.py` | Reflection 启动器（可改任务与反思轮数） |
| 6 | `chapter6\autogen_team.py` | AutoGen 软件团队案例（改掉人工输入，可无人值守） |
| 6 | `chapter6\agentscope_werewolf.py` | AgentScope 三国狼人杀（接了 DeepSeek） |
| 6 | `chapter6\btc_app\` | AutoGen 团队产出的 Streamlit 小应用 |
| 7 | `chapter7\run.py` | 第 7 章运行器，细节见 `chapter7\README.md` |
| 7 | `chapter7\quickstart.py` | 用 `hello_agents` 包建一个最简智能体 |

## 教材在哪

`Hello-Agents/` 是 `git clone https://github.com/datawhalechina/Hello-Agents.git` 的完整副本（859 个 commit），它自身就是一个 git 仓库，与上游保持同步。**本仓库只记录学习过程，不碰它的内容。**

- 正文：`Hello-Agents/docs/chapterN/`
- 代码：`Hello-Agents/code/chapterN/`
- 环境文档：`Hello-Agents/Extra-Chapter/Extra07-环境配置.md`

**一条规则：以 `code/` 目录为准。** `docs/` 里的代码块是 `code/` 文件的讲解版切片（第 1 章实测相似度 91.9%，差异只有标点全半角和注释措辞）。

## 环境

| 项 | 值 |
|---|---|
| Python | `Hello-Agents\.venv`（3.13.14） |
| 依赖 | openai / requests / python-dotenv / tavily-python |
| 第 3 章依赖 | numpy / torch 2.14.0+cpu / transformers 4.57.6 / accelerate / safetensors |
| 第 6 章依赖 | autogen 0.7.5 + streamlit / pandas / plotly；agentscope 1.0.2（配 `mcp<2`） |
| 第 7 章依赖 | hello-agents 0.1.1（自带 DeepSeek 识别，读 `.env` 的通用名即可） |
| 本地模型 | `models/Qwen1.5-0.5B-Chat`（1192.7 MB，纯离线可跑） |
| 配置 | `Hello-Agents\.env`（已被 .gitignore 忽略，key 需自己填） |
| LLM | DeepSeek 官方，`https://api.deepseek.com/v1`，模型 `deepseek-chat` |

注意：系统 PATH 里的 `python` 是 3.12，**没有** torch / transformers / autogen。跑各章脚本要用上面那个 venv 解释器；只有 `chapter7\run.py` 例外（它只用标准库）。

## 常用命令

```powershell
cd D:\NewFolder\hello-agents-main

# 环境自检
Hello-Agents\.venv\Scripts\python.exe tools\check_api.py

# 第 1 / 2 / 3 章
Hello-Agents\.venv\Scripts\python.exe chapter1\demo.py
Hello-Agents\.venv\Scripts\python.exe chapter2\demo.py
Hello-Agents\.venv\Scripts\python.exe chapter3\demo.py          # 本地模型，约 20 秒

# 第 4 章三个范式
Hello-Agents\.venv\Scripts\python.exe chapter4\plan_solve.py
Hello-Agents\.venv\Scripts\python.exe chapter4\reflection.py
Hello-Agents\.venv\Scripts\python.exe chapter4\react.py

# 第 6 章
Hello-Agents\.venv\Scripts\python.exe chapter6\agentscope_werewolf.py
Hello-Agents\.venv\Scripts\python.exe chapter6\autogen_team.py

# 第 7 章（run.py 用系统 python 就行）
python chapter7\run.py list
python chapter7\run.py quickstart

# 批量跑教程某章的代码
Hello-Agents\.venv\Scripts\python.exe tools\run_chapter.py 3

# 重新拉模型权重（已存在则跳过）
Hello-Agents\.venv\Scripts\python.exe tools\fetch_model.py
```

## 学习进度

- [x] 项目通读（16 章正文 + 配套代码 + 13 篇加餐 + 47 个共创项目）
- [x] 环境搭建（克隆 / venv / 依赖 / .env / DNS 排障）
- [x] 第 1 章：知识点通读 + 代码实跑（三轮循环到 `Finish`）+ `get_weather` 逐项精讲
- [ ] 第 1 章：`get_attraction` 精讲、1.4 协作模式、1.5 小结与习题
- [x] 第 2 章：知识点通读 + ELIZA 代码实跑与逐块精讲
- [ ] 第 2 章：2.4.5 关键节点概览 + 2.5 小结 + 习题（第 3 题是给 ELIZA 加规则和记忆）
- [x] 第 3 章：环境就绪、5 个代码文件跑通、**本地部署 Qwen1.5-0.5B-Chat 并离线推理验证**
- [x] 第 3 章：动手实践（采样参数 / 提示策略 / 幻觉三组实验）
- [ ] 第 3 章：代码逐项精讲；习题第 1、2、3、5、6 题（纯论述题）
- [ ] 第 4 章：三个范式已跑通并讲过，4.4 对比总结与习题未过
- [x] 第 5 章：教程缺的插件已自建 —— 新版插件包两个（`coze-plugin\`），可上传到扣子客户端
- [x] 第 6 章：AutoGen 与 AgentScope 两个案例跑通
- [ ] 第 6 章：CAMEL 与 LangGraph 两个案例（对应依赖还没装）
- [ ] 第 7 章：刚开始 —— 环境就绪、quickstart 跑通，其余按 `chapter7\README.md` 走

## 教材的分界线（提前知道，少踩坑）

| 章节 | 依赖情况 |
|---|---|
| ch1–6 | 代码自包含，本仓库环境就能跑 |
| ch7 起 | 全部 `from hello_agents import ...`，需 `pip install hello-agents`（已装 0.1.1） |
| ch5 | 无 Python 代码，是低代码平台（coze / dify / fastgpt / n8n）教程 |
| ch11 | Agentic-RL 训练，需 GPU |
| ch15 | 赛博小镇，需 Godot 引擎 |
