"""
比特币实时价格显示应用
数据源：CoinGecko Public API v3（免费、无需 API Key）
"""

import traceback
from datetime import datetime
from typing import Any, Dict

import requests
import streamlit as st
from streamlit.delta_generator import DeltaGenerator

# ============ 配置常量 ============
API_URL = "https://api.coingecko.com/api/v3/simple/price"
API_TIMEOUT = 10
CACHE_TTL = 60

# 跌幅接近 -100% 时，反推公式分母 1 + pct/100 趋近于 0，结果会爆炸式放大。
# 取 -99%（对应价格约为 24h 前的 1%）作为安全边界。
EXTREME_PCT_THRESHOLD = -99.0

# ============ 页面基础配置 ============
st.set_page_config(
    page_title="比特币实时价格",
    page_icon="₿",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ============ 自定义 CSS ============
st.markdown(
    """
    <style>
        .price-card {
            background: linear-gradient(135deg, #1e1e2e 0%, #2d2d44 100%);
            border-radius: 16px;
            padding: 32px 24px;
            text-align: center;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
            margin-bottom: 16px;
        }
        .price-label {
            color: #a0a0b8;
            font-size: 16px;
            letter-spacing: 2px;
            margin-bottom: 8px;
        }
        .price-value {
            color: #ffffff;
            font-size: 56px;
            font-weight: 700;
            font-family: 'Segoe UI', monospace;
            margin: 0;
            line-height: 1.2;
        }
        .price-change {
            font-size: 22px;
            font-weight: 600;
            margin-top: 12px;
        }
        .change-up   { color: #00d18f; }
        .change-down { color: #ff4d6d; }
        .change-flat { color: #a0a0b8; }
        .meta-text {
            color: #7a7a92;
            font-size: 13px;
            text-align: center;
            margin-top: 8px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============ 数据获取层 ============
@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def fetch_btc_price() -> Dict[str, Any]:
    """
    从 CoinGecko 拉取 BTC 对 USD 的价格及 24h 变化数据。

    注意：所有插入 HTML 的字段必须来源可信（当前仅使用自生成的 updated_at）。
    """
    params = {
        "ids": "bitcoin",
        "vs_currencies": "usd",
        "include_24hr_change": "true",
    }
    headers = {"Accept": "application/json", "User-Agent": "BTC-Price-App/1.0"}

    resp = requests.get(API_URL, params=params, headers=headers, timeout=API_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()

    if "bitcoin" not in data:
        raise ValueError("API 响应中缺少 bitcoin 字段")
    btc = data["bitcoin"]

    # 显式类型校验，避免 float("N/A") 造成的不友好错误
    usd_val = btc.get("usd")
    if not isinstance(usd_val, (int, float)):
        raise ValueError(f"价格字段类型异常：{usd_val!r}")
    price = float(usd_val)

    raw_pct = btc.get("usd_24h_change", 0.0)
    if not isinstance(raw_pct, (int, float)):
        raw_pct = 0.0
    change_pct = float(raw_pct)

    # 由 涨跌幅 反推 涨跌额：change_abs = price * pct / (100 + pct)
    if change_pct <= EXTREME_PCT_THRESHOLD:
        change_abs = 0.0
    else:
        change_abs = price * (change_pct / 100.0) / (1 + change_pct / 100.0)

    return {
        "price": price,
        "change_24h": change_abs,
        "change_pct_24h": change_pct,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# ============ 工具函数 ============
def format_money(value: float, show_sign: bool = False) -> str:
    """格式化美元金额，例如 $67,432.15 或 +$1,234.56"""
    sign = ""
    if show_sign:
        sign = "+" if value > 0 else ("-" if value < 0 else "")
    return f"{sign}${abs(value):,.2f}"


def format_percent(value: float) -> str:
    """格式化百分比，例如 +1.23% / -0.45% / 0.00%"""
    if value > 0:
        return f"+{value:.2f}%"
    elif value < 0:
        return f"{value:.2f}%"
    return "0.00%"


def change_css_class(value: float) -> str:
    """根据涨跌返回对应的 CSS 类名"""
    if value > 0:
        return "change-up"
    elif value < 0:
        return "change-down"
    return "change-flat"


# ============ UI 展示层 ============
def render_price_card(data: Dict[str, Any]) -> None:
    """渲染价格主卡片"""
    price = data["price"]
    change_abs = data["change_24h"]
    change_pct = data["change_pct_24h"]
    css_cls = change_css_class(change_pct)

    arrow = "▲" if change_pct > 0 else ("▼" if change_pct < 0 else "—")

    st.markdown(
        f"""
        <div class="price-card">
            <div class="price-label">BITCOIN / USD</div>
            <div class="price-value">{format_money(price)}</div>
            <div class="price-change {css_cls}">
                {arrow} {format_money(change_abs, show_sign=True)}
                （{format_percent(change_pct)}） 24h
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="meta-text">最后更新：{data["updated_at"]} · '
        f"数据源：CoinGecko</div>",
        unsafe_allow_html=True,
    )


def render_placeholder() -> None:
    """加载失败时展示的占位卡片"""
    st.markdown(
        """
        <div class="price-card">
            <div class="price-label">BITCOIN / USD</div>
            <div class="price-value">$ -- , --.--</div>
            <div class="price-change change-flat">数据暂不可用</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_error(message: str) -> None:
    """渲染友好的错误提示"""
    st.error(f"⚠️ 获取比特币价格失败：{message}")
    st.info(
        "可能原因：网络异常、本地 DNS 问题，或 CoinGecko API 临时限流。"
        "请稍后点击下方「刷新」重试。"
    )


def render_failure(placeholder: DeltaGenerator, message: str) -> None:
    """
    统一的失败态渲染：清占位 -> 占位卡片 -> 错误提示

    Args:
        placeholder: 由 st.empty() 返回的占位容器。
        message: 面向用户的错误描述。
    """
    placeholder.empty()
    render_placeholder()
    render_error(message)


# ============ 主流程 ============
def main() -> None:
    st.title("₿ 比特币实时价格")
    st.caption("实时查看 BTC 对美元的最新价格及 24 小时变化")

    # 顶部操作栏
    col_left, _ = st.columns([1, 3])
    with col_left:
        refresh_clicked = st.button("🔄 刷新", use_container_width=True, type="primary")

    # 刷新：清缓存 + 打标志 + rerun（请求统一由主流程发起）
    if refresh_clicked:
        fetch_btc_price.clear()
        st.session_state["just_refreshed"] = True
        st.rerun()

    # 主展示区
    placeholder = st.empty()
    with placeholder.container():
        with st.spinner("⏳ 正在加载比特币价格..."):
            try:
                data = fetch_btc_price()
            except requests.exceptions.Timeout:
                # 保留 just_refreshed 标志，留给下一次成功渲染时弹 toast
                render_failure(placeholder, "请求超时，请检查网络后重试。")
                return
            except requests.exceptions.HTTPError as e:
                status = getattr(e.response, "status_code", "未知")
                if status == 429:
                    render_failure(placeholder, "API 请求过于频繁（429），请稍等片刻再刷新。")
                else:
                    render_failure(placeholder, f"服务端返回异常状态码 {status}。")
                return
            except requests.exceptions.RequestException as e:
                render_failure(placeholder, f"网络请求失败：{e.__class__.__name__}")
                return
            except ValueError as e:
                render_failure(placeholder, f"数据解析异常：{e}")
                return
            except Exception as e:
                # 兜底分支：真实 bug 不应被静默吞掉，打印堆栈便于排查
                traceback.print_exc()
                render_failure(placeholder, f"未知错误：{type(e).__name__}")
                return

    # 成功态渲染
    placeholder.empty()
    render_price_card(data)

    # 数据确认拿到后，才反馈"已更新"，语义与结果对齐
    if st.session_state.pop("just_refreshed", False):
        st.toast("已更新", icon="✅")

    # 底部说明
    st.divider()
    st.caption(
        "💡 说明：数据缓存 60 秒以降低 API 调用频率；"
        "点击「刷新」可强制重新拉取。价格为 CoinGecko 聚合的 USD 市场价。"
    )


if __name__ == "__main__":
    main()
