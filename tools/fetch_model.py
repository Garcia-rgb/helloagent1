# -*- coding: utf-8 -*-
"""
第3章 · 本地模型下载器

从 ModelScope 直接拉取模型仓库文件（不依赖 modelscope SDK，也不需要 HuggingFace）。
支持断点续传、大小校验、失败重试。

用法:
    python fetch_model.py                          # 默认 Qwen/Qwen1.5-0.5B-Chat
    python fetch_model.py Qwen/Qwen3-0.6B          # 换模型
"""
import json
import os
import sys
import time

import requests

REPO_ROOT = r"D:\NewFolder\hello-agents-main"
MODELS_DIR = os.path.join(REPO_ROOT, "models")
LOG = os.path.join(REPO_ROOT, "_model_download.log")

DEFAULT_MODEL = "Qwen/Qwen1.5-0.5B-Chat"
API = "https://www.modelscope.cn/api/v1/models/{mid}/repo"

_log_lines = []


def log(msg=""):
    print(msg)
    _log_lines.append(str(msg))


def flush_log():
    with open(LOG, "w", encoding="utf-8") as f:
        f.write("\n".join(_log_lines))


def make_session():
    """关掉环境代理与 retry，避免被沙箱/系统代理劫持"""
    s = requests.Session()
    s.trust_env = False
    s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    return s


def list_files(session, model_id, revision="master"):
    url = (f"https://www.modelscope.cn/api/v1/models/{model_id}/repo/files"
           f"?Revision={revision}&Recursive=true")
    r = session.get(url, timeout=60)
    r.raise_for_status()
    data = r.json()
    files = data.get("Data", {}).get("Files", [])
    out = []
    for f in files:
        if f.get("Type") == "tree":
            continue
        out.append({"path": f["Path"], "size": int(f.get("Size", 0))})
    return out


def download_one(session, model_id, item, dest_root, revision="master"):
    rel = item["path"]
    expect = item["size"]
    dest = os.path.join(dest_root, rel.replace("/", os.sep))
    os.makedirs(os.path.dirname(dest), exist_ok=True)

    # 已完整下载则跳过
    if os.path.exists(dest) and os.path.getsize(dest) == expect and expect > 0:
        log(f"    [跳过] {rel}  已存在且大小一致 ({expect/2**20:.2f} MB)")
        return "skip"

    url = API.format(mid=model_id) + f"?Revision={revision}&FilePath={rel}"

    for attempt in range(1, 6):
        have = os.path.getsize(dest) if os.path.exists(dest) else 0
        if have > expect:
            have = 0
        headers = {}
        if have:
            headers["Range"] = f"bytes={have}-"
        mode = "ab" if have else "wb"
        try:
            t0 = time.time()
            with session.get(url, headers=headers, stream=True, timeout=(20, 120)) as r:
                if r.status_code not in (200, 206):
                    raise RuntimeError(f"HTTP {r.status_code}")
                total = expect
                got = have
                last_report = 0.0
                with open(dest, mode) as f:
                    for chunk in r.iter_content(chunk_size=1 << 18):
                        if not chunk:
                            continue
                        f.write(chunk)
                        got += len(chunk)
                        now = time.time()
                        if now - last_report > 3 or got >= total:
                            last_report = now
                            pct = got / total * 100 if total else 0
                            speed = (got - have) / max(now - t0, 1e-6) / 2**20
                            log(f"    {rel}  {got/2**20:7.1f}/{total/2**20:.1f} MB "
                                f"({pct:5.1f}%)  {speed:.2f} MB/s")
            actual = os.path.getsize(dest)
            if expect and actual != expect:
                raise RuntimeError(f"大小不符: 得到 {actual}, 期望 {expect}")
            log(f"    [完成] {rel}  {actual/2**20:.2f} MB  用时 {time.time()-t0:.1f}s")
            return "ok"
        except Exception as e:
            log(f"    [重试 {attempt}/5] {rel}  {type(e).__name__}: {str(e)[:120]}")
            if attempt == 5:
                raise
            time.sleep(2 * attempt)
    return "fail"


def main():
    model_id = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MODEL
    dest_root = os.path.join(MODELS_DIR, model_id.split("/")[-1])

    log("=" * 60)
    log(f"模型      : {model_id}")
    log(f"目标目录  : {dest_root}")
    log(f"开始时间  : {time.strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 60)

    session = make_session()

    log("")
    log("[1/2] 获取文件清单 ...")
    files = list_files(session, model_id)
    total = sum(f["size"] for f in files)
    log(f"      共 {len(files)} 个文件，合计 {total/2**20:.1f} MB")
    for f in files:
        log(f"        {f['path']:<40} {f['size']/2**20:9.2f} MB")

    log("")
    log("[2/2] 开始下载 ...")
    t0 = time.time()
    results = {}
    for f in files:
        try:
            results[f["path"]] = download_one(session, model_id, f, dest_root)
        except Exception as e:
            log(f"    [失败] {f['path']}  {type(e).__name__}: {e}")
            results[f["path"]] = "fail"

    log("")
    log("=" * 60)
    log(f"总用时    : {time.time()-t0:.1f} 秒")
    log(f"结果统计  : 完成 {sum(1 for v in results.values() if v=='ok')}  "
        f"跳过 {sum(1 for v in results.values() if v=='skip')}  "
        f"失败 {sum(1 for v in results.values() if v=='fail')}")

    # 落地校验
    log("")
    log("落盘校验：")
    all_ok = True
    for f in files:
        p = os.path.join(dest_root, f["path"].replace("/", os.sep))
        if not os.path.exists(p):
            log(f"    缺失: {f['path']}")
            all_ok = False
        else:
            sz = os.path.getsize(p)
            flag = "OK " if sz == f["size"] else "大小不符"
            if sz != f["size"]:
                all_ok = False
            log(f"    {flag} {f['path']:<40} {sz/2**20:9.2f} MB")

    log("")
    log(f"结论      : {'全部文件下载完成且大小校验通过' if all_ok else '存在缺失或大小不符，见上'}")
    log("=" * 60)

    flush_log()
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
