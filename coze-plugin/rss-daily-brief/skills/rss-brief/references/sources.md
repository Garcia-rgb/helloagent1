# 实测可用的源（2026-09-17 复测）

## 教程「每日 AI 简报」案例要用的四个媒体源

```
36氪      https://www.36kr.com/feed                  必须带 www。掉成 https://36kr.com/feed 会返回一段混淆过的 HTML 反爬页
虎嗅      https://rss.huxiu.com/                     不是 https://www.huxiu.com/rss/0.xml，那个会超时
IT之家    https://www.ithome.com/rss/
InfoQ AI  https://feed.infoq.com/ai-ml-data-eng/     AI / 机器学习 / 数据工程频道
```

## 学术与开源

```
arXiv cs.AI   http://export.arxiv.org/rss/cs.AI       arXiv 各分类都有 RSS，把 cs.AI 换成 cs.CL / cs.LG 等即得其他方向
GitHub 版本   https://github.com/<owner>/<repo>/releases.atom     换仓库名即可，Atom 格式
```

## 其他可用源（可替换或扩充）

```
阮一峰博客    https://www.ruanyifeng.com/blog/atom.xml             Atom 格式
少数派        https://sspai.com/feed
量子位        https://www.qbitai.com/feed
Solidot      https://www.solidot.org/index.rss
```

## 踩过的坑

- 36氪的 host 少三个字母 `www` 就完全变样：一个是正常 XML，一个是 HTML 反爬页，而且都返回 HTTP 200。
- 虎嗅 `<item>` 里 `<id>`、`<guid>`、`<link>` 三个字段同时在，`<link>` 排在最后。取字段要按
  「先找 link，没有再找 guid」的优先级来，不能按标签出现的顺序取，否则会拿到 `4891940` 这样的纯数字编号当链接。
- 反爬页和登录页也会返回 200，所以判断一个源能不能用要看内容里有没有 `<rss>` / `<feed>` / `<rdf>`，
  不能只看状态码。
- Coze 服务器在字节机房，出网路径和本地不一样。上面是本地实测结果，以平台上的实际效果为准；
  哪个源取不到就换清单里的另一个。
