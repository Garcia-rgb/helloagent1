# -*- coding: utf-8 -*-
"""Coze 插件 · RSS 读取器

用法：在扣子（coze.cn）里「创建插件」→ 选「在 Coze IDE 中创建」→ Python3，
      新建一个名为 rss_reader 的工具，把本文件内容整个粘进代码框。

功能：给它一个 RSS / Atom 地址，抓回最近若干条文章的标题、链接、时间。

依赖：只用 Python 标准库（urllib + xml.etree），不需要在 IDE 里装任何包。

工具名必须是 rss_reader —— 下面第 15 行的 import 路径里有两处 rss_reader，
它们对应的是「工具名」。如果你起名不同（比如 rss_fetch），这两处也要一起改。
"""
from runtime import Args
from typings.rss_reader.rss_reader import Input, Output

import re
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
}

# 匹配「没被转义的裸 &」——后面跟着合法实体名（amp; / #123; / #x1f;）的不算
_BARE_AMP = re.compile(rb"&(?!(?:#[0-9]+|#x[0-9a-fA-F]+|[A-Za-z_][\w.-]*);)")


def _fetch(url: str, timeout: int = 15) -> bytes:
    """把 RSS 地址的原始内容抓回来。

    刻意返回 bytes 而不是 str —— xml.etree 会自己读 XML 声明里的 encoding，
    有些源不是 UTF-8（GBK / ISO-8859-1），先 decode 反而会炸。
    """
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _local(tag: str) -> str:
    """去掉命名空间的方括号部分：'{http://www.w3.org/2005/Atom}title' -> 'title'"""
    return tag.split("}", 1)[1] if "}" in tag else tag


def _text(node, *names) -> str:
    """按 names 给出的**优先级**在 node 的直接子节点里找第一个有内容的文本。

    注意是「先看有没有 link，没有再看 guid」——而不是「谁的标签先出现就用谁」。
    虎嗅的 item 顺序是 <id><guid><link>，按出现顺序会取到 4891940 这种纯数字 ID。

    同时兼容两种写法：
        RSS  : <title>标题</title>
        Atom : <link href="https://..."/>
    """
    for name in names:
        for child in node:
            if _local(child.tag) != name:
                continue
            if child.text and child.text.strip():
                return child.text.strip()
            href = child.get("href")
            if href:
                return href.strip()
    return ""


def _parse(xml_bytes: bytes, limit: int):
    """解析 RSS 2.0 / RDF / Atom 三种常见格式，返回 (源名称, 条目列表)。"""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        # 有些源的正文里裸 & 没转义（例如标题写作 "A&B"），标准库解析器会直接拒绝。
        # 把不合法的 & 补成 &amp; 再试一次；已经合法的实体不受影响。
        root = ET.fromstring(_BARE_AMP.sub(b"&amp;", xml_bytes))

    # RSS 2.0 的标题在 <channel> 下；Atom 直接在根 <feed> 下
    container = root
    for el in root.iter():
        if _local(el.tag) == "channel":
            container = el
            break
    source = _text(container, "title")

    # RSS 用 <item>，Atom 用 <entry>，两种都收
    nodes = [el for el in root.iter() if _local(el.tag) in ("item", "entry")]

    items = []
    for node in nodes[:limit]:
        items.append({
            "title": _text(node, "title"),
            "link": _text(node, "link", "guid", "id"),
            "pubDate": _text(node, "pubDate", "published", "updated", "date"),
            "source": source,
        })
    return source, items


def handler(args: Args[Input]) -> Output:
    url = (getattr(args.input, "rss_url", "") or "").strip()
    limit = getattr(args.input, "limit", 0) or 5

    if not url:
        return {"items": [], "count": 0, "summary": "", "message": "rss_url 不能为空"}

    try:
        xml_bytes = _fetch(url)
    except urllib.error.HTTPError as e:
        args.logger.info(f"HTTP {e.code} <- {url}")
        return {"items": [], "count": 0, "summary": "",
                "message": f"抓取失败：HTTP {e.code}（{url}）"}
    except Exception as e:
        args.logger.info(f"fetch failed: {type(e).__name__} {e} <- {url}")
        return {"items": [], "count": 0, "summary": "",
                "message": f"抓取失败：{type(e).__name__} {e}（{url}）"}

    # 先确认抓回来的真的是订阅源。反爬页 / 登录页 / 首页都会返回 200，
    # 只有走到解析那一步才炸，错误信息会很难懂，所以这里提前拦一道。
    probe = xml_bytes[:600].decode("utf-8", errors="ignore").lower()
    if not any(k in probe for k in ("<rss", "<feed", "<rdf")):
        args.logger.info(f"not a feed: {url}")
        return {"items": [], "count": 0, "summary": "",
                "message": f"该地址返回的不是 RSS/Atom（可能被反爬拦截，或它根本不是订阅源）：{url}"}

    try:
        source, items = _parse(xml_bytes, int(limit))
    except Exception as e:
        args.logger.info(f"parse failed: {type(e).__name__} {e} <- {url}")
        return {"items": [], "count": 0, "summary": "",
                "message": f"解析失败：{type(e).__name__} {e}（{url}）"}

    lines = []
    for i, it in enumerate(items, 1):
        lines.append(f"{i}. 【{it['title']}】\n   链接：{it['link']}\n   时间：{it['pubDate']}")

    args.logger.info(f"解析到 {len(items)} 条，来源：{source}")
    return {
        "items": items,
        "count": len(items),
        "summary": f"来源：{source}\n共 {len(items)} 条\n\n" + "\n".join(lines),
        "message": "ok",
    }
