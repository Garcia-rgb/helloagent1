#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按关键词检索 GitHub 仓库 / arXiv 论文，输出可读列表。

纯标准库，零依赖 —— 平台侧装不了第三方包，只用标准库是唯一能活的那种写法。

对应教程第 5 章 Coze 案例里那两个信息源插件：
    GitHub 插件（工具 searchRepository）  参数 q / per_page / sort
    arXiv  插件（工具 searcharXiv）       参数 count / search_query / sort_by
本脚本用两个站的公开 API 把同样的检索语义实现出来，不依赖插件市场里有没有。

用法:
    python3 search_sources.py github --query AI --min-stars 500 --limit 5
    python3 search_sources.py github --query "language:python stars:>3000" --sort stars --limit 5
    python3 search_sources.py arxiv  --query "cat:cs.AI" --limit 5
    python3 search_sources.py arxiv  --query "all:\"large language model\"" --sort relevance --limit 5
    python3 search_sources.py both   --query AI --limit 3
    python3 search_sources.py github --query AI --json
"""

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

GH_API = "https://api.github.com/search/repositories"
ARXIV_API = "http://export.arxiv.org/api/query"

# 允许的排序值。GitHub 的 updated 对应教程里的 sort=updated
GH_SORTS = ("best-match", "stars", "forks", "updated")
ARXIV_SORTS = ("relevance", "lastUpdatedDate", "submittedDate")

SORT_CN = {
    "updated": "最近更新",
    "stars": "星标最多",
    "forks": "fork 最多",
    "best-match": "最佳匹配",
    "submittedDate": "提交时间",
    "lastUpdatedDate": "最近更新",
    "relevance": "相关度",
}

ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"

CST = timezone(timedelta(hours=8))


def fetch(url: str, headers: dict = None, timeout: int = 25) -> bytes:
    h = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def to_cst(iso: str) -> str:
    """ISO8601（UTC，形如 2026-09-17T13:45:12Z）换成东八区 YYYY-MM-DD HH:MM。

    解析不了就原样返回，不要把空值补成别的东西。
    """
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(iso.strip().replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(CST).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return iso


def flat(text) -> str:
    """把 XML 里换行缩进的文本压成一行。"""
    return " ".join((text or "").split())


# ----------------------------------------------------------------- GitHub


def search_github(query: str, limit: int, sort: str):
    params = {"q": query, "per_page": str(min(limit, 100))}
    if sort and sort != "best-match":
        params["sort"] = sort
        params["order"] = "desc"

    url = GH_API + "?" + urllib.parse.urlencode(params)
    data = json.loads(
        fetch(url, {"Accept": "application/vnd.github+json"}).decode("utf-8", "replace")
    )

    items = []
    for it in (data.get("items") or [])[:limit]:
        items.append(
            {
                "name": it.get("full_name") or "",
                "url": it.get("html_url") or "",
                "description": (it.get("description") or "").strip(),
                "stars": int(it.get("stargazers_count") or 0),
                "forks": int(it.get("forks_count") or 0),
                "language": it.get("language") or "",
                "pushed_at": to_cst(it.get("pushed_at") or ""),
            }
        )
    return items, int(data.get("total_count") or len(items))


# ------------------------------------------------------------------ arXiv


def search_arxiv(query: str, limit: int, sort_by: str):
    params = {
        "search_query": query,
        "start": "0",
        "max_results": str(min(limit, 100)),
        "sortBy": sort_by,
        "sortOrder": "descending",
    }
    url = ARXIV_API + "?" + urllib.parse.urlencode(params)
    root = ET.fromstring(fetch(url))

    items = []
    for e in root.findall(ATOM + "entry")[:limit]:
        authors = [flat(a.findtext(ATOM + "name")) for a in e.findall(ATOM + "author")]
        authors = [a for a in authors if a]
        if len(authors) > 3:
            author_str = ", ".join(authors[:3]) + " 等 %d 人" % len(authors)
        else:
            author_str = ", ".join(authors)

        cat = e.find(ARXIV_NS + "primary_category")

        items.append(
            {
                "title": flat(e.findtext(ATOM + "title")),
                # id 形如 http://arxiv.org/abs/2509.12345v1
                "url": flat(e.findtext(ATOM + "id")),
                "published": to_cst(flat(e.findtext(ATOM + "published"))),
                "updated": to_cst(flat(e.findtext(ATOM + "updated"))),
                "authors": author_str,
                "category": (cat.get("term") if cat is not None else "") or "",
                "summary": flat(e.findtext(ATOM + "summary"))[:300],
            }
        )
    return items, len(items)


# ----------------------------------------------------------------- 渲染


def render_github(query: str, sort: str, items, total: int) -> str:
    lines = [
        "=== GitHub 仓库检索「%s」· 按%s · %d 条（全站命中 %d） ==="
        % (query, SORT_CN.get(sort, sort), len(items), total),
        "",
    ]
    for i, it in enumerate(items, 1):
        lines.append("[%d] %s" % (i, it["name"]))
        if it["description"]:
            lines.append("    " + it["description"])
        lines.append("    " + it["url"])
        meta = ["%d stars" % it["stars"], "%d forks" % it["forks"]]
        if it["language"]:
            meta.append(it["language"])
        if it["pushed_at"]:
            meta.append("最近推送 " + it["pushed_at"])
        lines.append("    " + "  ·  ".join(meta))
        lines.append("")
    return "\n".join(lines)


def render_arxiv(query: str, sort_by: str, items) -> str:
    lines = [
        "=== arXiv 论文检索「%s」· 按%s倒序 · %d 条 ==="
        % (query, SORT_CN.get(sort_by, sort_by), len(items)),
        "",
    ]
    for i, it in enumerate(items, 1):
        lines.append("[%d] %s" % (i, it["title"]))
        lines.append("    " + it["url"])
        meta = []
        if it["category"]:
            meta.append(it["category"])
        if it["published"]:
            meta.append("提交 " + it["published"])
        if meta:
            lines.append("    " + "  ·  ".join(meta))
        if it["authors"]:
            lines.append("    作者：" + it["authors"])
        if it["summary"]:
            lines.append("    摘要：" + it["summary"])
        lines.append("")
    return "\n".join(lines)


# ------------------------------------------------------------------ main


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="检索 GitHub 仓库与 arXiv 论文（纯标准库，零依赖）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("source", choices=("github", "arxiv", "both"), help="检索哪个源")
    p.add_argument("-q", "--query", required=True, help="检索词")
    p.add_argument("--limit", type=int, default=5, help="返回几条，默认 5，上限 50")
    p.add_argument(
        "--min-stars",
        type=int,
        default=0,
        help="只保留星标数不低于该值的仓库（仅 GitHub）。按 updated 排序时不加门槛会"
        "刷出一堆刚建的空仓库，做简报建议设 100 以上",
    )
    p.add_argument(
        "--sort",
        default=None,
        help="github: best-match|stars|forks|updated（默认 updated）；"
        "arxiv: relevance|lastUpdatedDate|submittedDate（默认 submittedDate）",
    )
    p.add_argument("--json", action="store_true", help="输出 JSON，进度信息走 stderr")
    args = p.parse_args(argv)

    limit = max(1, min(50, args.limit))
    args.limit = limit

    gh_sort = args.sort or "updated"
    arx_sort = args.sort or "submittedDate"

    if args.source in ("github", "both") and gh_sort not in GH_SORTS:
        sys.stderr.write(
            "GitHub 的 --sort 只能填 %s，收到的是 %r\n" % ("|".join(GH_SORTS), gh_sort)
        )
        return 2
    if args.source in ("arxiv", "both") and arx_sort not in ARXIV_SORTS:
        sys.stderr.write(
            "arXiv 的 --sort 只能填 %s，收到的是 %r\n" % ("|".join(ARXIV_SORTS), arx_sort)
        )
        return 2

    # 星标门槛直接拼进 GitHub 的查询串（arXiv 没有这个概念）
    gh_query = args.query
    if args.min_stars > 0:
        gh_query = "%s stars:>%d" % (args.query, args.min_stars)

    result = {}
    problems = []
    ok = 0

    if args.source in ("github", "both"):
        try:
            items, total = search_github(gh_query, limit, gh_sort)
            result["github"] = {
                "query": gh_query,
                "sort": gh_sort,
                "count": len(items),
                "total_count": total,
                "items": items,
                "message": "ok",
            }
            ok += 1
        except urllib.error.HTTPError as e:
            hint = ""
            if e.code == 403:
                hint = "（未认证的搜索请求限速为每分钟 10 次，等一会儿再试）"
            elif e.code == 422:
                hint = "（检索语法不对，检查一下限定符写法）"
            problems.append("github: HTTP %d %s%s" % (e.code, e.reason, hint))
        except Exception as e:
            problems.append("github: %s: %s" % (type(e).__name__, e))

    if args.source in ("arxiv", "both"):
        try:
            items, _ = search_arxiv(args.query, limit, arx_sort)
            result["arxiv"] = {
                "query": args.query,
                "sort": arx_sort,
                "count": len(items),
                "items": items,
                "message": "ok",
            }
            ok += 1
        except urllib.error.HTTPError as e:
            problems.append("arxiv: HTTP %d %s" % (e.code, e.reason))
        except Exception as e:
            problems.append("arxiv: %s: %s" % (type(e).__name__, e))

    if args.json:
        out = result if args.source == "both" else (
            result.get(args.source) or {"count": 0, "items": [], "message": "failed"}
        )
        sys.stdout.write(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    else:
        blocks = []
        if "github" in result:
            blocks.append(
                render_github(gh_query, gh_sort, result["github"]["items"],
                              result["github"]["total_count"])
            )
        if "arxiv" in result:
            blocks.append(
                render_arxiv(args.query, arx_sort, result["arxiv"]["items"])
            )
        if blocks:
            sys.stdout.write("\n".join(blocks) + "\n")
        total_sources = 1 if args.source in ("github", "arxiv") else 2
        sys.stdout.write("成功 %d / 共 %d 个源\n" % (ok, total_sources))
        for prob in problems:
            sys.stdout.write("  ! " + prob + "\n")

    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
