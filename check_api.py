"""环境连通性自检：天气 API / LLM API / Tavily API

用法（在任意目录）：
    D:\\NewFolder\\hello-agents-main\\Hello-Agents\\.venv\\Scripts\\python.exe D:\\NewFolder\\hello-agents-main\\check_api.py

前提：先把 key 填进 Hello-Agents\\.env

设计说明：
  本机内网 DNS 会把 api.deepseek.com 解析到不可达的 IP，导致直连超时。
  所以 LLM 部分会依次尝试三条通道，哪条通用哪条，并把结论打在最后：
    A 直连 -> B 公共 DNS 解析后按 IP 直连 -> C 本地代理端口
"""

import os
import pathlib
import socket

import requests
from dotenv import load_dotenv

ENV = pathlib.Path(r"D:\NewFolder\hello-agents-main\Hello-Agents\.env")
load_dotenv(ENV)

LLM_HOST = "api.deepseek.com"
DOH_SERVERS = ["223.5.5.5", "119.29.29.29", "1.1.1.1"]
LOCAL_PROXY_PORTS = [7897, 7890, 7899, 8889, 10809, 1080]

_orig_getaddrinfo = socket.getaddrinfo
WINNER = None


def section(title: str) -> None:
    print()
    print(title)
    print("-" * 52)


def is_filled(value: str) -> bool:
    return bool(value) and not value.startswith("YOUR_")


def tcp_ok(host: str, port: int = 443, timeout: float = 4.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def doh_resolve(host: str) -> list:
    """用 DoH 拿真实 A 记录（绕过被污染的本机 DNS）"""
    ips = []
    for srv in DOH_SERVERS:
        try:
            s = requests.Session()
            s.trust_env = False
            r = s.get(f"https://{srv}/resolve",
                      params={"name": host, "type": "A"},
                      headers={"accept": "application/dns-json"}, timeout=8)
            for a in r.json().get("Answer", []):
                if a.get("type") == 1 and a.get("data") not in ips:
                    ips.append(a["data"])
            if ips:
                print(f"    DoH {srv} -> {ips}")
                return ips
        except Exception as e:
            print(f"    DoH {srv} 失败: {type(e).__name__}")
    return ips


def try_chat(base, key, model, *, proxy=None, pin_ip=None):
    """跑一次最小 chat 调用。返回 (是否成功, 信息)"""
    if pin_ip:
        def patched(host, port, family=0, type_=0, proto=0, flags=0):
            if host == LLM_HOST:
                host = pin_ip
            return _orig_getaddrinfo(host, port, family, type_, proto, flags)
        socket.getaddrinfo = patched
    try:
        s = requests.Session()
        s.trust_env = False
        s.proxies = ({"http": proxy, "https": proxy} if proxy
                     else {"http": None, "https": None})
        r = s.post(f"{base}/chat/completions",
                   headers={"Authorization": f"Bearer {key}",
                            "Content-Type": "application/json"},
                   json={"model": model,
                         "messages": [{"role": "user",
                                       "content": "只回复两个字：通了"}],
                         "max_tokens": 20},
                   timeout=12)
        if r.status_code == 200:
            return True, r.json()["choices"][0]["message"]["content"].strip()
        return False, f"HTTP {r.status_code} {r.text[:120]}"
    except Exception as e:
        return False, f"{type(e).__name__}: {str(e)[:120]}"
    finally:
        socket.getaddrinfo = _orig_getaddrinfo


# ==========================================================================
section("1/3  天气 API (wttr.in，不需要 key)")
try:
    resp = requests.get("https://wttr.in/Beijing?format=j1", timeout=20)
    print("状态码:", resp.status_code)
    cur = resp.json()["current_condition"][0]
    print("北京:", cur["weatherDesc"][0]["value"], cur["temp_C"], "摄氏度")
except Exception as exc:
    print("失败:", type(exc).__name__, exc)


# ==========================================================================
section("2/3  LLM API")
key = os.getenv("LLM_API_KEY", "")
base = os.getenv("LLM_BASE_URL", "")
model = os.getenv("LLM_MODEL_ID", "")
print("base_url:", base)
print("model   :", model)
print("api_key :", f"已填写（{len(key)} 位）" if is_filled(key) else "未填写")

if not is_filled(key):
    print("跳过 —— 请先在 .env 里填 LLM_API_KEY")
else:
    try:
        local = sorted({i[4][0] for i in
                        socket.getaddrinfo(LLM_HOST, 443, proto=socket.IPPROTO_TCP)})
    except Exception as e:
        local = f"失败 {type(e).__name__}"
    print("本机 DNS 解析:", local)

    print("\n  [A] 直连")
    ok, msg = try_chat(base, key, model)
    print("      ", ("OK   " + msg) if ok else ("FAIL " + msg))
    if ok:
        WINNER = ("A 直连（DNS 正常）", None)

    if not WINNER:
        print("\n  [B] 公共 DNS 解析后按 IP 直连")
        for ip in doh_resolve(LLM_HOST):
            if not tcp_ok(ip):
                print(f"    {ip} 端口不通，跳过")
                continue
            ok, msg = try_chat(base, key, model, pin_ip=ip)
            print("      ", ("OK   " + msg) if ok else ("FAIL " + msg), f"({ip})")
            if ok:
                WINNER = (f"B 指定节点直连 {ip}", ip)
                break

    if not WINNER:
        print("\n  [C] 本地代理端口")
        ports = [p for p in LOCAL_PROXY_PORTS if tcp_ok("127.0.0.1", p, timeout=1.5)]
        print("    监听中:", ports or "无")
        for p in ports:
            px = f"http://127.0.0.1:{p}"
            ok, msg = try_chat(base, key, model, proxy=px)
            print("      ", ("OK   " + msg) if ok else ("FAIL " + msg), f"({px})")
            if ok:
                WINNER = (f"C 本地代理 {px}", px)
                break

    print("\n  >>> LLM 结论:",
          f"可用 —— 通道 {WINNER[0]}" if WINNER else "三条通道全部失败")


# ==========================================================================
section("3/3  Tavily API")
tav = os.getenv("TAVILY_API_KEY", "")
print("api_key :", f"已填写（{len(tav)} 位）" if is_filled(tav) else "未填写")

if not is_filled(tav):
    print("跳过 —— 请先在 .env 里填 TAVILY_API_KEY")
else:
    try:
        from tavily import TavilyClient

        res = TavilyClient(api_key=tav).search(
            "杭州今天天气", search_depth="basic", include_answer=True)
        print("搜索成功:", (res.get("answer") or "(无 answer 字段)")[:100])
    except Exception as exc:
        print("失败:", type(exc).__name__, exc)


# ==========================================================================
print()
print("=" * 52)
print("自检结束")
if WINNER:
    print("LLM 可用通道:", WINNER[0])
    if WINNER[0].startswith("B"):
        print("提示：直连不通是本机 DNS 解析问题，见脚本头部说明。")
    elif WINNER[0].startswith("C"):
        print("提示：直连不通，目前只能靠本地代理。建议固定一个长期方案。")
