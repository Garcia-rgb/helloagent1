# 检索语法速查

两个源的检索语法完全不同，别混用。同一个词在 GitHub 上能跑，在 arXiv 上可能一条都搜不到。

## GitHub（`--query` 里写）

普通词直接写，多个词之间是「且」。短语加双引号。

```
AI
large language model
"large language model"          ← 当成一个整体
```

常用限定符，可以和普通词混着写：

```
语言      language:python   language:typescript
星标      stars:>1000       stars:100..500
推送时间  pushed:>2026-09-10
创建时间  created:>2026-01-01
话题标签  topic:llm         topic:agent
归属      org:langchain-ai  user:karpathy
许可证    license:mit
是否归档  archived:false
匹配位置  in:name           in:description     in:readme
```

组合示例：

```
q=AI pushed:>2026-09-10 stars:>100       最近两周有推送、且星标过百的 AI 项目
q=topic:llm stars:>5000                   LLM 话题下的高星项目
q=agent language:python archived:false    没归档的 Python agent 项目
```

排序（`--sort`）：

```
updated      最近更新（默认，对应教程里的 sort=updated）
stars        星标最多
forks        fork 最多
best-match   相关度，不带排序参数
```

注意：未认证的搜索请求限速是每分钟 10 次。连点太快会返回 403，等一分钟再试。

## arXiv（`--query` 里写）

必须带字段前缀，裸词（直接写 `AI`）通常搜不到东西。前缀后面接短语要加引号。

```
all:AI                      全字段
ti:transformer              标题
abs:reinforcement learning  摘要
au:Hinton                   作者
cat:cs.AI                   分类
```

布尔运算符必须大写，且前后要有空格：

```
cat:cs.CL AND abs:agent
ti:agent OR ti:tool
cat:cs.AI ANDNOT abs:survey
```

常用分类：

```
cs.AI   人工智能
cs.CL   计算语言学（NLP）
cs.LG   机器学习
cs.CV   计算机视觉
cs.MA   多智能体系统
cs.SE   软件工程
cs.RO   机器人
stat.ML 机器学习（统计）
```

组合示例：

```
-q "cat:cs.AI"                           cs.AI 分类的最新论文
-q "cat:cs.CL AND abs:agent"             NLP 里带 agent 的
-q "all:\"large language model\""        全字段含这个短语
-q "ti:agent ANDNOT ti:survey"           标题有 agent 但不是综述
```

排序（`--sort`）：

```
submittedDate     提交时间倒序（默认）
lastUpdatedDate   最近更新倒序
relevance         相关度
```

## both 模式

`both` 会用同一个 `--query` 去问两个源。带限定符的查询只对一个源有意义 ——
`cat:cs.AI` 在 GitHub 那边会返回一堆无关结果或直接 422。

`both` 只在用自然语言短语时合适：

```bash
python3 search_sources.py both --query "large language model" --limit 3
```

要精确控制，就分两次跑，各写各的语法。
