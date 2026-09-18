---
name: rss-brief
description: 从 RSS / Atom 订阅源抓取最新文章并汇总成资讯简报。当用户要"看某个网站的更新""抓一下这几个源""做一份今日 AI 简报""36氪/虎嗅/IT之家/InfoQ 最近有什么"，或直接给出一个 .xml、/feed、releases.atom 地址要求读取内容时使用。覆盖新闻站点、博客、arXiv 论文列表和 GitHub 版本发布。
---

# RSS / 资讯简报

## 用在哪

用户要看某个信息源的最新内容时。典型场景：

- 给一个或多个 RSS 地址，要"最新几条讲了什么"
- 把多个媒体源合成一份「每日简报」
- 追踪某个 GitHub 仓库的新版本、某个 arXiv 分类的新论文

## 怎么做

1. 找出要抓的源地址。用户没给就查 `references/sources.md`，里面有实测可用的清单。
2. 运行脚本把条目取回来（见下）。
3. 读脚本的输出 —— 那是真实抓到的内容，**简报只能基于它来写**。
4. 按用户要求的形态汇总：分主题、加一句话概括、保留原文链接。

## 运行脚本

脚本在 `scripts/rss_reader.py`，纯标准库，不需要装任何依赖。

```bash
python3 scripts/rss_reader.py https://www.ithome.com/rss/ --limit 5
```

一次抓多个源：

```bash
python3 scripts/rss_reader.py https://www.36kr.com/feed https://rss.huxiu.com/ https://feed.infoq.com/ai-ml-data-eng/ --limit 3
```

需要结构化数据（要逐条处理字段）时加 `--json`：

```bash
python3 scripts/rss_reader.py https://www.ithome.com/rss/ --json
```

说明：

- Windows 上解释器可能是 `python` 而不是 `python3`，两种都试一下
- `--limit` 是每个源取几条，默认 5，上限 50
- 退出码 0 表示至少一个源成功，2 表示全部失败

## 输出长什么样

```
--- IT之家 · 5 条 ---
[1] 某条新闻的标题
    https://www.ithome.com/0/xxx.htm  ·  2026-09-17 08:30
[2] ...
```

正常情况下每个源一段，最后一行是 `成功 N / 共 M 个源`。

某个源抓不到时，那一段会变成：

```
--- https://xxx ---
    不可用：该地址返回的不是 RSS/Atom（可能被反爬拦截，或不是订阅源）
```

## 写简报的规则

- **只用脚本输出里出现过的事实**。标题、链接、时间都从输出里取，不要用你自己的记忆补新闻、补数字、补机构名。
- 某个源不可用就在简报里注一句「该源本次未取到」，不要为了让简报看起来完整而编内容。
- 链接原样保留，不要改写或拼接。
- 时间已经统一成 `YYYY-MM-DD HH:MM`（东八区），照搬即可，不要重新推算时区。
  个别源不给时间字段，那里会显示 `(无时间)` —— 照实写，不要补一个时间上去。
- 用户要"AI 相关"这类筛选时，按标题判断，宁可多留几条也不要凭空补。

## 源不可用时怎么处理

1. 先换 `references/sources.md` 里的备用地址重试一次。同一个站点换 host 结果可能完全不同
   （例如 36氪 必须是 `www.36kr.com/feed`，掉三个字母就只剩反爬页）。
2. 还是不行就如实说明该源不可用。
3. 如果当前环境根本执行不了 Python 脚本，改用你自己的联网能力直接打开那个地址，
   把 XML 里的 `<title>`、`<link>`、`<pubDate>`（Atom 是 `<updated>`）按同样的字段读出来 —— 解析规则与脚本一致。
