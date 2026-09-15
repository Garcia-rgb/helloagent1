# Hello-Agents 学习笔记

跟着 Datawhale 开源教程 **《Hello-Agents · 从零开始构建智能体》** 逐章学习的过程记录。

## 目录

| 路径 | 说明 |
|---|---|
| `notes/01-环境搭建与网络排障.md` | 从零搭好可运行环境；DeepSeek 连不通的根因与修复 |
| `notes/02-第1章-初识智能体.md` | 第 1 章知识笔记 |
| `notes/03-第1章代码逐项说明.md` | `get_weather` 工具函数逐块拆解 |
| `chapter1_demo.py` | 第 1 章「智能旅行助手」可运行版 |
| `check_api.py` | 环境自检：天气 / LLM / Tavily |
| `fix_deepseek_hosts.bat` | 修复 DeepSeek DNS（管理员运行，可回滚） |
| `Hello-Agents/` | **教程本体，独立 git 仓库，本仓库不跟踪** |
| `hello-agents-main/` | 早期的 ZIP 快照，保留备用，不跟踪 |

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
| 配置 | `Hello-Agents\.env`（已被 .gitignore 忽略，key 需自己填） |
| LLM | DeepSeek 官方，`https://api.deepseek.com/v1`，模型 `deepseek-chat` |

跑环境自检：

```
D:\NewFolder\hello-agents-main\Hello-Agents\.venv\Scripts\python.exe D:\NewFolder\hello-agents-main\check_api.py
```

跑第 1 章演示：

```
D:\NewFolder\hello-agents-main\Hello-Agents\.venv\Scripts\python.exe D:\NewFolder\hello-agents-main\chapter1_demo.py
```

## 学习进度

- [x] 项目通读（16 章正文 + 配套代码 + 13 篇加餐 + 47 个共创项目）
- [x] 环境搭建（克隆 / venv / 依赖 / .env / DNS 排障）
- [x] 第 1 章：知识点通读
- [x] 第 1 章：代码实跑打通（三轮循环到 `Finish`）
- [x] 第 1 章：`get_weather` 逐项精讲
- [ ] 第 1 章：`get_attraction` 精讲
- [ ] 第 1 章：1.4 协作模式 + Workflow vs Agent
- [ ] 第 1 章：1.5 小结与习题
- [ ] 第 2 章：智能体发展史

## 教材的分界线（提前知道，少踩坑）

| 章节 | 依赖情况 |
|---|---|
| ch1–6 | 代码自包含，本仓库环境就能跑 |
| ch7 起 | 全部 `from hello_agents import ...`，需 `pip install hello-agents` |
| ch5 | 无 Python 代码，是低代码平台（coze / dify / fastgpt / n8n）教程 |
| ch11 | Agentic-RL 训练，需 GPU |
| ch15 | 赛博小镇，需 Godot 引擎 |
