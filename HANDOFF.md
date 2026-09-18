# 换机继续指南 / 进度交接

本文件给「换一台机器接着学」用。写于 2026-09-18，对应本地 commit `ef8bc27`。

## 一、现在学到哪了

学到第 7 章第 3 节，正在往 7.4 走。前 6 章已讲完，其中第 6 章的两个框架跑通、两个只讲没跑。

各章状态：

| 章节 | 状态 | 本仓库对应文件 |
| --- | --- | --- |
| 第 1 章 初识智能体 | 完成 | `chapter1/demo.py` |
| 第 2 章 发展史与 ELIZA | 完成 | `chapter2/demo.py` |
| 第 3 章 大模型基础 | 完成（含本地模型部署） | `chapter3/demo.py`、`chapter3/practice.py` |
| 第 4 章 经典范式 | 完成（ReAct / Plan-and-Solve / Reflection） | `chapter4/react.py`、`plan_solve.py`、`reflection.py` |
| 第 5 章 低代码平台 | 完成（Coze 插件 + Dify 工作流） | `coze-plugin/` |
| 第 6 章 主流框架 | AutoGen 跑通、AgentScope 跑通；CAMEL / LangGraph 只讲过未实跑 | `chapter6/autogen_sample.py`、`autogen_team.py`、`agentscope_werewolf.py`、`btc_app/` |
| 第 7 章 hello-agents | 进行中，到 7.3；下一步 7.4 | `chapter7/` |

第 7 章细分：

- 7.1 跑通：`chapter7/quickstart.py`（框架自动认出 DeepSeek，`.env` 零改动）
- 7.2 跑通：`chapter7/llm_detect.py`（provider 四层检测优先级实测）
- 7.3 写完：`chapter7/core_interfaces.py`（Message / Config / Agent 三个接口的逐行注解版）
- 7.4 未开始：教程要讲 SimpleAgent 等五个内置 Agent，都是继承 `Agent` 只重写 `run()`

笔记在 `notes/`，共 6 篇（`01` 环境排障、`02/03` 第 1 章、`04` 第 2 章、`05/06` 第 3 章）。第 4 章之后没再写独立笔记，成果直接落在各章 `.py` 文件的注释里。

## 二、仓库里有什么、没什么

这个仓库只跟踪「我自己的代码 + 笔记 + 工具」，教程本体不入库。

被 `.gitignore` 排除、换机后必须自己补的：

- `Hello-Agents/` —— 教程本体（它自己是独立 git 仓库）。新机要重新 clone。
- `models/` —— 本地模型权重，1.2 GB 起。用 `tools/fetch_model.py` 重拉。
- `.env` —— API key。仓库里只有 `chapter7/.env.example` 模板。
- `runs/` —— 各章运行输出，随时可重跑，不用带。
- `.workbuddy/` —— 助手工作记忆，含本机细节，不公开。
- `hello-agents-main/` —— 早期 ZIP 快照，可丢弃。
- `_*`、`*.log` —— 临时诊断文件。

## 三、换机三步

### 第 1 步：把代码同步过去

当前本地比远端多 1 个 commit（`ef8bc27` 未推送）。远端是 `git@github.com:Garcia-rgb/helloagent1.git`（公开仓库）。

- 在旧机推送后，新机 `git clone git@github.com:Garcia-rgb/helloagent1.git` 即可。
- 不想走网络就整个目录打包复制，但注意 `Hello-Agents/` 和 `models/` 也要一起带（前者可直接复制，后者建议重下，1.2 GB）。

### 第 2 步：重建教程与虚拟环境

```bash
# 教程本体（放在仓库根目录下，名字保持 Hello-Agents）
git clone https://github.com/datawhalechina/hello-agents Hello-Agents

# 虚拟环境 —— 教程自己的 venv，各章脚本都认这个路径
cd Hello-Agents
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r <仓库根>\requirements-full.txt
```

Linux / macOS 把 `.venv\Scripts\python.exe` 换成 `.venv/bin/python`。

两份依赖清单的用途：

- `requirements-full.txt` —— 本机 `pip freeze` 全量，照搬环境用。里面 `torch==2.14.0` 是 CPU 版；新机若有 NVIDIA 卡，先卸 torch 再按官网装 CUDA 版。
- 只想学第 7 章的话，最小集合是 `hello-agents==0.1.1` + `python-dotenv` + `openai`。

