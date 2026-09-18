---
name: tech-search
description: 按关键词检索 GitHub 仓库与 arXiv 论文，返回标题、链接、星标数、作者和摘要。当用户要"找一下最近有什么 AI 开源项目""搜一下 LLM 相关的论文""看看某个方向最新研究""GitHub 上最近有什么动静"，或要往简报里补「开源项目」「学术论文」这两类内容时使用。也用于把「AI 日报」里的项目榜和论文榜配齐。
---

# GitHub / arXiv 检索

## 用在哪

用户要按关键词找开源项目或论文时。典型场景：

- 「最近有什么值得看的 AI 开源项目」
- 「搜一下 agent 方向的论文」
- 做 AI 日报，需要「开源项目」和「学术论文」两块内容

这是**按需检索**，跟 `rss-daily-brief` 那个包的**订阅式抓取**不一样：

```
rss-daily-brief   给地址，拿回这个地址的最新条目     （arXiv 分类、某个仓库的 releases）
tech-search       给关键词，按条件搜全站             （GitHub 仓库、arXiv 论文）
```

用户要的是「看看有什么」，用本包；要的是「盯着这几个源」，用另一个包。

## 怎么做

1. 把用户的话翻译成检索词。两个源的语法不一样，先看 `references/queries.md`。
2. 运行脚本（见下）。
3. 读输出 —— 那是真实搜到的内容，**总结只能基于它来写**。

## 运行脚本

脚本在 `scripts/search_sources.py`，纯标准库，不需要装任何依赖。

```bash
python3 scripts/search_sources.py github --query AI --min-stars 500 --limit 5
python3 scripts/search_sources.py arxiv  --query "cat:cs.AI" --limit 5
```

一次问两个源：

```bash
python3 scripts/search_sources.py both --query "large language model" --limit 3
```

需要结构化数据时加 `--json`：

```bash
python3 scripts/search_sources.py arxiv --query "cat:cs.CL" --json
```

参数：

```
source        位置参数，github | arxiv | both
-q, --query   检索词（按各自的语法写）
--limit       返回几条，默认 5，上限 50
--min-stars   星标门槛，仅 GitHub，默认 0
--sort        github: best-match|stars|forks|updated   默认 updated
              arxiv : relevance|lastUpdatedDate|submittedDate  默认 submittedDate
--json        输出 JSON，进度和报错走 stderr
```

说明：

- Windows 上解释器可能是 `python` 而不是 `python3`，两种都试一下
- 退出码 0 表示至少一个源成功，2 表示全部失败或参数不合法

## 一条要记住的实操经验

**GitHub 按 `updated` 搜索时必须加星标门槛。**

不加会怎样 —— 实测 `q=AI & sort=updated` 的前三名：

```
[1] webwerkwien/contao-ai-cli          0 stars
[2] Lilith3777/rei-ai-updates          0 stars
[3] Toluwerr/Simply                    0 stars
```

因为「最近推送」这个排序天然偏向刚刚创建、刚提交过一次的仓库，跟项目质量无关。
教程里给的那组参数（`q:AI / per_page:10 / sort:updated`）就是这个结果。

加上 `--min-stars 500` 之后：

```
[1] modular/modular           29787 stars
[2] microsoft/agent-lightning 18239 stars
[3] Mesh-LLM/mesh-llm          3414 stars
```

所以做简报时，默认就该带上门槛。100 是底线，500 比较干净。

想换一个角度找「有名的项目」，用 `--sort stars`，那才是按影响力排。

## 输出长什么样

GitHub：

```
=== GitHub 仓库检索「AI stars:>500」· 按最近更新 · 3 条（全站命中 6421） ===

[1] modular/modular
    The Modular Platform (includes MAX & Mojo)
    https://github.com/modular/modular
    29787 stars  ·  3173 forks  ·  Mojo  ·  最近推送 2026-09-17 14:56
```

arXiv：

```
=== arXiv 论文检索「cat:cs.AI」· 按提交时间倒序 · 3 条 ===

[1] Objective vs. Search: Decomposing What Makes a Good Tokeniser
    http://arxiv.org/abs/2609.19145v1
    cs.CL  ·  提交 2026-09-17 01:59
    作者：Ahmetcan Yavuz, Clara Meister, Tiago Pimentel
    摘要：Two dominant tokenisation algorithms are used by modern language models...
```

正常情况下每个源一段，最后一行是 `成功 N / 共 M 个源`。失败会多出一行 `! github: ...`。

## 写简报的规则

这几条和 `rss-daily-brief` 一致，理由也一样 —— 模型很容易把「看起来像答案」的东西写出来：

- **只用脚本输出里出现过的事实。** 星标数、推送时间、作者、分类都从输出里取，
  不要用你自己的记忆补项目名、补论文、补数字。
- 某个源没结果就写「本次未检索到」，不要为了让简报完整而编内容。
- 链接原样保留，不要改写。arXiv 给的是 `http://arxiv.org/abs/...`，照搬。
- 时间是东八区的 `YYYY-MM-DD HH:MM`，已经换算过，照搬即可，不要重新推算。
- 摘要超过 300 字会被截断，结尾没有省略号也是正常的，不要脑补后半句。
- 用户要「重要的」这类判断时，按 stargazers_count 和推送时间说，不要凭项目名望下结论。

## 拿不到结果时

1. GitHub 报 403 —— 未认证的搜索请求限速是每分钟 10 次。等一分钟再试，不要连着重试。
2. GitHub 报 422 —— 检索语法不对。回 `references/queries.md` 核对限定符写法。
3. 一条都搜不到 —— 大概率是语法问题，不是真没有。arXiv 裸词搜不到东西，
   必须带字段前缀，例如 `all:AI` 而不是 `AI`。
4. 如果当前环境根本执行不了 Python 脚本，改用你自己的联网能力直接打开这两个接口，
   按同样的字段读出来：

```
GitHub  https://api.github.com/search/repositories?q=<关键词>&sort=updated&per_page=5
arXiv   http://export.arxiv.org/api/query?search_query=<查询>&max_results=5&sortBy=submittedDate
```
