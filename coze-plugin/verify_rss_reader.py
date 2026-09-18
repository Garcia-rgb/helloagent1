# -*- coding: utf-8 -*-
"""本地验证 coze-plugin/rss_reader.py

Coze IDE 里那两行 import（runtime / typings）在本地不存在，
这里先往 sys.modules 里塞两个假的，再把插件文件当普通模块加载进来跑。
这样测的就是**将要粘贴到平台的同一份代码**，不是它的改写版。
"""
import importlib.util
import os
import sys
import types

ROOT = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.join(ROOT, "coze-plugin", "rss_reader.py")

# ---------------- 1. 造假 runtime ----------------
runtime_mod = types.ModuleType("runtime")


class _FakeLogger:
    def info(self, msg):
        print(f"    [logger] {msg}")


class _FakeArgs:
    def __init__(self, input_obj):
        self.input = input_obj
        self.logger = _FakeLogger()


class Args:
    def __class_getitem__(cls, item):  # 让 Args[Input] 这种写法不报错
        return cls


runtime_mod.Args = Args
sys.modules["runtime"] = runtime_mod

# ---------------- 2. 造假 typings.rss_reader.rss_reader ----------------
class Input:
    pass


class Output(dict):
    pass


pkg = types.ModuleType("typings")
pkg.__path__ = []
sub = types.ModuleType("typings.rss_reader")
sub.__path__ = []
leaf = types.ModuleType("typings.rss_reader.rss_reader")
leaf.Input = Input
leaf.Output = Output
sub.rss_reader = leaf
pkg.rss_reader = sub
sys.modules["typings"] = pkg
sys.modules["typings.rss_reader"] = sub
sys.modules["typings.rss_reader.rss_reader"] = leaf

# ---------------- 3. 加载插件本体 ----------------
spec = importlib.util.spec_from_file_location("plugin_rss_reader", PLUGIN)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def run(url, limit=3):
    class In:
        rss_url = url
        this = None

    inp = Input()
    inp.rss_url = url
    inp.limit = limit
    return mod.handler(_FakeArgs(inp))


SOURCES = [
    ("36氪", "https://www.36kr.com/feed"),
    ("虎嗅", "https://rss.huxiu.com/"),
    ("IT之家", "https://www.ithome.com/rss/"),
    ("InfoQ AI频道", "https://feed.infoq.com/ai-ml-data-eng/"),
    ("阮一峰博客(Atom)", "https://www.ruanyifeng.com/blog/atom.xml"),
    ("arXiv cs.AI", "http://export.arxiv.org/rss/cs.AI"),
    ("少数派", "https://sspai.com/feed"),
    ("量子位", "https://www.qbitai.com/feed"),
    ("Solidot", "https://www.solidot.org/index.rss"),
    ("GitHub releases(Atom)", "https://github.com/langchain-ai/langchain/releases.atom"),
]

print("=" * 70)
print("逐个源实测")
print("=" * 70)

ok, fail = 0, 0
for name, url in SOURCES:
    print(f"\n### {name}  {url}")
    r = run(url, limit=3)
    if r["count"]:
        ok += 1
        print(f"    count={r['count']}  message={r['message']}")
        for it in r["items"]:
            title = it["title"][:42]
            print(f"    - {title}")
            print(f"      {it['link'][:88]}")
            print(f"      {it['pubDate']}")
    else:
        fail += 1
        print(f"    count=0  message={r['message']}")

# ---------------- 4. 边界用例 ----------------
print("\n" + "=" * 70)
print("边界用例")
print("=" * 70)

print("\n[空地址]")
print("   ", run("", limit=3))

print("\n[不存在的域名]")
print("   ", run("https://this-host-does-not-exist-abc123.com/feed"))

print("\n[不是 XML 的页面]")
print("   ", run("https://www.baidu.com"))

print("\n[limit 不传 -> 默认 5]")
r = run("https://www.ithome.com/rss/")
print("    count =", r["count"])

print(f"\n汇总：成功 {ok} 个源，失败 {fail} 个源")
