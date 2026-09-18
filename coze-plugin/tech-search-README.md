# tech-search 插件包 · 使用说明

给扣子（coze.cn）新版客户端用的插件包，补上教程第 5 章里缺的那两块信息源：GitHub 和 arXiv。

## 一、它解决什么问题

教程第 5 章的「每日 AI 简报」案例要接三个信息源插件：

```
RSS 插件      36氪 / 虎嗅 / IT之家 / InfoQ       ← 用 rss-daily-brief 包解决了
GitHub 插件   searchRepository                ← 教程截图里的图 5.7
arXiv 插件    searcharXiv                     ← 教程截图里的图 5.8
```

后两个是 Coze 平台侧的官方插件，教程写作时能搜到，现在国内版商店里还在不在没法替你确认（商店要登录）。
但无论还在不在，这两个的信息其实都能从公开接口直接拿到，不需要依赖插件市场。

所以这个包用两个站自己的 API 把同样的检索语义做出来了。

## 二、和另一个包的分工

两个包各管一件事，别混：

```
rss-daily-brief   给地址，拿回这个地址的最新条目
                  用于：36氪/虎嗅/IT之家的新闻流、某个仓库的 releases、某个 arXiv 分类
                  关键词：订阅、盯着这几个源

tech-search       给关键词，按条件搜全站
                  用于：搜 GitHub 仓库、搜 arXiv 论文
                  关键词：找找有什么、搜一下
```

做一份完整日报，两个都挂上：新闻用前者，项目榜和论文榜用后者。

## 三、上传

和上一个包一样：

```
左侧「扩展」→「插件」→ 右上角「上传插件包」→ 选择文件
tech-search.zip → 等解析 → 确认名称 tech-search → 保存
```

传完在「我的」标签里能看到。对话里挂上：输入框「+」→ 插件 → 选 `tech-search` → 添加。

如果平台报「不识别插件包」，换 `tech-search-nested.zip`（内容一样，只是多套了一层文件夹）。

## 四、挂上之后怎么说话

不用提脚本，直接说人话：

```
最近有什么值得看的 AI 开源项目
搜一下 agent 方向的论文，要这周的新论文
帮我看看 cs.CL 分类今天有什么新论文
给日报补两块：今天的 AI 开源项目和最新论文
```

## 五、教程参数对照

教程里那两个插件的配置项，对应到本脚本的参数：

```
GitHub 插件                         本脚本
  q: AI                             --query AI
  per_page: 10                      --limit 10
  sort: updated                     --sort updated
  （教程没有，但强烈建议加上）        --min-stars 100

arXiv 插件                          本脚本
  search_query: AI                  --query "all:AI"
  count: 5                          --limit 5
  sort_by: 2                        --sort submittedDate
```

两处需要说明：

一是 arXiv 的 `search_query`。教程里填的是裸词 `AI`，但 arXiv 官方 API 要求带字段前缀，
裸词会搜不到东西。要用 `all:AI`（全字段）、`cat:cs.AI`（分类）、`ti:agent`（标题）这类写法，
完整清单见 `tech-search/skills/tech-search/references/queries.md`。

二是 `sort_by: 2`。那是 Coze 插件自己的枚举值，具体映射官方没写明。
本脚本用的是 arXiv API 的原生字段名，只有三个可选：

```
submittedDate     提交时间倒序（默认）
lastUpdatedDate   最近更新倒序
relevance         相关度
```

## 六、实测

结构验收是**把 zip 解开、从解压出来的副本里跑**的，不是拿源码目录跑。两项都通过：

```
plugin.json 在压缩包根目录           ✓
plugin.json 的 name 与文件夹名一致    ✓
SKILL.md frontmatter 完整            ✓
脚本可执行，联网真跑                  ✓
两种错误输入都返回退出码 2            ✓
```

功能实跑（2026-09-17）：

```
GitHub   q=AI stars:>500 sort=updated   →  全站命中 6421，取回 3 条
         modular/modular           29787 stars  Mojo
         larksuite/cli             17244 stars  Go
         microsoft/agent-lightning 18239 stars  Python

arXiv    cat:cs.AI sortBy=submittedDate →  取回 3 条
         Objective vs. Search: Decomposing What Makes a Good Tokeniser   cs.CL
         A Zeroth-Order Paradigm for LLM Preference Alignment             cs.CL
         Dreaming the Sound of Contact...                                 cs.RO
```

完整过程见 `tech-search-verify.txt`。

## 七、两件要记牢的事

**GitHub 按 updated 搜，必须加星标门槛。**

不加的结果是这样 —— 全是刚建的空仓库，对日报毫无价值：

```
[1] webwerkwien/contao-ai-cli     0 stars
[2] Lilith3777/rei-ai-updates     0 stars
[3] Toluwerr/Simply               0 stars
```

「最近推送」这个排序天然偏向刚提交过一次的仓库，跟质量无关。教程给的那组参数就是这个结果。
加上 `--min-stars 500` 才是上面那份像样的列表。

**GitHub 未认证的搜索请求限速是每分钟 10 次。**

连续搜太多次会返回 403。等一分钟再试，不要连着重试。

## 八、包内结构

```
plugin.json                               插件身份
skills/tech-search/SKILL.md               何时用、怎么跑、哪几条不许做
skills/tech-search/references/queries.md  两个源的检索语法速查
skills/tech-search/scripts/search_sources.py   检索脚本，纯标准库，零依赖
```

零依赖是刻意的 —— 平台侧装不上第三方包，只用标准库的脚本才跑得起来。
