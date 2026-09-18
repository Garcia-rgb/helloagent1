# Coze 自建插件 · RSS 读取器

用来替代教程第 5 章「每日AI简报」案例里那个缺失的 RSS 插件。

它做一件事：你给它一个 RSS / Atom 地址，它把最新几条文章的标题、链接、发布时间取回来。

Coze 建插件有两条路：一是「导入 API」，那要求你有一个**已经部署在公网上的接口**；二是「在 Coze IDE 中创建」，代码由平台托管运行，不需要你自己有服务器。这里走第二条。

## 〇、先确认你在哪一套界面里

coze.cn 现在有两套东西都叫「插件」，名字一样，实质完全不同：

```
新版（网址形如 coze.cn/skills?capability=plugin）
  左侧导航是 新任务 / 日程 / 扩展 / 云盘，没有「资源库」这个词
  「插件」= 技能 Skill + MCP + Panel 的组合，给对话里的 Agent 用
  这一页里建的东西，格式跟下面这份代码对不上

旧版（扣子开发平台，教程第 5 章用的就是这个）
  左侧导航有 资源库 / 项目 / API 管理
  「插件」= 一个 Python 函数，能在工作流里当节点用
  下面这份 rss_reader.py 属于这一套
```

去旧版的入口，下面两个任选：

```
https://www.coze.cn/home                    直接在浏览器地址栏输这个
新版左侧进「扣子编程」→ 页面右上角「回到旧版」
```

到了之后，左侧导航能看到「资源库」，位置就对了。

注意：扣子官方文档写明「由于产品方向调整，扣子开发平台（低代码）不再向新注册用户开放」。
如果按上面的地址进去看不到「资源库」，先停下，把看到的东西告诉我，不要再自己找入口 —— 那种情况要改走新版的插件或 MCP。

## 一、建插件

1. 进入上面说的旧版界面，在左侧点「资源库」
2. 右上角「+ 资源」→ 选「插件」
3. 插件名称填 `RSS读取器`，插件工具创建方式选**「云侧插件-在 Coze IDE 中创建」**，IDE 运行时选 **Python3**
4. 进入 IDE 后新建一个工具，工具名填 **`rss_reader`**
   - 工具名必须是这个。代码第 16 行 `from typings.rss_reader.rss_reader import Input, Output` 里的两处 `rss_reader` 就是它
   - 如果你起了别的名字，把那两处改成你的工具名
5. 工具描述填（这段会被模型读，影响它判断什么时候调用）：

   ```
   读取一个 RSS 或 Atom 订阅源的地址，返回该源最新若干条文章的标题、链接和发布时间。
   当用户需要获取某个网站的最新资讯、博客更新、新闻列表时使用。
   ```

6. 把 `rss_reader.py` 的内容整个粘进代码框，覆盖掉模板里除 `handler` 之外的部分
   - 模板自带的 `from runtime import Args` 和 `handler` 函数名不要改
7. 在 IDE 的「元数据 / Metadata」里按下表填输入输出参数
8. 点右上角「试运行」，输入 `https://www.ithome.com/rss/`，能返回 5 条标题就算通
9. 保存并发布插件

## 二、参数配置表

输入参数：

```
rss_url   String    必填    要抓取的 RSS / Atom 地址
limit     Integer   非必填  返回多少条，默认 5
```

输出参数：

```
items     Array<Object>   条目数组，每个元素含四个字段：
              title     String   标题
              link      String   原文链接
              pubDate   String   发布时间（原始格式，未做时区转换）
              source    String   该 RSS 的频道名，多源汇总时用来区分
count     Integer         实际取到的条数
summary   String          已按「序号 + 标题 + 链接 + 时间」拼好的可读文本
message   String          "ok" 表示成功，否则是失败原因
```

`items` 和 `summary` 是同一批数据的两种形态：工作流里要逐条处理就用 `items`，直接丢给大模型读就用 `summary`。

## 三、接到教程的工作流里