分组依赖（按需装，不必一次全装）：

```
第 1~2 章  openai python-dotenv requests
第 3 章    torch transformers accelerate safetensors modelscope
第 4 章    上面 + serpapi(包名 google_search_results) tavily-python
第 6 章    autogen-agentchat==0.7.5 autogen-core==0.7.5 autogen-ext==0.7.5
           streamlit pandas plotly
           agentscope==1.0.2 "mcp<2"      ← mcp 必须 <2，见下方坑
第 7 章    hello-agents==0.1.1
```

### 第 3 步：填 `.env`

从 `Hello-Agents/.env.example` 复制一份改名 `.env`，填这几个：

```
LLM_MODEL_ID=deepseek-chat
LLM_API_KEY=sk-xxxxxxxx
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_TIMEOUT=120
TAVILY_API_KEY=tvly-xxxxxxxx     # 第 4 章部分工具要用
```

`chapter7/.env` 是它的副本，第 7 章脚本读这份。两份都别提交。

## 四、换机后一定会撞的坑

按撞上的概率排序：

1. **直接敲 `python` 会报 ModuleNotFoundError。** PATH 里的 `python` 是系统解释器，没装依赖。一律写全路径 `Hello-Agents\.venv\Scripts\python.exe`，或在 PyCharm 里把项目解释器改成它（设置 → 项目 → Python 解释器 → 添加本地 → 现有），改完**终端要重开**才生效。
2. **agentscope 必须配 `mcp<2`。** 它声明的 `mcp>=1.13` 没上限，会拉到 mcp 2.x，然后 `import agentscope` 直接崩在 `streamablehttp_client` 改名上。装完补一条 `pip install "mcp<2"`。
3. **AutoGen 必须显式传 `model_info`**，否则抛 `ValueError: model_info is required`。已改好的版本在 `Hello-Agents/code/chapter6/AutoGenDemo/autogen_software_team.py`。
4. **终端中文乱码是终端侧问题**（代码页 936），不是 Python 的锅。`chcp 65001` 可解；要抓输出用 `tools/run_capture_utf8.py <脚本> <输出文件>`，它让 Python 自己写 UTF-8 文件。**别用 `python x.py | Out-File`**，PowerShell 会先按 GBK 解码再写出，中文不可逆地糊掉。
5. **HuggingFace 全链路不通**（huggingface.co 和 hf-mirror.com 都不行），只有 `modelscope.cn` 通。模型一律走 `tools/fetch_model.py`，教程里写的 `HF_ENDPOINT=hf-mirror.com` 在这台机器无效。
6. **这台机器没有 NVIDIA 独显**（只有 Intel UHD 集显）→ vLLM 装不了，Ollama 也只能 CPU 跑。第 3 章那个 Qwen1.5-0.5B-Chat 已经是本地推理体验的上限。新机若有 N 卡，第 11 章才能正常做。
7. **删文件绝不用 `git rm`**（带不带 `-r` 都一样会清空目标所在的整个目录）。要移出跟踪用 `git rm --cached`，真删用 shell `rm` 单个文件。
8. **7.2 的检测演示会被系统环境变量干扰**：本机在系统级设了 `DEEPSEEK_API_KEY`，它会把 provider 检测压在第一层，看不到后面的分层逻辑。新机没这个变量的话，跑 `chapter7/llm_detect.py` 看到的顺序会和旧机记录的不一样，这是正常的。

## 五、跑法速查

```bash
# 第 7 章（统一入口）
python chapter7\run.py list
python chapter7\run.py <名字> [--mine]     # --mine 优先跑 my_*.py 自己写的那版

# 其它章节
python chapter1\demo.py
python chapter2\demo.py
python chapter3\demo.py
python chapter4\react.py
python chapter6\autogen_team.py
python chapter6\agentscope_werewolf.py
```

第 6 章那个比特币行情应用单独跑：

```bash
cd chapter6\btc_app && streamlit run app.py
```

## 六、下一步 7.4

教程 7.4 讲 `hello-agents` 内置的五个 Agent，它们都继承 7.3 的 `Agent` 基类，只重写 `run()`。看的时候按这个顺序：先读 `Agent.run()` 的抽象方法签名，再看每个子类的 `run()` 里多了什么。

`chapter7/run.py` 会优先跑教程 `code/chapter7/` 下的同名文件；要跑自己写的那份，先把教程文件挪走或加 `--mine`。
