# 第 7 章 · 构建你的 Agent 框架

## 这一章在做什么

前几章每换一个范式就要重写一遍循环，代码越堆越多。这一章把这些收拢进一个框架 `hello_agents`：统一的消息结构、统一的 Agent 基类、统一的工具注册表。

装 pip 包只是开头。7.3 到 7.5 真正要你做的，是照着文档把 Message / Config / Agent 基类、四个 Agent 范式、工具系统各走一遍。教程给的是参考实现和测试，`my_*.py` 那几个文件是留给你自己填的。

## 这个目录里有什么

```
chapter7\
├─ README.md        本文件：本章地图与跑法
├─ quickstart.py    7.1.3 的「快速开始」，直接用 pip 包
├─ run.py           运行器：跑教程里任意一个文件，输出存进 runs\
├─ .env             从 Hello-Agents\.env 复制而来，已配好（被 .gitignore 排除）
├─ .env.example     教程自带的配置模板，只作格式说明
└─ runs\            每次运行的 UTF-8 输出记录（不入库）
```

## 教程代码在哪儿

在 `Hello-Agents\code\chapter7\`，13 个文件。对照关系：

| 节 | 文件 | 是什么 |
|---|---|---|
| 7.1.3 | `quickstart.py`（本目录） | 用装好的包建一个最简智能体 |
| 7.2.1 | `my_llm.py`、`my_main.py` | 继承 HelloAgentsLLM，加多提供商支持 |
| 7.2.2 | 无 | 本地模型调用，讲 VLLM / Ollama，本机跑不动 |
| 7.2.3 | 无 | 自动检测机制，讲原理 |
| 7.3 | 无独立文件 | Message / Config / Agent 基类，文档讲解，实现在已装的包里 |
| 7.4.1 | `my_simple_agent.py`、`test_simple_agent.py` | SimpleAgent 的完整实现与测试 |
| 7.4.2 | `my_react_agent.py`、`test_react_agent.py` | ReActAgent |
| 7.4.3 | `test_reflection_agent.py` | ReflectionAgent —— 实现要你自己写 |
| 7.4.4 | `test_plan_solve_agent.py` | PlanAndSolveAgent —— 实现要你自己写 |
| 7.4.5 | 无独立文件 | FunctionCallAgent，文档讲解 |
| 7.5.2 | `my_calculator_tool.py`、`test_my_calculator.py` | 自定义工具 |
| 7.5.3 | `my_advanced_search.py`、`test_advanced_search.py` | 多源搜索工具（Tavily + SerpApi） |
| 7.5.4 | 无独立文件 | 工具链与异步执行，文档里只给片段 |

## 怎么跑

```powershell
cd D:\NewFolder\hello-agents-main
python chapter7\run.py list                 # 看有哪些文件
python chapter7\run.py quickstart           # 先跑这个
python chapter7\run.py my_llm               # 跑教程里的文件
python chapter7\run.py test_simple_agent
```

`run.py` 只用标准库，系统那个 `python` 就能跑。它替你做四件事：换成 venv 里的解释器、强制 UTF-8（中文和 emoji 不再糊）、把 `Hello-Agents\.env` 喂进环境变量、把输出同时存一份到 `chapter7\runs\`。

终端还是认不出中文时，直接看 `runs\` 里那份记录。

## 跑之前要知道的三件事

一，依赖已经装好。`hello-agents` 0.1.1 在 venv 里，当时的探针记录见 `runs\verify-install.txt`。这个包自带 DeepSeek 识别 —— `HelloAgentsLLM()` 不传参数，会自动读 `.env` 里 `LLM_MODEL_ID` / `LLM_API_KEY` / `LLM_BASE_URL` 这三个通用名。

二，`my_*.py` 有两种来源，用 `--mine` 切换：

```powershell
python chapter7\run.py my_llm           # 跑教程那份
python chapter7\run.py my_llm --mine    # 跑 chapter7\ 下你自己写的那份
```

不加 `--mine` 时找教程目录，找不到再找本目录。两边同名时靠这个开关区分。

三，两个测试现在跑不通，这是正常的。`test_reflection_agent.py` 和 `test_plan_solve_agent.py` 会 import `my_reflection_agent` / `my_plan_solve_agent`，而教程没提供这两个文件 —— 文档 7.4.3、7.4.4 的原话是「你可以尝试根据第四章的代码……构建出自己的」。你写出来放进 `chapter7\`，运行器会自动把它加进 import 路径。

写的时候可以直接参照 `chapter4\reflection.py` 和 `chapter4\plan_solve.py`：第 4 章那两份就是这两个范式的裸版，框架做的事只是把它们收进统一的基类、把提示词做成可替换的参数。

## 本机用不上的一节

7.2.2「本地模型调用」讲的是 VLLM 和 Ollama，两者都需要 GPU。这台机器没有 CUDA，跑不动。

想看本地模型长什么样，回去跑 `chapter3\demo.py` —— 那份用 CPU + transformers 直接加载 `models\Qwen1.5-0.5B-Chat`，断网也能跑。

## 下一步

7.1 的 quickstart 已经跑通过一次，输出在 `runs\quickstart.txt`。

接着按 7.2 → 7.3 → 7.4 → 7.5 的顺序走，每节先读文档，再跑上表对应的文件。7.3 没有代码文件，读的时候可以直接翻装好的包，看框架自己的 `Message` 长什么样：

```powershell
python -c "from hello_agents import Message; import inspect; print(inspect.getsource(Message))"
```