教程的「每日AI简报」原来用 RSS 插件的输出 `articles` / `articles1` / `articles2` / `articles3` 喂给大模型。现在改成：

1. 工作流里拖四个「RSS读取器」节点（每个源一个），或者用批处理
2. 每个节点的 `rss_url` 分别填一个源，`limit` 建议 3~5
3. 大模型节点的输入改成引用这四个节点的 `summary` 字段
4. 教程用户提示里那句「从输入源 `{{articles}}` 中筛选」保持不变即可 —— `summary` 里已经带上了标题和链接

四个源建议用下面实测能取到的那几个。

## 四、本地实测（2026-09-17）

拿这份代码在本地跑过一轮 —— 把 `runtime` / `typings` 换成桩模块加载，
跑的**就是将要粘贴到 Coze 的那一份代码**，不是它的改写版。

教程给出的四个源，全部能取到：

```
36氪      https://www.36kr.com/feed               注意要带 www
虎嗅      https://rss.huxiu.com/                  注意不是 www.huxiu.com/rss/0.xml
IT之家    https://www.ithome.com/rss/
InfoQ AI  https://feed.infoq.com/ai-ml-data-eng/
```

另外这些也能用，可以拿来替换或扩充：

```
阮一峰博客  https://www.ruanyifeng.com/blog/atom.xml           （Atom 格式）
arXiv AI   http://export.arxiv.org/rss/cs.AI
少数派      https://sspai.com/feed
量子位      https://www.qbitai.com/feed
Solidot    https://www.solidot.org/index.rss
GitHub     https://github.com/任意用户/任意仓库/releases.atom   （Atom 格式）
```

一共测了 10 个源，10 个都正常。异常输入也都返回结构化错误而不是崩溃：

```
空地址       → message: "rss_url 不能为空"
非 RSS 网页  → message: "该地址返回的不是 RSS/Atom（可能被反爬拦截…）"
网络不通     → message: "抓取失败：URLError …"
```

有两个坑是实测踩出来的，代码里已经处理：

- **36氪必须带 `www`**。`https://36kr.com/feed` 会返回一段混淆过的 HTML 反爬脚本，
  带上 `www` 才是正常 XML。两个地址看起来只差三个字母，结果完全不同。
- **虎嗅的 `<item>` 里 `<id>`、`<guid>`、`<link>` 三个都在**，而且 `<link>` 排在最后。
  如果按标签出现的顺序取，会拿到 `4891940` 这种纯数字 ID 当成文章链接。

真实效果以你在 Coze 上的「试运行」为准 —— Coze 服务器在字节的机房里，出网路径和这台机器不一样，偶尔会有某个源在那边取不到。遇到就换成本清单里的其他源。

## 五、代码里几个刻意的设计

- **只用标准库**（`urllib` + `xml.etree`），不需要在 IDE 里装任何依赖，粘贴即用
- **抓回来的是 bytes 不是 str** —— 有些源不是 UTF-8 编码，`ElementTree` 会自己读 XML 声明里的 encoding，提前 decode 反而会炸
- **同时兼容 RSS 2.0 和 Atom 两种格式**，靠 `_local()` 剥掉命名空间再比对标签名
- **字段按优先级找，不按出现顺序找** —— `_text(node, "link", "guid", "id")` 的意思是
  「先全找一遍 link，没有再找 guid」，而不是「谁的标签先出现就用谁」
- **对裸 `&` 有容错** —— 有些源的正文里有没转义的 `&`（比如标题写成 `A&B`），标准库解析器会直接拒绝，代码会自动补成 `&amp;` 再试一次
- **先判断抓回来的是不是订阅源** —— 反爬页和登录页也会返回 HTTP 200，只在解析时炸的话错误信息很难懂，所以提前拦一道，给出「该地址返回的不是 RSS/Atom」
- **任何异常都返回结构化结果而不是抛异常** —— 插件抛异常会让整个工作流中断，返回 `message` 更利于排查
