#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RSS / Atom 读取器 —— 纯标准库实现，不需要安装任何第三方依赖。

用法:
    python rss_reader.py <rss_url> [<rss_url> ...] [--limit N] [--json]

例子:
    python rss_reader.py https://www.ithome.com/rss/ --limit 5
    python rss_reader.py https://www.36kr.com/feed https://rss.huxiu.com/ --limit 3

输出:
    默认是给人（和大模型）读的文本；加 --json 输出结构化 JSON。

退出码:
    0 = 至少一个源成功；2 = 全部失败；1 = 参数错误。
"""

import json
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
}

TIMEOUT = 20

# 裸 & 的容忍：先原样解析，失败再补成 &amp; 重试
_BAD_AMP = re.compile(rb"&(?!(?:#[0-9]+|#x[0-9a-fA-F]+|[A-Za-z_][\w.-]*);)")


def _fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read()


def _local(tag: str) -> str:
    """剥掉命名空间，Atom 的 {http://www.w3.org/2005/Atom}entry -> entry。"""
    return tag.rsplit("}", 1)[-1].lower() if "}" in tag else tag.lower()


def _text(node, *names) -> str:
    """按 names 的优先级找子节点的文本（不是按出现顺序）。

    同时兼容两种写法:
        RSS  : <title>标题</title>
        Atom : <link href="https://..."/>
    标签名统一小写比对，所以传 "pubDate" 和 "pubdate" 都可以。
    """
    wanted = [n.lower() for n in names]
    for name in wanted:
        for child in node:
            if _local(child.tag) != name:
                continue
            if child.text and child.text.strip():
                return child.text.strip()
            href = child.get("href")
            if href and href.strip():
                return href.strip()
    return ""


def _clean(text: str) -> str:
    """去标签、压空白。有些源把 HTML 塞进 title/description。"""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _when(raw: str) -> str:
    """把各种时间写法统一成 YYYY-MM-DD HH:MM（带时区的换算到东八区）。

    实测遇到的三种：
        IT之家  Thu, 17 Sep 2026 05:44:03 GMT      RFC822
        36氪    2026-09-17 11:17:07  +0800         不是 RFC822，得手动试格式
        虎嗅    Thu, 17 Sep 2026 13:52:13 +0800    RFC822
    都解析不了就原样返回，不猜。
    """
    if not raw:
        return ""
    s = re.sub(r"\s+", " ", raw).strip()

    dt = None
    for parse in (
        lambda: parsedate_to_datetime(s),
        lambda: datetime.strptime(s, "%Y-%m-%d %H:%M:%S %z"),
        lambda: datetime.strptime(s, "%Y-%m-%d %H:%M:%S"),
        lambda: datetime.strptime(s, "%Y-%m-%d %H:%M"),
        lambda: datetime.strptime(s, "%Y-%m-%d"),
    ):
        try:
            dt = parse()
            break
        except Exception:
            continue

    if dt is None:
        return s
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone(timedelta(hours=8)))
    return dt.strftime("%Y-%m-%d %H:%M")


def _link(node) -> str:
    """取条目链接。

    Atom 里一个 entry 可能有好几个 <link>（alternate / self），
    self 指向订阅源本身，不是文章，要跳过。
    没有再退回 guid / id（虎嗅的 guid 是纯数字编号，不是 URL）。
    """
    fallback = ""
    for child in node:
        if _local(child.tag) != "link":
            continue
        href = (child.get("href") or child.text or "").strip()
        if not href:
            continue
        if (child.get("rel") or "alternate").lower() == "self":
            fallback = fallback or href
            continue
        return href
    for name in ("guid", "id"):
        v = _text(node, name)
        if v.startswith("http"):
            return v
    return fallback


def _parse(xml_bytes: bytes, limit: int):
    """解析 RSS 2.0 / RDF / Atom，返回 (源名称, 条目列表)。"""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        root = ET.fromstring(_BAD_AMP.sub(rb"&amp;", xml_bytes))

    source = ""
    for child in root:
        if _local(child.tag) == "channel":          # RSS 2.0
            source = _clean(_text(child, "title"))
            break
    if not source:                                   # Atom / RDF
        source = _clean(_text(root, "title"))

    items = []
    for node in root.iter():
        tag = _local(node.tag)
        if tag not in ("item", "entry"):
            continue

        items.append(
            {
                "title": _clean(_text(node, "title")),
                "link": _link(node),
                "pubDate": _when(_text(node, "pubDate", "published", "updated", "date")),
                "source": source,
            }
        )
        if len(items) >= limit:
            break

    return source, items


def read_one(url: str, limit: int) -> dict:
    """抓一个源。任何异常都吞成结构化结果，绝不抛出去。"""
    url = (url or "").strip()
    if not url:
        return {"url": url, "source": "", "items": [], "message": "地址为空"}

    try:
        xml_bytes = _fetch(url)
    except urllib.error.HTTPError as e:
        return {"url": url, "source": "", "items": [],
                "message": "抓取失败：HTTP %s" % e.code}
    except Exception as e:
        return {"url": url, "source": "", "items": [],
                "message": "抓取失败：%s %s" % (type(e).__name__, e)}

    head = xml_bytes[:2000].lower()
    if not (b"<rss" in head or b"<feed" in head or b"<rdf" in head):
        return {"url": url, "source": "", "items": [],
                "message": "该地址返回的不是 RSS/Atom（可能被反爬拦截，或不是订阅源）"}

    try:
        source, items = _parse(xml_bytes, limit)
    except Exception as e:
        return {"url": url, "source": "", "items": [],
                "message": "解析失败：%s %s" % (type(e).__name__, e)}

    if not items:
        return {"url": url, "source": source, "items": [],
                "message": "解析成功但没有条目"}

    return {"url": url, "source": source, "items": items, "message": "ok"}


def render(results) -> str:
    lines = []
    for r in results:
        if r["message"] != "ok":
            lines.append("--- %s ---" % r["url"])
            lines.append("    不可用：%s" % r["message"])
            lines.append("")
            continue
        lines.append("--- %s · %d 条 ---" % (r["source"] or r["url"], len(r["items"])))
        for i, it in enumerate(r["items"], 1):
            lines.append("[%d] %s" % (i, it["title"] or "(无标题)"))
            tail = "    %s  ·  %s" % (it["link"] or "(无链接)", it["pubDate"] or "(无时间)")
            lines.append(tail)
        lines.append("")
    ok = sum(1 for r in results if r["message"] == "ok")
    lines.append("成功 %d / 共 %d 个源" % (ok, len(results)))
    return "\n".join(lines)


def main(argv):
    urls, limit, as_json = [], 5, False
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--limit":
            i += 1
            if i >= len(argv):
                print("--limit 后面要跟一个数字", file=sys.stderr)
                return 1
            try:
                limit = max(1, min(50, int(argv[i])))
            except ValueError:
                print("--limit 要跟整数", file=sys.stderr)
                return 1
        elif a == "--json":
            as_json = True
        elif a in ("-h", "--help"):
            print(__doc__)
            return 0
        else:
            urls.append(a)
        i += 1

    if not urls:
        print(__doc__)
        return 1

    results = [read_one(u, limit) for u in urls]

    if as_json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(render(results))

    return 0 if any(r["message"] == "ok" for r in results) else 2


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main(sys.argv[1:]))
