import datetime
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np
import pandas as pd
import requests
import yfinance as yf
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import scipy.stats as stats
import scipy.optimize as sco

# ==============================================================================
# 1. 页面基本配置与高级 CSS 视觉引擎 (Bento Box + Tabs + TradingAgents 投委会样式)
# ==============================================================================
st.set_page_config(
    page_title="Ultimate Quant & TradingAgents Terminal V12.0",
    page_icon="💹",
    layout="wide",
    initial_sidebar_state="collapsed"
)

PREMIUM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

.stApp {
    background: radial-gradient(circle at 50% 0%, #1e293b 0%, #0f172a 60%, #090d16 100%) !important;
    font-family: 'Inter', -apple-system, sans-serif !important;
    color: #f8fafc !important;
}
.block-container { padding-top: 2rem !important; max-width: 1440px !important; }
header[data-testid="stHeader"] { background: transparent !important; }

.stTabs [data-baseweb="tab-list"] {
    gap: 6px; background-color: rgba(15, 23, 42, 0.6); border-radius: 12px; padding: 8px; border: 1px solid rgba(56, 189, 248, 0.2);
    flex-wrap: wrap;
}
.stTabs [data-baseweb="tab"] {
    color: #94a3b8 !important; font-weight: 600 !important; border-radius: 8px !important; padding: 9px 12px !important; font-size: 12px !important; transition: all 0.3s ease;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #38bdf8 0%, #0284c7 100%) !important; color: #ffffff !important; box-shadow: 0 4px 15px rgba(56, 189, 248, 0.4);
}

[data-testid="column"] > div { height: 100% !important; }
[data-testid="stVerticalBlockBorderWrapper"] {
    background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.85) 100%) !important;
    border: 1px solid rgba(56, 189, 248, 0.3) !important; border-radius: 14px !important;
    box-shadow: 0 8px 24px -4px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.08) !important;
    backdrop-filter: blur(12px) !important; transition: all 0.3s ease !important; padding: 16px 20px !important;
    height: 100% !important; display: flex; flex-direction: column; justify-content: space-between;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border-color: #38bdf8 !important; box-shadow: 0 10px 30px -4px rgba(56, 189, 248, 0.3) !important; transform: translateY(-2px);
}

.stButton > button, .stDownloadButton > button {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%) !important; color: #38bdf8 !important;
    border: 1px solid rgba(56, 189, 248, 0.3) !important; border-radius: 8px !important; font-weight: 600 !important; font-size: 13px !important; transition: all 0.25s ease !important;
}
.stButton > button:hover, .stDownloadButton > button:hover {
    background: rgba(56, 189, 248, 0.15) !important; color: #ffffff !important; border-color: #38bdf8 !important; box-shadow: 0 6px 18px -2px rgba(56, 189, 248, 0.4) !important; transform: translateY(-2px);
}

.agent-badge {
    display: inline-block; padding: 3px 10px; border-radius: 999px; font-size: 11px; font-weight: 700; letter-spacing: 0.4px; margin-bottom: 6px;
}
.debate-card-bull {
    background: linear-gradient(135deg, rgba(6, 78, 59, 0.35) 0%, rgba(15, 23, 42, 0.9) 100%);
    border-left: 4px solid #10b981; border-radius: 10px; padding: 14px 16px; margin-bottom: 10px;
}
.debate-card-bear {
    background: linear-gradient(135deg, rgba(127, 29, 29, 0.35) 0%, rgba(15, 23, 42, 0.9) 100%);
    border-left: 4px solid #ef4444; border-radius: 10px; padding: 14px 16px; margin-bottom: 10px;
}
.debate-card-pm {
    background: linear-gradient(135deg, rgba(30, 58, 138, 0.45) 0%, rgba(15, 23, 42, 0.95) 100%);
    border: 1.5px solid #38bdf8; border-radius: 12px; padding: 18px 20px; margin-top: 10px;
}

label { color: #cbd5e1 !important; font-weight: 500 !important; }
p { color: #e2e8f0 !important; }
h1, h2, h3, h4, h5 { font-family: 'Inter', sans-serif !important; font-weight: 700 !important; color: #ffffff !important; }
h3 { color: #38bdf8 !important; text-shadow: 0 0 15px rgba(56, 189, 248, 0.2); margin-bottom: 15px !important; }
[data-testid="stMetricValue"] { font-family: 'JetBrains Mono', monospace !important; font-weight: 800 !important; font-size: 1.8rem !important; color: #f8fafc !important; }
[data-testid="stMetricLabel"] { font-weight: 600 !important; color: #94a3b8 !important; font-size: 0.85rem !important; }
div[data-baseweb="input"] > div, div[data-baseweb="select"] > div { background-color: #0f172a !important; border: 1px solid rgba(56, 189, 248, 0.3) !important; border-radius: 8px !important; color: #ffffff !important; }
</style>
"""
st.markdown(PREMIUM_CSS, unsafe_allow_html=True)

# ==============================================================================
# 2. 高速数据缓存层 (@st.cache_data 哈希安全序列化 + 跨国 MultiIndex/时区剥离)
# ==============================================================================
def _sanitize_info_dict(raw_info: dict) -> dict:
    """
    🌟 审计修复 I-1：将 yfinance 返回的复杂嵌套 info 字典净化为基础可序列化类型 (str, int, float, bool)，
    彻底防止 st.cache_data 序列化或哈希时抛出 UnhashableType / StreamlitAPIException 或内存泄漏。
    """
    if not isinstance(raw_info, dict):
        return {}
    clean = {}
    for k, v in raw_info.items():
        if isinstance(v, (str, int, float, bool)) or v is None:
            clean[str(k)] = v
    return clean


def _strip_df_tz(df):
    """剥离 DataFrame 索引与列上的时区信息，确保缓存与跨国拼接 100% 稳健"""
    if df is None or getattr(df, "empty", True):
        return pd.DataFrame()
    out = df.copy()
    try:
        if hasattr(out.index, "tz_localize"):
            out.index = out.index.tz_localize(None)
    except Exception:
        pass
    try:
        if hasattr(out.columns, "tz_localize"):
            out.columns = out.columns.tz_localize(None)
    except Exception:
        pass
    return out


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_ticker_bundle(ticker: str):
    """缓存标的公司的核心净化 Info 与三大财务报表 (1小时有效，仅接收基础 str 参数)"""
    clean_sym = str(ticker).strip().upper()
    t = yf.Ticker(clean_sym)
    info = _sanitize_info_dict(t.info or {})
    if 'symbol' not in info and not info.get('regularMarketPrice') and not info.get('currentPrice') and not info.get('previousClose'):
        hist_check = t.history(period="5d")
        if hist_check.empty:
            raise ValueError(f"Data missing for {clean_sym}")
        info['symbol'] = clean_sym
        info['previousClose'] = float(hist_check['Close'].dropna().iloc[-1])

    fallback_price = 0.0
    if not (info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')):
        try:
            h = t.history(period="5d")
            if not h.empty:
                fallback_price = float(h['Close'].dropna().iloc[-1])
        except Exception:
            pass

    bs = _strip_df_tz(t.balance_sheet)
    fin = _strip_df_tz(t.financials)
    cfs = _strip_df_tz(t.cashflow)
    return info, bs, fin, cfs, float(fallback_price)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_live_us_10y_yield() -> float:
    """动态抓取 10 年期美债收益率 (^TNX)，失败时平滑回退至 4.20%"""
    try:
        hist = yf.Ticker("^TNX").history(period="5d")
        if not hist.empty:
            val = float(hist['Close'].dropna().iloc[-1]) / 100.0
            if 0.01 <= val <= 0.12:
                return round(val, 4)
    except Exception:
        pass
    return 0.042


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_beta_aligned_returns(ticker: str, market_sym: str):
    """缓存 3 年月度收益率序列用于 Blume Beta 回归"""
    s_hist = yf.Ticker(str(ticker)).history(period='3y', interval='1mo')
    m_hist = yf.Ticker(str(market_sym)).history(period='3y', interval='1mo')
    if s_hist.empty or m_hist.empty:
        return pd.DataFrame()
    s_ret = s_hist['Close'].pct_change().dropna()
    m_ret = m_hist['Close'].pct_change().dropna()
    s_ret.index = s_ret.index.tz_localize(None)
    m_ret.index = m_ret.index.tz_localize(None)
    aligned = pd.concat([s_ret.rename('Stock'), m_ret.rename('Market')], axis=1).dropna()
    return aligned


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_candlestick_history(ticker: str):
    """缓存 1 年日 K 线数据（自动剥离时区）"""
    return _strip_df_tz(yf.Ticker(str(ticker)).history(period="1y", interval="1d"))


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_peer_info(peer_ticker: str):
    """缓存同业可比公司净化 Info"""
    return _sanitize_info_dict(yf.Ticker(str(peer_ticker)).info or {})


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_portfolio_history(tickers_tuple: tuple):
    """
    🌟 审计修复 I-2：跨国多资产历史收盘价矩阵获取
    强制剥离 MultiIndex 多重列索引，并将美股 (America/New_York) 与马股 (Asia/Kuala_Lumpur) 的时间戳
    统一转换为无时区日历日期 (tz_localize(None))，再使用 .ffill().dropna() 对齐，彻底杜绝 KeyError 与空表崩溃！
    """
    clean_tickers = tuple(str(x).strip().upper() for x in tickers_tuple if str(x).strip())
    if not clean_tickers:
        return pd.DataFrame()
    try:
        raw = yf.download(list(clean_tickers), period="1y", interval="1d", progress=False)
        data = raw['Close'] if (isinstance(raw, dict) or (hasattr(raw, 'columns') and 'Close' in raw.columns)) else raw
        if hasattr(data, "columns") and hasattr(data.columns, "nlevels") and getattr(data.columns, "nlevels", 1) > 1:
            if "Close" in data.columns.get_level_values(0):
                data = data["Close"]
            elif "Close" in data.columns.get_level_values(-1):
                data = data.xs("Close", axis=1, level=-1)
            else:
                data.columns = [str(c[0]) for c in data.columns]
        if hasattr(pd, "Series") and isinstance(data, pd.Series):
            data = data.to_frame(name=clean_tickers[0])
        if hasattr(data, "index") and hasattr(data.index, "tz_localize"):
            try:
                data.index = data.index.tz_localize(None)
            except Exception:
                pass
        return data.ffill().dropna(how="all")
    except Exception:
        # 逐只股票降级安全拼接（100% 剥离时区）
        series_map = {}
        for sym in clean_tickers:
            try:
                h = yf.Ticker(sym).history(period="1y", interval="1d")
                if not h.empty and 'Close' in h:
                    s = h['Close'].dropna()
                    if hasattr(s.index, "tz_localize"):
                        s.index = s.index.tz_localize(None)
                    series_map[sym] = s
            except Exception:
                continue
        if not series_map:
            return pd.DataFrame()
        return pd.DataFrame(series_map).ffill().dropna(how="all")


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_option_expirations(ticker: str):
    """缓存期权到期日列表 (返回纯 tuple[str])"""
    opts = yf.Ticker(str(ticker)).options
    return tuple(str(x) for x in opts) if opts else ()


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_option_chain_df(ticker: str, expiry: str):
    """缓存指定到期日的 Calls 与 Puts 期权链"""
    chain = yf.Ticker(str(ticker)).option_chain(str(expiry))
    return _strip_df_tz(chain.calls), _strip_df_tz(chain.puts)


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_recent_news(ticker: str):
    """缓存标的近期新闻标题 (用于 TradingAgents 情绪与新闻分析师节点)"""
    try:
        raw_news = yf.Ticker(str(ticker)).news or []
        parsed = []
        for item in raw_news[:8]:
            content = item.get("content", {}) if isinstance(item, dict) else {}
            title = item.get("title") or content.get("title") or ""
            publisher = item.get("publisher") or (content.get("provider", {}) or {}).get("displayName", "MarketWire")
            if title:
                parsed.append(f"[{publisher}] {title}")
        return parsed
    except Exception:
        return []


def get_fin_metric(df, keyword, default=0.0):
    """鲁棒财报科目提取：自动寻找该科目最新一个非空 (Non-NaN) 期间的数据"""
    if df is None or df.empty:
        return default
    try:
        matches = df[df.index.str.contains(keyword, case=False, na=False)]
        if not matches.empty:
            valid_vals = matches.iloc[0].dropna()
            if not valid_vals.empty:
                return float(valid_vals.iloc[0])
    except Exception:
        pass
    return default


def get_fin_metric_pair(df, keywords, default_curr=0.0, default_prev=0.0) -> tuple[float, float]:
    """提取财报科目的最新一期 (t) 与上一期 (t-1) 数值，支持字符串或关键词列表，用于 Beneish M-Score 财务造假侦测模型"""
    fallback_prev = default_prev if default_prev != 0.0 else default_curr
    if df is None or getattr(df, "empty", True):
        return float(default_curr), float(fallback_prev)
    kw_list = [keywords] if isinstance(keywords, str) else list(keywords)
    for kw in kw_list:
        try:
            matches = df[df.index.astype(str).str.contains(kw, case=False, na=False)]
            if not matches.empty:
                valid_vals = matches.iloc[0].dropna()
                if len(valid_vals) >= 2:
                    c_val = float(valid_vals.iloc[0])
                    p_val = float(valid_vals.iloc[1])
                    return c_val, (p_val if p_val != 0.0 else c_val)
                elif len(valid_vals) == 1:
                    c_val = float(valid_vals.iloc[0])
                    return c_val, c_val
        except Exception:
            continue
    return float(default_curr), float(fallback_prev)


# ==============================================================================
# 3. 国际化多语言字典
# ==============================================================================
TEXTS = {
    "zh": {
        "title": "🌐 智能量化与多智能体金融终端 (V13.0 量化宗师满血终极版)",
        "subtitle": "融合 GARCH(1,1)动态波动率、桥水风险平价(ERC)、多空配对统计套利、Beneish M-Score造假雷达、动态Delta对冲、宏观黑天鹅压力测试 与 Gemini 2.5 投委会",
        "quick_tag": "🔥 热门快捷测评：",
        "input_label": "输入股票代码 (如 1155.KL, NVDA, AAPL)：",
        
        "param_title": "⚙️ 步骤 2：估值核心参数设定 (可保持默认) 👈 (小白用户建议直接保持默认，无需改动)",
        "param_tip": "💡 **何时建议手动调整？**\n* **永续增长率 (g)**：当您预期该行业未来长期通胀或名义GDP增速显著高于/低于历史常态时可微调。\n* **风险溢价 (ERP)**：当市场处于极端恐慌（调高ERP）或极度狂热（调低ERP）周期时可手动修正。",
        "erp_label": "股市风险溢价要求 (Equity Risk Premium)",
        "g2_label": "长期永续通胀增长率 (Terminal Growth Rate)",
        "esg_caption": "🌿 本系统已自动结合可持续金融 (Sustainable Finance)、动态10年期国债收益率与公司真实有效税率进行折现率修正。",
        
        "macro_title": "[1. 动态宏观与资本成本 (DYNAMIC MACRO & COST OF CAPITAL)]",
        "macro_exp": "💡 **通俗解释 (Plain English)：** Beta 衡量股票相对于大盘的波动率。Rf 是实时十年期国债基准利率。WACC / 折现率是你作为投资者要求的最低及格线回报率。",
        
        "matrix_header": "[2. 三大经典估值模型横向对比矩阵 (DCF + DDM + P/E)]",
        "model_dcf_name": "两阶段线性衰减 DCF 模型",
        "model_ddm_name": "股息分红贴现模型 (DDM)",
        "model_pe_name": "市盈率倍数估值 (P/E Multiples)",
        "badge_recommended": "⭐ 系统主推",
        "badge_reference": "📌 辅助参考",
        "no_data_dcf": "现金流为负或数据不足",
        "no_data_ddm": "该公司不派发股息",
        "no_data_pe": "公司目前处于净亏损",
        "vs_market": "vs 市价",
        "note_dcf": "基于线性衰减自由现金流与 WACC 资本成本折现。",
        "note_ddm": "基于历史股息分红及永续增长率折现。",
        "note_pe": "基于每股收益 (EPS) 乘以行业合理市盈率倍数。",
        
        "price": "当前市场价格",
        "fair_val": "内在公道估值 (衰减后)",
        "fair_val_desc": "💡 **关于【内在公道估值 (衰减后)】的通俗解释**：剥离短期市场狂热与恐慌炒作，根据公司真实赚钱能力算出的保守身价。**“衰减后”**代表模型让高速增长逐年平稳递减，彻底防止科技巨头复利失真。",
        "safe_buy": "20% 安全边际买点",

        "heat_title": "[3. 🌡️ 核心参数敏感性分析矩阵 (DCF SENSITIVITY HEATMAP)]",
        "heat_desc": "💡 **图表说明**：投行通常不给出单一绝对估值。纵轴代表不同的**折现率 (WACC)**，横轴代表**永续增长率 (g)**。矩阵中的数值为对应假设下的内在公道价。<br>👉 <span style='color:#10b981;'>**绿色区域**</span> 代表该参数下当前市价被低估 (具备安全边际)；<span style='color:#ef4444;'>**红色区域**</span> 代表高估；深灰色接近当前市价。",
        
        "lie_title": "[4. 💡 市场情绪测谎仪 (MARKET PSYCHOLOGY / LIE DETECTOR)]",
        "lie_exp": "💡 **通俗解释 (Plain English)：** 测谎仪通过二分法反向推导，看看当前的市场价格到底在幻想这家公司未来每年增长多少。",
        "ai_title": "[5. 🤖 双视角 AI 投资顾问 (DUAL-PERSPECTIVE AI ADVISORY)]",
        "inc_title": "🔸 视角 A：保守派收息策略 (Conservative Income)",
        "cap_title": "🔹 视角 B：进取派资本增值 (Capital Appreciation)",
        "exec_title": "[6. 🎯 最终投资评级与执行摘要 (EXECUTIVE SUMMARY)]",
        "rating_explain": "ℹ️ *学术释疑：‘市场情绪理性’代表投资者没有盲目炒作泡沫，但给出 ‘SELL’ 评级是因为当前市价高于内在公道价（缺乏安全边际）。即：好公司不等于好价格。*",
        
        "plain_title": "[7. 🗣️ 小白通俗翻译器 (PLAIN ENGLISH TRANSLATOR)]",
        "fx_title": "[8. 💱 跨境汇率风险提示 (CROSS-BORDER FX RISK)]",
        "fx_content": "- **提示：** 此乃美元计价资产，请注意美元兑马币 (USD/MYR) 的汇率波动风险。",
        
        "ws_title": "🏛️ [9. 华尔街投行分析师共识与预期差雷达]",
        "ws_mean": "投行平均目标价",
        "ws_range": "目标价区间",
        "ws_rating": "投行综合评级",
        "ws_tag": "投行机构共识",
        "gap_title": "⚡ 华尔街 vs 量化模型：深度预期差雷达 (Expectation Gap Analysis)",
        "gap_line1": "量化内在公允价 (Model Fair Value)",
        "gap_line2": "华尔街平均目标价 (Wall Street Target)",
        "gap_line3": "预期差偏离度 (Divergence Gap)",
        "gap_desc_high": "华尔街目标价比模型估值高出",
        "gap_alert_high": "🚨 **【预期差警示 / 情绪溢价驱动】**：华尔街目标价远高于量化模型底线。当前市价已透支部分未来，长线价值投资者需警惕高估值回撤。",
        "gap_alert_low": "🔥 **【深度价值 / 逆向左侧契机】**：量化模型算出的基本面造血价值高于华尔街卖方预期，属于潜在的“捡烟蒂”布局区。",
        "ws_match": "✅ 模型算出的公道价与华尔街机构预测高度吻合，无重大预期差！",

        "chart_title": "[10. 📈 高级盘面与波动率回归分析]",
        "beta_desc": "📊 **Beta 收益率特征线散点分布图说明：**\n* 每个点代表过往 3 年某个月份的收益率联动。红线斜率即为 Blume 修正后的回归关系（马股对标富时大马综指 `^KLSE`，美股对标标普 500 `^GSPC`）。\n* **$R^2$（拟合优度）补充解析**：点越密集贴近红线，说明该股越受大盘宏观主导（如银行股）；点越分散，说明该股具有极强的个股独立行情（如科技股）。",
        "glossary_title": "[11. 📖 小白通俗金融词典：这些数据代表什么？]",
        
        "g_beta_title": "##### 🎯 Beta (波动敏感度)",
        "g_beta_desc": "衡量这只股票相对于大盘是更活泼还是更稳健。Beta > 1 涨跌比大盘更猛，Beta < 1 走势更抗跌防守。",
        "g_growth_title": "##### 🚀 Growth (预期增长率)",
        "g_growth_desc": "未来公司现金流或盈利预计每年递增的比例。增长越快，股票当前公道身价就越高。",
        "g_wacc_title": "##### 🛡️ WACC / 折现率",
        "g_wacc_desc": "你买入这家公司所要求的最低年化回报门槛。风险越高、借钱越多的公司，要求越高。",
        "g_fv_title": "##### 💎 Fair Value (内在公道价)",
        "g_fv_desc": "剥离市场的短期情绪狂热与恐慌，根据公司真实资产、欠债与赚钱能力算出的厂牌公道价。",
        
        "disclaimer_title": "[12. ⚠️ 重要法律与风险免责声明]",
        "disclaimer_1": "1. **非投资建议**：本系统所呈现的所有估值结果、公道价格、诊断与图表分析，仅供学术研究、个人学习交流与教学参考，不构成任何投资建议、买卖要约或财务建议。",
        "disclaimer_2": "2. **市场风险**：股票市场波动剧烈，历史数据和数学量化模型无法预知未来。公司的实际表现可能受到宏观经济、行业竞争及突发事件的影响。",
        "disclaimer_3": "3. **自主决策**：任何投资决策均应由投资者在独立调查或咨询持牌财务顾问的基础上自行做出。开发者与本系统不对依据本系统数据交易产生的任何盈亏承担法律责任."
    },
    "en": {
        "title": "🌐 Universal Quant & Multi-Agent Terminal (Flagship V12.0)",
        "subtitle": "Integrating Football Field, True 3-Stmt NWC, Tax-Shield PIK LBO, Peer Implied Price, SLSQP+CVaR Frontier, brentq IV Solver, Option PoP%, Half-Kelly & Gemini 2.5 IC",
        "quick_tag": "🔥 Quick Select:",
        "input_label": "Enter Stock Ticker (e.g., 1155.KL, NVDA, AAPL):",
        
        "param_title": "⚙️ Step 2: Macro & Valuation Parameters (Defaults Recommended) 👈 (Keep default unless necessary)",
        "param_tip": "💡 **When to adjust manually?**\n* **Terminal Growth (g)**: Adjust if you expect long-term structural inflation or GDP growth to deviate from historical norms.\n* **Equity Risk Premium (ERP)**: Adjust during extreme market cycles (higher ERP during panics, lower during bubbles).",
        "erp_label": "Equity Risk Premium (ERP)",
        "g2_label": "Terminal Growth Rate (g)",
        "esg_caption": "🌿 Sustainable Finance, live 10Y Treasury yield, and effective corporate tax rate automatically integrated into WACC.",
        
        "macro_title": "[1. DYNAMIC MACRO & COST OF CAPITAL]",
        "macro_exp": "💡 **Plain English Explanation:** Beta measures stock volatility compared to the market. Rf is the live benchmark 10Y government bond yield. WACC / Discount Rate is your hurdle rate / minimum required rate of return.",
        
        "matrix_header": "[2. Multi-Model Valuation Matrix (DCF + DDM + P/E)]",
        "model_dcf_name": "Two-Stage Fading Growth DCF",
        "model_ddm_name": "Dividend Discount Model (DDM)",
        "model_pe_name": "P/E Multiples Valuation",
        "badge_recommended": "⭐ System Recommended",
        "badge_reference": "📌 Reference",
        "no_data_dcf": "Negative or Missing Cash Flows",
        "no_data_ddm": "Company pays no dividend",
        "no_data_pe": "Company in net loss",
        "vs_market": "vs Market",
        "note_dcf": "Based on linear fading FCF and WACC discount rate.",
        "note_ddm": "Based on historical dividends and terminal growth.",
        "note_pe": "Based on EPS multiplied by peer median / benchmark P/E.",
        
        "price": "Current Market Price",
        "fair_val": "Intrinsic Fair Value (Faded)",
        "fair_val_desc": "💡 **Explanation of [Intrinsic Fair Value (Faded)]**: Strips away short-term market hype and panic to reveal true fundamental worth. **'Faded'** means growth rates smoothly decay over time to prevent multi-year compounding errors, making valuation conservative and robust.",
        "safe_buy": "Safe Buy Target (20% MoS)",

        "heat_title": "[3. 🌡️ DCF SENSITIVITY HEATMAP]",
        "heat_desc": "💡 **How to read this?** Institutional models do not rely on a single absolute value. The Y-axis represents different **Discount Rates (WACC)**, and the X-axis represents **Terminal Growth (g)**. <br>👉 <span style='color:#10b981;'>**Green zones**</span> indicate the stock is undervalued at those parameters; <span style='color:#ef4444;'>**Red zones**</span> indicate overvalued; Dark grey represents values close to the current market price.",
        
        "lie_title": "[4. 💡 MARKET PSYCHOLOGY (LIE DETECTOR)]",
        "lie_exp": "💡 **Plain English Explanation:** The lie detector uses reverse-engineering to find out what growth rate investors are currently pricing into the stock.",
        "ai_title": "[5. 🤖 DUAL-PERSPECTIVE AI ADVISORY]",
        "inc_title": "🔸 Perspective A: Conservative Income",
        "cap_title": "🔹 Perspective B: Capital Appreciation",
        "exec_title": "[6. 🎯 FINAL EXECUTIVE SUMMARY & RATING]",
        "rating_explain": "ℹ️ *Academic Note: 'Rational Market Sentiment' means investors are not irrationally hyping the stock, but a 'SELL' rating is triggered strictly because the market price exceeds the intrinsic value (Lack of Margin of Safety). Good company ≠ Good price.*",
        
        "plain_title": "[7. 🗣️ PLAIN ENGLISH TRANSLATOR]",
        "fx_title": "[8. 💱 CROSS-BORDER FX RISK ADVISORY]",
        "fx_content": "- **Note:** USD-denominated asset; monitor USD/MYR exchange rate fluctuations.",
        
        "ws_title": "🏛️ [9. Wall Street Analyst Consensus & Expectation Gap Radar]",
        "ws_mean": "Analyst Average Target Price",
        "ws_range": "Target Price Range",
        "ws_rating": "Consensus Rating",
        "ws_tag": "Institutional Consensus",
        "gap_title": "⚡ Wall Street vs. Quant Model: Expectation Gap Analysis",
        "gap_line1": "Model Fair Value",
        "gap_line2": "Wall Street Target Mean",
        "gap_line3": "Divergence Gap",
        "gap_desc_high": "Wall Street target is higher than model value by",
        "gap_alert_high": "🚨 **[Expectation Gap Warning / Sentiment Premium]**: Wall Street targets far exceed the quant model. Current prices have factored in future growth; long-term value investors should remain cautious.",
        "gap_alert_low": "🔥 **[Deep Value / Contrarian Opportunity]**: Quant model fundamental cash flow value exceeds Wall Street sell-side expectations, presenting a potential deep-value entry.",
        "ws_match": "✅ Your Valuation aligns tightly with Wall Street targets with minimal expectation gap!",

        "chart_title": "[10. Advanced Price Action & Regression Analysis]",
        "beta_desc": "📊 **Beta & Jensen's Alpha Regression Plot Explanation:** Each dot represents past 3-year monthly return correlation. The red line represents the OLS regression with intercept (Jensen's Alpha α) and Raw Beta slope, alongside Blume Adjusted Beta.\n* **$R^2$ Analysis**: Tight clustering indicates market-driven systemic risk; higher dispersion reflects strong independent alpha.",
        "glossary_title": "[11. Beginner's Financial Glossary]",
        
        "g_beta_title": "##### 🎯 Beta (Sensitivity)",
        "g_beta_desc": "Measures stock volatility relative to the market. Beta > 1 means higher aggression, while Beta < 1 indicates defensive characteristics.",
        "g_growth_title": "##### 🚀 Expected Growth Rate",
        "g_growth_desc": "The projected annual growth rate of company cash flows or earnings. Higher growth drives higher fair value.",
        "g_wacc_title": "##### 🛡️ WACC / Discount Rate",
        "g_wacc_desc": "The minimum hurdle rate of return required by investors. Higher risks and debt levels demand a higher WACC.",
        "g_fv_title": "##### 💎 Intrinsic Fair Value",
        "g_fv_desc": "The calculated intrinsic value based on fundamental assets, liabilities, and earning power, stripping away market hype or panic.",
        
        "disclaimer_title": "[12. ⚠️ Important Legal & Risk Disclaimer]",
        "disclaimer_1": "1. **Not Investment Advice**: All valuation results, fair prices, diagnostics, and charts presented herein are for academic research, personal learning, and educational purposes only. They do not constitute investment advice or financial recommendations.",
        "disclaimer_2": "2. **Market Risk**: The stock market is volatile, and historical data or quant models cannot predict the future. Company performance is subject to macroeconomic and unforeseen events.",
        "disclaimer_3": "3. **Independent Decision**: All investment decisions must be made independently by users after thorough research or consultation with licensed advisors. The developer accepts no liability for trading losses."
    }
}

# ==============================================================================
# 4. 核心硬核量化引擎 (V12.0: 审计级修复 + 税盾PIK-LBO + 同业隐含估值 + brentq IV反解 + 凯利/CVaR)
# ==============================================================================
class UltimateHardcoreEngine:
    def __init__(self, ticker):
        self.ticker = ticker.strip().upper()
        try:
            self.info, self.bs, self.fin, self.cfs, fallback_price = fetch_ticker_bundle(self.ticker)
        except Exception:
            st.error(f"⚠️ Yahoo Finance data unavailable for {self.ticker}.")
            st.stop()

        self.name = self.info.get('longName') or self.info.get('shortName') or self.ticker
        self.sector = self.info.get('sector') or 'Unknown'
        self.currency = self.info.get('currency') or ('MYR' if self.ticker.endswith('.KL') else 'USD')
        self.is_malaysia = self.ticker.endswith('.KL')

        self.price = float(
            self.info.get('currentPrice')
            or self.info.get('regularMarketPrice')
            or self.info.get('previousClose')
            or fallback_price
            or 0.0
        )

        self.shares = float(self.info.get('sharesOutstanding') or 1)
        self.cash = float(self.info.get('totalCash') or get_fin_metric(self.bs, 'Cash And Cash Equivalents', 0.0))
        self.debt = float(self.info.get('totalDebt') or get_fin_metric(self.bs, 'Total Debt', 0.0))
        self.revenue = float(self.info.get('totalRevenue') or get_fin_metric(self.fin, 'Total Revenue', 1000000.0))

        gross_profit = float(self.info.get('grossProfits') or get_fin_metric(self.fin, 'Gross Profit', self.revenue * 0.5))
        self.cogs = max(1.0, self.revenue - gross_profit)

        self.ebitda = float(self.info.get('ebitda') or get_fin_metric(self.fin, 'EBITDA', self.revenue * 0.2))
        self.net_income = float(self.info.get('netIncomeToCommon') or get_fin_metric(self.fin, 'Net Income', self.ebitda * 0.5))
        self.hist_da = abs(float(get_fin_metric(self.cfs, 'Depreciation', self.ebitda * 0.2)))

        # 从真实资产负债表与现金流量表反推历史 DSO / DIO / DPO / Capex%
        raw_ar = abs(float(get_fin_metric(self.bs, 'Receivables', 0.0)))
        raw_inv = abs(float(get_fin_metric(self.bs, 'Inventory', 0.0)))
        raw_ap = abs(float(get_fin_metric(self.bs, 'Payables', 0.0)))
        raw_capex = abs(float(get_fin_metric(self.cfs, 'Capital Expenditure', 0.0)))

        self.hist_dso = int(np.clip(round((raw_ar / self.revenue) * 365.0), 5, 180)) if (raw_ar > 0 and self.revenue > 0) else 45
        self.hist_dio = int(np.clip(round((raw_inv / self.cogs) * 365.0), 0, 200)) if (raw_inv > 0 and self.cogs > 0) else 30
        self.hist_dpo = int(np.clip(round((raw_ap / self.cogs) * 365.0), 10, 220)) if (raw_ap > 0 and self.cogs > 0) else 60
        self.hist_capex_pct = float(np.clip(round((raw_capex / self.revenue) * 100.0, 1), 1.0, 35.0)) if (raw_capex > 0 and self.revenue > 0) else 5.0

        raw_fcf = float(self.info.get('freeCashflow') or 0.0)
        if raw_fcf <= 0:
            raw_fcf = float(get_fin_metric(self.cfs, 'Free Cash Flow', 0.0))
        if raw_fcf <= 0:
            raw_fcf = max(self.net_income * 0.6, self.ebitda * 0.15, 1000000.0) if self.net_income > 0 else self.revenue * 0.05
        self.cf = raw_fcf

        self.market_cap = self.price * self.shares
        self.ev = self.market_cap + self.debt - self.cash
        self.scatter_data = None
        self.raw_beta = 1.0
        self.alpha_monthly = 0.0
        self.alpha_annual = 0.0
        self.r_squared = 0.0
        self.hardcore_ufcf_proj = []
        self.hardcore_ebitda_proj = []
        self.val_3stmt_dcf = None
        self.comps_df = pd.DataFrame()
        self.comps_summary = {}

    def get_esg_adjustment(self):
        if self.sector in ['Energy', 'Basic Materials', 'Industrials']:
            return 0.015, "🔴 High ESG Risk (Penalty +1.5%)"
        elif self.sector in ['Technology', 'Healthcare', 'Financial Services']:
            return -0.005, "🟢 Low ESG Risk (Reward -0.5%)"
        return 0.00, "⚪ Neutral ESG Risk (No Adj)"

    def compute_blume_beta(self):
        fallback = 1.0
        try:
            market_sym = '^KLSE' if self.is_malaysia else '^GSPC'
            aligned = fetch_beta_aligned_returns(self.ticker, market_sym)
            if len(aligned) < 12:
                return fallback, 'Insufficient Data'
            self.scatter_data = aligned
            stock_r = aligned.iloc[:, 0].values
            mkt_r = aligned.iloc[:, 1].values
            var = np.var(mkt_r, ddof=1)
            if var == 0:
                return fallback, 'Zero Market Var'
            # 🌟 审计升级 III-4：使用 np.polyfit 求解带截距 OLS 回归，计算真实 Raw Beta 与年化 Jensen's Alpha
            slope, intercept = np.polyfit(mkt_r, stock_r, 1)
            if not np.isfinite(slope):
                return fallback, 'System Default'
            self.raw_beta = float(slope)
            self.alpha_monthly = float(intercept)
            self.alpha_annual = float((1.0 + self.alpha_monthly) ** 12 - 1.0) if self.alpha_monthly > -0.9 else float(self.alpha_monthly * 12.0)
            corr = np.corrcoef(stock_r, mkt_r)[0, 1]
            self.r_squared = float(corr ** 2) if not np.isnan(corr) else 0.0

            clipped_beta = float(np.clip(self.raw_beta, 0.2, 2.5))
            blume_beta = round((0.67 * clipped_beta) + (0.33 * 1.0), 2)
            tag = 'Blume Adjusted' if 0.2 <= self.raw_beta <= 2.5 else 'Blume (Clipped)'
            return blume_beta, tag
        except Exception:
            return fallback, 'System Default'

    def run_valuation(self, erp, terminal_g):
        self.beta, self.beta_type = self.compute_blume_beta()
        self.rf = 0.038 if self.is_malaysia else fetch_live_us_10y_yield()
        self.esg_adj, self.esg_tag = self.get_esg_adjustment()

        self.ke = self.rf + (self.beta * erp) + self.esg_adj

        pretax_inc = float(get_fin_metric(self.fin, 'Pretax Income', 0.0))
        tax_prov = float(get_fin_metric(self.fin, 'Tax Provision', 0.0))
        if pretax_inc > 0 and tax_prov > 0 and 0.08 <= (tax_prov / pretax_inc) <= 0.35:
            self.tax = round(tax_prov / pretax_inc, 4)
            self.tax_tag = f"Effective Tax ({self.tax*100:.1f}%)"
        else:
            self.tax = 0.24 if self.is_malaysia else 0.21
            self.tax_tag = f"Statutory Tax ({self.tax*100:.0f}%)"

        total_cap = self.market_cap + self.debt
        w_e = self.market_cap / total_cap if total_cap > 0 else 1.0
        w_d = self.debt / total_cap if total_cap > 0 else 0.0

        # 🌟 审计修复 I-4：修复缺失 Interest Expense 时债务成本 kd 变成 0% 的 WACC 失真漏洞
        int_exp = abs(float(self.info.get('interestExpense') or get_fin_metric(self.fin, 'Interest Expense', 0.0)))
        kd_floor = self.rf + 0.015  # 无风险利率 + 150bps 信用利差下限兜底
        if self.debt > 0 and int_exp > 0:
            raw_kd = int_exp / self.debt
            if raw_kd < self.rf:
                kd = kd_floor
                self.kd_tag = f"Floor Rf+150bps ({kd*100:.2f}%)"
            else:
                kd = min(raw_kd, 0.12)
                self.kd_tag = f"Implied Kd ({kd*100:.2f}%)"
        else:
            kd = kd_floor
            self.kd_tag = f"Synthetic Rf+150bps ({kd*100:.2f}%)"
        self.kd = kd

        self.wacc = (w_e * self.ke) + (w_d * kd * (1.0 - self.tax))
        self.wacc = max(self.wacc, terminal_g + 0.02)

        self.g1 = min(max(float(self.info.get('earningsGrowth') or 0.08), 0.03), 0.25)
        self.g2 = terminal_g
        self.horizon = 10 if self.sector in ['Technology', 'Communication Services'] else 5

        self.val_dcf = self.calc_specific_dcf(self.wacc, self.g2)

        div = float(self.info.get('dividendRate') or self.info.get('trailingAnnualDividendRate') or 0.0)
        self.val_ddm = None
        if div > 0:
            g_ddm = min(self.g2, self.ke - 0.01)
            self.val_ddm = (div * (1.0 + g_ddm)) / (self.ke - g_ddm) if self.ke > g_ddm else 0.0

        eps = float(self.info.get('trailingEps') or self.info.get('forwardEps') or 0.0)
        if eps <= 0 and self.net_income > 0 and self.shares > 0:
            eps = self.net_income / self.shares
        self.eps = eps

        # 🌟 审计升级 II-2：预计算同业可比矩阵 (Comps)，将同业中位数 P/E 与 EV/EBITDA 反哺回估值体系
        self.comps_df = self.run_comps_analysis()
        peer_med_pe = self.comps_summary.get("peer_median_pe", 0.0)

        self.val_pe = None
        if eps > 0:
            fallback_pe = 24.0 if self.sector in ['Technology', 'Communication Services'] else (11.5 if self.sector == 'Financial Services' else 16.0)
            bench_pe = peer_med_pe if (peer_med_pe and 4.0 <= peer_med_pe <= 60.0) else fallback_pe
            self.bench_pe_used = bench_pe
            self.val_pe = eps * bench_pe
        else:
            self.bench_pe_used = 0.0

        if self.sector in ['Financial Services', 'Real Estate', 'Utilities'] and self.val_ddm and self.val_ddm > 0:
            self.model_name = 'Dividend Discount Model (DDM)'
            self.r = self.ke
            val = self.val_ddm
        elif self.val_dcf and self.val_dcf > 0:
            self.model_name = 'Discounted Cash Flow (DCF)'
            self.r = self.wacc
            val = self.val_dcf
        elif self.val_pe and self.val_pe > 0:
            self.model_name = 'P/E Multiples Valuation'
            self.r = self.wacc
            val = self.val_pe
        else:
            self.model_name = 'Discounted Cash Flow (DCF)'
            self.r = self.wacc
            val = self.val_dcf if self.val_dcf else 0.0

        self.fair_val = val
        self.implied_g = self.find_implied_growth()
        # 预先使用真实历史营运资本参数初始化三表预测，确保全局任意 Tab 均可立即调用
        self.build_hardcore_3_statement(self.hist_dso, self.hist_dio, self.hist_dpo, self.hist_capex_pct / 100.0)
        return self.fair_val, self.implied_g

    def calc_specific_dcf(self, test_wacc, test_g2):
        if self.cf <= 0 or test_wacc <= test_g2:
            return None
        pv1 = 0.0
        curr_cf = self.cf
        growth_rates = np.linspace(self.g1, test_g2, self.horizon)
        for y in range(1, self.horizon + 1):
            curr_cf *= (1.0 + growth_rates[y - 1])
            pv1 += curr_cf / ((1.0 + test_wacc) ** y)
        pv_tv = (curr_cf * (1.0 + test_g2)) / (test_wacc - test_g2) / ((1.0 + test_wacc) ** self.horizon)
        return (pv1 + pv_tv + self.cash - self.debt) / self.shares if self.shares > 0 else 0.0

    def find_implied_growth(self):
        if self.price <= 0 or self.cf <= 0:
            return None
        low, high = -0.50, 2.00
        for _ in range(50):
            mid = (low + high) / 2.0
            pv1, curr_cf = 0.0, self.cf
            growth_rates = np.linspace(mid, self.g2, self.horizon)
            for y in range(1, self.horizon + 1):
                curr_cf *= (1.0 + growth_rates[y - 1])
                pv1 += curr_cf / ((1.0 + self.wacc) ** y)
            pv_tv = (curr_cf * (1.0 + self.g2)) / (self.wacc - self.g2) / ((1.0 + self.wacc) ** self.horizon)
            res = (pv1 + pv_tv + self.cash - self.debt) / self.shares
            if res < self.price:
                low = mid
            else:
                high = mid
        return mid

    def build_hardcore_3_statement(self, dso, dio, dpo, capex_pct):
        """
        🌟 审计修复 I-3：
        Year 0 (Current) 严格锚定公司资产负债表上的真实历史天数 (self.hist_dso, self.hist_dio, self.hist_dpo)，
        Year 1 ~ Year 5 使用用户在滑块上设定的预测假设 (dso, dio, dpo)，从而使 Year 1 的 ΔNWC 真实反映营运资本变动带来的现金流冲击！
        """
        years = ['Year 0 (Current)', 'Year 1', 'Year 2', 'Year 3', 'Year 4', 'Year 5']

        rev_0 = self.revenue
        cogs_0 = self.cogs if self.cogs > 0 else rev_0 * 0.5
        ebitda_margin = self.ebitda / self.revenue if self.revenue > 0 else 0.2
        tax_rate = self.tax

        rev = [rev_0]
        cogs = [cogs_0]
        ebitda = [self.ebitda]
        da = [self.hist_da]
        capex = [rev_0 * (self.hist_capex_pct / 100.0)]

        ar = [(self.hist_dso / 365.0) * rev_0]
        inv = [(self.hist_dio / 365.0) * cogs_0]
        ap = [(self.hist_dpo / 365.0) * cogs_0]
        nwc = [ar[0] + inv[0] - ap[0]]
        dnwc = [0.0]
        ufcf = [self.cf]

        new_capex_schedule = []

        for i in range(1, 6):
            g = self.g1 - (self.g1 - self.g2) * (i / 5.0)
            r = rev[-1] * (1.0 + g)
            c = cogs[-1] * (1.0 + g)
            e = r * ebitda_margin

            rev.append(r)
            cogs.append(c)
            ebitda.append(e)

            cap = r * capex_pct
            capex.append(cap)
            new_capex_schedule.append(cap)

            current_da = self.hist_da * max(0.0, 1.0 - 0.2 * i)
            for j in range(len(new_capex_schedule)):
                current_da += new_capex_schedule[j] * 0.2
            da.append(current_da)

            current_ar = (dso / 365.0) * r
            current_inv = (dio / 365.0) * c
            current_ap = (dpo / 365.0) * c
            current_nwc = current_ar + current_inv - current_ap

            ar.append(current_ar)
            inv.append(current_inv)
            ap.append(current_ap)
            nwc.append(current_nwc)
            dnwc.append(current_nwc - nwc[-2])

            ebit = e - current_da
            nopat = ebit * (1.0 - tax_rate)
            current_ufcf = nopat + current_da - cap - dnwc[-1]
            ufcf.append(current_ufcf)

        self.hardcore_ufcf_proj = ufcf[1:]
        self.hardcore_ebitda_proj = ebitda[1:]

        if self.wacc > self.g2 and self.shares > 0:
            pv_ufcf = sum(cf_val / ((1.0 + self.wacc) ** idx) for idx, cf_val in enumerate(self.hardcore_ufcf_proj, start=1))
            terminal_cf = max(0.0, self.hardcore_ufcf_proj[-1]) * (1.0 + self.g2)
            pv_tv_3stmt = (terminal_cf / (self.wacc - self.g2)) / ((1.0 + self.wacc) ** 5)
            self.val_3stmt_dcf = max(0.0, (pv_ufcf + pv_tv_3stmt + self.cash - self.debt) / self.shares)
        else:
            self.val_3stmt_dcf = 0.0

        df = pd.DataFrame({
            "Revenue": rev,
            "EBITDA": ebitda,
            "(-) D&A (Waterfall)": [-d for d in da],
            "(=) EBIT": [e - d for e, d in zip(ebitda, da)],
            "NOPAT (EBIT x 1-T)": [(e - d) * (1.0 - tax_rate) for e, d in zip(ebitda, da)],
            "(-) Capex": [-c for c in capex],
            "(-) Δ NWC (WC Change)": [-d for d in dnwc],
            "(=) Unlevered FCF": ufcf
        }, index=years).T
        return df

    def run_lbo_model(self, ltv_ratio, interest_rate, exit_multiple, buyout_premium: float = 0.15):
        """
        🌟 审计升级 II-1：
        1. 引入控制权收购溢价 (Acquisition Premium %)：Purchase EV = Current EV * (1 + Premium)
        2. 引入利息税盾 (Interest Tax Shield = Interest * Tax Rate)：税后净利息 = Interest * (1 - Tax)
        3. 引入 PIK (实物支付利息 / 利滚利兜底)：当某年 UFCF 不足以支付税后利息时，未付清差额自动累入期末债务本金！
        """
        purchase_price = self.ev * (1.0 + buyout_premium)
        debt_funding = purchase_price * ltv_ratio
        equity_funding = purchase_price - debt_funding

        debt_schedule = [debt_funding]
        interest_schedule = []
        tax_shield_schedule = []
        pik_schedule = []

        ufcf_list = self.hardcore_ufcf_proj if (self.hardcore_ufcf_proj and len(self.hardcore_ufcf_proj) == 5) else [self.cf * ((1.0 + self.g2) ** i) for i in range(1, 6)]
        for fcf in ufcf_list:
            prev_debt = debt_schedule[-1]
            interest = prev_debt * interest_rate
            tax_shield = interest * self.tax
            after_tax_interest = interest * (1.0 - self.tax)
            levered_fcf = fcf - after_tax_interest

            if levered_fcf >= 0:
                cash_sweep = min(prev_debt, levered_fcf)
                pik_added = 0.0
                ending_debt = max(0.0, prev_debt - cash_sweep)
            else:
                # 现金流不足付息，触发 PIK 利滚利计入本金
                pik_added = abs(levered_fcf)
                ending_debt = prev_debt + pik_added

            debt_schedule.append(ending_debt)
            interest_schedule.append(interest)
            tax_shield_schedule.append(tax_shield)
            pik_schedule.append(pik_added)

        y5_ebitda = self.hardcore_ebitda_proj[-1] if self.hardcore_ebitda_proj else self.ebitda * ((1.0 + self.g2) ** 5)
        exit_ev = y5_ebitda * exit_multiple
        exit_equity = max(0.0, exit_ev - debt_schedule[-1])

        moic = exit_equity / equity_funding if equity_funding > 0 else 0.0
        irr = (moic ** (1.0 / 5.0)) - 1.0 if moic > 0 else -1.0

        return {
            "Entry EV": purchase_price, "Debt": debt_funding, "Equity": equity_funding,
            "Buyout Premium %": buyout_premium * 100.0,
            "Y5 EBITDA": y5_ebitda, "Exit EV": exit_ev, "Exit Debt": debt_schedule[-1],
            "Exit Equity": exit_equity, "MOIC": moic, "IRR": irr,
            "Debt Schedule": debt_schedule,
            "Interest Schedule": interest_schedule,
            "Tax Shield Schedule": tax_shield_schedule,
            "PIK Schedule": pik_schedule,
            "Total Tax Shield": float(sum(tax_shield_schedule))
        }

    def run_comps_analysis(self):
        """
        🌟 审计升级 II-2 & IV-1：
        1. 结果按 ticker 缓存在 st.session_state 中，彻底消除切换 Tab 重复请求；
        2. 自动计算同业中位数 (Peer Median) 与均值 (Peer Mean) 的 P/E 和 EV/EBITDA；
        3. 反推目标公司的【同业 P/E 隐含股价】与【同业 EV/EBITDA 隐含股价】！
        """
        cache_key = f"comps_cache_v12_{self.ticker}"
        if cache_key in st.session_state:
            cached_df, cached_sum = st.session_state[cache_key]
            self.comps_summary = cached_sum
            return cached_df

        peer_map = {
            'NVDA': ['AMD', 'INTC', 'TSM', 'QCOM'],
            'AAPL': ['MSFT', 'GOOGL', 'AMZN', 'META'],
            'TSLA': ['RIVN', 'F', 'GM', 'TM'],
            '1155.KL': ['1023.KL', '1295.KL', '1188.KL', '5819.KL'],
            '1295.KL': ['1155.KL', '1023.KL', '1188.KL', '5819.KL'],
            '1023.KL': ['1155.KL', '1295.KL', '5819.KL'],
            '5347.KL': ['5264.KL', '1155.KL', '1023.KL'],
            '5264.KL': ['5347.KL', '1155.KL', '1023.KL']
        }

        if self.ticker in peer_map:
            peers = list(peer_map[self.ticker])
        elif self.is_malaysia:
            peers = ['1155.KL', '1023.KL', '1295.KL', '5347.KL']
        else:
            peers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN']

        if self.ticker in peers:
            peers.remove(self.ticker)

        mcap_col = f"Market Cap ({self.currency} B)"
        self_pe = float(self.info.get('trailingPE') or self.info.get('forwardPE') or 0.0)
        self_gm = float(self.info.get('grossMargins') or 0.0) * 100.0
        self_ev_ebitda = round(self.ev / self.ebitda, 2) if (self.info.get('ebitda') and self.ebitda > 0) else "N/A (Bank/Fin)"

        comp_data = [{
            "Ticker": f"⭐ {self.ticker}",
            "Name": self.name[:16],
            mcap_col: round(self.market_cap / 1e9, 2),
            "EV/EBITDA": str(self_ev_ebitda),
            "P/E": round(self_pe, 2) if self_pe > 0 else 0.0,
            "Gross Margin %": round(self_gm, 1)
        }]

        peer_pes = []
        peer_evs = []

        def _build_peer_row(p):
            try:
                pi = fetch_peer_info(p)
                if not pi:
                    return None
                pmcap = float(pi.get('marketCap') or 0.0)
                pebitda = float(pi.get('ebitda') or 0.0)
                pe_ratio = float(pi.get('trailingPE') or pi.get('forwardPE') or 0.0)
                gm = float(pi.get('grossMargins') or 0.0) * 100.0
                pdebt = float(pi.get('totalDebt') or 0.0)
                pcash = float(pi.get('totalCash') or 0.0)
                pev = pmcap + pdebt - pcash
                ev_mult = (pev / pebitda) if pebitda > 0 else None
                ev_ebitda_str = f"{ev_mult:.2f}" if ev_mult and ev_mult > 0 else "N/A (Bank/Fin)"
                return {
                    "row": {
                        "Ticker": p,
                        "Name": str(pi.get('shortName') or p)[:16],
                        mcap_col: round(pmcap / 1e9, 2),
                        "EV/EBITDA": ev_ebitda_str,
                        "P/E": round(pe_ratio, 2) if pe_ratio > 0 else 0.0,
                        "Gross Margin %": round(gm, 1)
                    },
                    "pe": pe_ratio if 0 < pe_ratio < 150 else None,
                    "ev_mult": ev_mult if (ev_mult and 0 < ev_mult < 120) else None
                }
            except Exception:
                return None

        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(_build_peer_row, peers))
        for r_item in results:
            if r_item is not None:
                comp_data.append(r_item["row"])
                if r_item["pe"]:
                    peer_pes.append(r_item["pe"])
                if r_item["ev_mult"]:
                    peer_evs.append(r_item["ev_mult"])

        peer_med_pe = float(np.median(peer_pes)) if peer_pes else 0.0
        peer_mean_pe = float(np.mean(peer_pes)) if peer_pes else 0.0
        peer_med_ev = float(np.median(peer_evs)) if peer_evs else 0.0
        peer_mean_ev = float(np.mean(peer_evs)) if peer_evs else 0.0

        eps_val = float(self.info.get('trailingEps') or self.info.get('forwardEps') or (self.net_income / self.shares if self.shares > 0 else 0.0))
        implied_pe_price = (eps_val * peer_med_pe) if (eps_val > 0 and peer_med_pe > 0) else None
        implied_ev_price = None
        if self.ebitda > 0 and peer_med_ev > 0 and self.shares > 0:
            imp_mcap = (self.ebitda * peer_med_ev) - self.debt + self.cash
            if imp_mcap > 0:
                implied_ev_price = imp_mcap / self.shares

        self.comps_summary = {
            "peer_median_pe": peer_med_pe,
            "peer_mean_pe": peer_mean_pe,
            "peer_median_ev_ebitda": peer_med_ev,
            "peer_mean_ev_ebitda": peer_mean_ev,
            "implied_pe_price": float(implied_pe_price or 0.0),
            "implied_price_pe": float(implied_pe_price or 0.0),
            "implied_ev_price": float(implied_ev_price or 0.0),
            "implied_price_ev_ebitda": float(implied_ev_price or 0.0)
        }
        df_out = pd.DataFrame(comp_data)
        st.session_state[cache_key] = (df_out, self.comps_summary)
        return df_out

    def run_monte_carlo(self, sims=2000):
        if self.cf <= 0 or self.shares <= 0:
            return []
        mc_key = f"mc_cache_v12_{self.ticker}_{round(self.wacc, 4)}_{round(self.g2, 4)}_{sims}"
        if mc_key in st.session_state:
            return st.session_state[mc_key]

        rng = np.random.default_rng(42)
        sim_waccs = rng.normal(self.wacc, 0.015, sims)
        sim_gs = rng.normal(self.g2, 0.005, sims)

        valid_mask = sim_waccs > (sim_gs + 0.005)
        w_arr = sim_waccs[valid_mask]
        g_arr = sim_gs[valid_mask]
        if len(w_arr) == 0:
            return []

        t_steps = np.linspace(0.0, 1.0, self.horizon)[None, :]
        g_matrix = self.g1 + (g_arr[:, None] - self.g1) * t_steps
        cf_Trajectory = self.cf * np.cumprod(1.0 + g_matrix, axis=1)
        years_idx = np.arange(1, self.horizon + 1)[None, :]
        discount_factors = (1.0 + w_arr[:, None]) ** years_idx

        pv1_arr = np.sum(cf_Trajectory / discount_factors, axis=1)
        last_cf = cf_Trajectory[:, -1]
        pv_tv_arr = (last_cf * (1.0 + g_arr)) / (w_arr - g_arr) / ((1.0 + w_arr) ** self.horizon)
        vals = (pv1_arr + pv_tv_arr + self.cash - self.debt) / self.shares
        out_list = vals[vals > 0].tolist()
        st.session_state[mc_key] = out_list
        return out_list

    def black_scholes_pricing(self, S, K, T, r, sigma, q=0.0):
        S_arr = np.asarray(S, dtype=float)
        if T <= 0 or sigma <= 0 or K <= 0 or np.any(S_arr <= 0):
            if np.ndim(S) == 0:
                return {
                    "Call": max(0.0, float(S) - K), "Put": max(0.0, K - float(S)),
                    "Delta_C": 0.0, "Delta_P": 0.0, "Gamma": 0.0,
                    "Theta_C": 0.0, "Theta_P": 0.0, "Vega": 0.0, "Rho_C": 0.0, "Rho_P": 0.0
                }
            return {"Call": np.maximum(0.0, S_arr - K), "Put": np.maximum(0.0, K - S_arr)}

        d1 = (np.log(S_arr / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)

        call = S_arr * np.exp(-q * T) * stats.norm.cdf(d1) - K * np.exp(-r * T) * stats.norm.cdf(d2)
        put = K * np.exp(-r * T) * stats.norm.cdf(-d2) - S_arr * np.exp(-q * T) * stats.norm.cdf(-d1)

        if np.ndim(S) > 0:
            return {"Call": call, "Put": put}

        delta_c = np.exp(-q * T) * stats.norm.cdf(d1)
        delta_p = -np.exp(-q * T) * stats.norm.cdf(-d1)
        gamma = (np.exp(-q * T) * stats.norm.pdf(d1)) / (S_arr * sigma * np.sqrt(T))
        vega = S_arr * np.exp(-q * T) * stats.norm.pdf(d1) * np.sqrt(T) / 100.0

        theta_c = (
            -(S_arr * sigma * np.exp(-q * T) * stats.norm.pdf(d1)) / (2 * np.sqrt(T))
            - r * K * np.exp(-r * T) * stats.norm.cdf(d2)
            + q * S_arr * np.exp(-q * T) * stats.norm.cdf(d1)
        ) / 365.0
        theta_p = (
            -(S_arr * sigma * np.exp(-q * T) * stats.norm.pdf(d1)) / (2 * np.sqrt(T))
            + r * K * np.exp(-r * T) * stats.norm.cdf(-d2)
            - q * S_arr * np.exp(-q * T) * stats.norm.cdf(-d1)
        ) / 365.0

        rho_c = K * T * np.exp(-r * T) * stats.norm.cdf(d2) / 100.0
        rho_p = -K * T * np.exp(-r * T) * stats.norm.cdf(-d2) / 100.0

        return {
            "Call": float(call), "Put": float(put),
            "Delta_C": float(delta_c), "Delta_P": float(delta_p),
            "Gamma": float(gamma), "Vega": float(vega),
            "Theta_C": float(theta_c), "Theta_P": float(theta_p),
            "Rho_C": float(rho_c), "Rho_P": float(rho_p)
        }

    def solve_implied_volatility(self, mkt_price: float, S: float, K: float, T: float, r: float, q: float = 0.0, is_call: bool = True, fallback_iv: float = 0.35) -> tuple[float, str]:
        """
        🌟 V13.0 深度审计修复 #3：B-S 隐含波动率反解器 (scipy.optimize.brentq 零崩溃加固版)
        当非交易时段或深度实值/虚值导致 mkt_price <= intrinsic（违背无套利下界）或求根区间同号时，
        全包裹异常捕获并验证 np.isfinite，平滑回退至 fallback_iv，杜绝 ValueError 红字崩溃！
        """
        try:
            mkt_price = float(mkt_price)
            S = float(S)
            K = float(K)
            T = float(T)
            r = float(r)
            q = float(q)
            if mkt_price <= 0 or S <= 0 or K <= 0 or T <= 0:
                return float(fallback_iv), "Fallback"
            intrinsic = max(0.0, S * np.exp(-q * T) - K * np.exp(-r * T)) if is_call else max(0.0, K * np.exp(-r * T) - S * np.exp(-q * T))
            if mkt_price <= intrinsic + 1e-4:
                return float(fallback_iv), "Intrinsic-Bound"

            opt_key = "Call" if is_call else "Put"
            def obj_fn(sigma_try):
                return self.black_scholes_pricing(S, K, T, r, sigma_try, q)[opt_key] - mkt_price

            f_low = float(obj_fn(0.01))
            f_high = float(obj_fn(5.0))
            if np.isfinite(f_low) and np.isfinite(f_high) and (f_low * f_high < 0.0):
                solved_iv = float(sco.brentq(obj_fn, 0.01, 5.0, xtol=1e-4, maxiter=60))
                if 0.01 <= solved_iv <= 5.0 and np.isfinite(solved_iv):
                    return solved_iv, "brentq Solved"
        except Exception:
            pass
        return float(fallback_iv), "Fallback"

    # ==========================================================================
    # 🌟 V13.0 降维打击模块 1：Beneish M-Score 财务造假与盈余操纵侦测雷达
    # ==========================================================================
    def compute_beneish_m_score(self) -> dict:
        """
        计算华尔街做空机构标配的 Beneish M-Score 八因子模型与应计项目异动率 (Accruals Ratio)：
        M = -4.84 + 0.920*DSRI + 0.528*GMI + 0.404*AQI + 0.892*SGI + 0.115*DEPI - 0.172*SGAI + 4.679*TATA - 0.327*LVGI
        判定阈值：M-Score > -1.78 高度疑似存在财务粉饰/盈余操纵（触发 -20 分一票降级惩罚）；
        -2.22 <= M-Score <= -1.78 为灰区观察；M-Score < -2.22 为财务报表稳健。
        """
        rev_t, rev_t1 = get_fin_metric_pair(self.fin, ['Total Revenue', 'Operating Revenue', 'Revenue'], self.revenue)
        ar_t, ar_t1 = get_fin_metric_pair(self.bs, ['Accounts Receivable', 'Receivables', 'Net Receivables'], self.revenue * 0.12)
        cogs_t, cogs_t1 = get_fin_metric_pair(self.fin, ['Cost Of Revenue', 'Cost of Goods Sold', 'Reconciled Cost Of Revenue'], self.cogs)
        ca_t, ca_t1 = get_fin_metric_pair(self.bs, ['Current Assets', 'Total Current Assets'], self.revenue * 0.45)
        ppe_t, ppe_t1 = get_fin_metric_pair(self.bs, ['Net PPE', 'Property Plant Equipment Net'], self.revenue * 0.35)
        ta_t, ta_t1 = get_fin_metric_pair(self.bs, ['Total Assets'], max(self.revenue * 1.2, 1.0))
        dep_t, dep_t1 = get_fin_metric_pair(self.cfs, ['Depreciation And Amortization', 'Depreciation'], max(self.hist_da, self.revenue * 0.04))
        sga_t, sga_t1 = get_fin_metric_pair(self.fin, ['Selling General And Administration', 'Operating Expense'], self.revenue * 0.15)
        tl_t, tl_t1 = get_fin_metric_pair(self.bs, ['Total Liabilities Net Minority Interest', 'Total Liabilities'], self.debt * 1.4)
        ni_t, _ = get_fin_metric_pair(self.fin, ['Net Income', 'Net Income Common Stockholders'], self.net_income)
        ocf_t, _ = get_fin_metric_pair(self.cfs, ['Operating Cash Flow', 'Cash Flow From Continuing Operating Activities'], self.ebitda * 0.80)

        rev_t = max(abs(rev_t), 1.0)
        rev_t1 = max(abs(rev_t1), 1.0)
        ta_t = max(abs(ta_t), 1.0)
        ta_t1 = max(abs(ta_t1), 1.0)

        # 1. DSRI (Days Sales in Receivables Index - 应收账款膨胀指数)
        dsri = ((ar_t / rev_t) / max(ar_t1 / rev_t1, 1e-4)) if ar_t1 > 0 else 1.0
        dsri = float(np.clip(dsri, 0.4, 2.8))

        # 2. GMI (Gross Margin Index - 毛利率恶化指数)
        gm_t1 = max((rev_t1 - cogs_t1) / rev_t1, 0.05)
        gm_t = max((rev_t - cogs_t) / rev_t, 0.05)
        gmi = float(np.clip(gm_t1 / gm_t, 0.5, 2.5))

        # 3. AQI (Asset Quality Index - 资产质量软化指数)
        aq_t = max(1.0 - (ca_t + ppe_t) / ta_t, 0.05)
        aq_t1 = max(1.0 - (ca_t1 + ppe_t1) / ta_t1, 0.05)
        aqi = float(np.clip(aq_t / aq_t1, 0.5, 2.5))

        # 4. SGI (Sales Growth Index - 营收激增指数)
        sgi = float(np.clip(rev_t / rev_t1, 0.5, 3.0))

        # 5. DEPI (Depreciation Index - 折旧率放缓指数)
        dep_rate_t1 = abs(dep_t1) / max(abs(dep_t1) + abs(ppe_t1), 1.0)
        dep_rate_t = abs(dep_t) / max(abs(dep_t) + abs(ppe_t), 1.0)
        depi = float(np.clip(dep_rate_t1 / max(dep_rate_t, 1e-4), 0.5, 2.2))

        # 6. SGAI (SG&A Expenses Index - 销售管理费用率指数)
        sga_rate_t = abs(sga_t) / rev_t
        sga_rate_t1 = abs(sga_t1) / rev_t1
        sgai = float(np.clip(sga_rate_t / max(sga_rate_t1, 1e-4), 0.5, 2.2))

        # 7. LVGI (Leverage Index - 杠杆膨胀指数)
        lev_t = abs(tl_t) / ta_t
        lev_t1 = abs(tl_t1) / ta_t1
        lvgi = float(np.clip(lev_t / max(lev_t1, 1e-4), 0.5, 2.5))

        # 8. TATA (Total Accruals to Total Assets - 总应计项目占总资产比)
        tata = float(np.clip((ni_t - ocf_t) / ta_t, -0.35, 0.35))

        m_score = (
            -4.84
            + 0.920 * dsri
            + 0.528 * gmi
            + 0.404 * aqi
            + 0.892 * sgi
            + 0.115 * depi
            - 0.172 * sgai
            + 4.679 * tata
            - 0.327 * lvgi
        )
        m_score = float(round(m_score, 2))
        accruals_pct = round(tata * 100.0, 2)

        if m_score > -1.78:
            status = "HIGH_RISK"
            penalty = -20.0
            badge_zh = f"🚨 红色警报 (M-Score = {m_score:.2f} > -1.78)：侦测到激进收入确认或应计利润异常，触发基本面 -20 分惩罚！"
            badge_en = f"🚨 RED FLAG (M-Score = {m_score:.2f} > -1.78): High probability of earnings manipulation; -20pt penalty triggered!"
        elif m_score > -2.22:
            status = "GRAY_ZONE"
            penalty = -5.0
            badge_zh = f"⚠️ 灰区观察 (M-Score = {m_score:.2f})：部分营运资本或折旧指标边际弱化，触发 -5 分审慎扣减。"
            badge_en = f"⚠️ WATCHLIST (M-Score = {m_score:.2f}): Moderate accounting quality drift; -5pt prudence adjustment."
        else:
            status = "CLEAN"
            penalty = 0.0
            badge_zh = f"✅ 财务健康 (M-Score = {m_score:.2f} < -2.22)：自由现金流与净利润高度匹配，无盈余操纵迹象。"
            badge_en = f"✅ CLEAN AUDIT (M-Score = {m_score:.2f} < -2.22): Strong cash conversion; low earnings manipulation risk."

        return {
            "m_score": m_score,
            "status": status,
            "penalty": penalty,
            "accruals_pct": accruals_pct,
            "badge_zh": badge_zh,
            "badge_en": badge_en,
            "components": {
                "DSRI": round(dsri, 2),
                "GMI": round(gmi, 2),
                "AQI": round(aqi, 2),
                "SGI": round(sgi, 2),
                "DEPI": round(depi, 2),
                "SGAI": round(sgai, 2),
                "LVGI": round(lvgi, 2),
                "TATA": round(tata, 3)
            }
        }

    # ==========================================================================
    # 🌟 V13.0 降维打击模块 2：动态 Delta 对冲与 Gamma Scalping 模拟器
    # ==========================================================================
    def simulate_dynamic_delta_hedging(self, K: float = None, T_days: int = 30, sigma: float = 0.35, contracts: int = 10, seed: int = 42) -> dict:
        """
        模拟做市商 / 波动率交易台在买入 ATM Straddle (或 Call) 后的 30 天动态 Delta-Neutral 对冲账本：
        每天根据股价位移重新计算 Black-Scholes Delta_t 与 Gamma_t，给出今日需买卖对冲的正股股数，
        并拆分 Gamma Scalping 锁定的已实现波动收益 vs Theta 时间衰减损耗。
        """
        S0 = max(self.price, 1.0)
        K_use = float(K) if (K and K > 0) else S0
        T_days = max(int(T_days), 5)
        sigma_use = max(float(sigma), 0.10)
        mult = max(int(contracts), 1) * 100

        rng = np.random.default_rng(seed)
        dt = 1.0 / 252.0
        # 模拟具有真实波动率聚集特征的 30 天路径
        daily_shocks = rng.normal(0.0, sigma_use * np.sqrt(dt) * 1.12, size=T_days)

        days_list = []
        spot_list = []
        delta_list = []
        gamma_list = []
        hedge_shares_held = []
        daily_trade_shares = []
        cum_gamma_pnl = []
        cum_theta_pnl = []
        cum_net_pnl = []

        curr_s = S0
        prev_shares = 0.0
        running_gamma_pnl = 0.0
        running_theta_pnl = 0.0

        for d in range(T_days):
            rem_T = max((T_days - d) / 365.0, 1.0 / 365.0)
            if d > 0:
                prev_s = curr_s
                curr_s = max(1.0, prev_s * float(np.exp(daily_shocks[d - 1])))
                dS = curr_s - prev_s
                # Long Straddle Gamma Scalping P&L ~= 0.5 * Gamma * (dS)^2 + Theta * dt
                bs_prev = self.black_scholes_pricing(prev_s, K_use, max((T_days - d + 1) / 365.0, 1.0 / 365.0), self.rf, sigma_use)
                straddle_gamma = 2.0 * bs_prev["Gamma"] * mult
                straddle_theta_daily = (bs_prev["Theta_C"] + bs_prev["Theta_P"]) * mult
                running_gamma_pnl += 0.5 * straddle_gamma * (dS ** 2)
                running_theta_pnl += straddle_theta_daily

            bs_now = self.black_scholes_pricing(curr_s, K_use, rem_T, self.rf, sigma_use)
            # Long ATM Straddle Net Delta = (Delta_C + Delta_P) * mult
            net_opt_delta = (bs_now["Delta_C"] + bs_now["Delta_P"]) * mult
            net_opt_gamma = (2.0 * bs_now["Gamma"]) * mult
            target_hedge_shares = -round(net_opt_delta, 0)
            trade_today = target_hedge_shares - prev_shares
            prev_shares = target_hedge_shares

            days_list.append(f"Day {d}")
            spot_list.append(round(curr_s, 2))
            delta_list.append(round(net_opt_delta, 1))
            gamma_list.append(round(net_opt_gamma, 2))
            hedge_shares_held.append(int(target_hedge_shares))
            daily_trade_shares.append(int(trade_today))
            cum_gamma_pnl.append(round(running_gamma_pnl, 2))
            cum_theta_pnl.append(round(running_theta_pnl, 2))
            cum_net_pnl.append(round(running_gamma_pnl + running_theta_pnl, 2))

        # 计算今日（Day 0）的实时对冲指令
        bs_day0 = self.black_scholes_pricing(S0, K_use, T_days / 365.0, self.rf, sigma_use)
        call_delta_shares = round(bs_day0["Delta_C"] * mult, 0)
        straddle_delta_shares = round((bs_day0["Delta_C"] + bs_day0["Delta_P"]) * mult, 0)
        gamma_1pct_shares = round(2.0 * bs_day0["Gamma"] * mult * (S0 * 0.01), 1)

        return {
            "df": pd.DataFrame({
                "Day": days_list,
                "Spot Price": spot_list,
                "Position Net Delta ($\\Delta$)": delta_list,
                "Position Net Gamma ($\\Gamma$)": gamma_list,
                "Target Hedge Shares": hedge_shares_held,
                "Shares to Trade Today": daily_trade_shares,
                "Cum. Gamma Scalping P&L": cum_gamma_pnl,
                "Cum. Theta Decay": cum_theta_pnl,
                "Net Hedged P&L": cum_net_pnl
            }),
            "call_hedge_shares": int(-call_delta_shares),
            "straddle_hedge_shares": int(-straddle_delta_shares),
            "gamma_1pct_rebalance": gamma_1pct_shares,
            "final_gamma_pnl": cum_gamma_pnl[-1],
            "final_theta_pnl": cum_theta_pnl[-1],
            "final_net_pnl": cum_net_pnl[-1],
            "contracts": contracts,
            "strike": round(K_use, 2)
        }

    # ==========================================================================
    # 🌟 V13.0 降维打击模块 3：多资产宏观与地缘政治压力测试引擎 (Macro Stress Test)
    # ==========================================================================
    def run_macro_stress_test(self, portfolio_val: float = 100000.0, port_beta: float = None, base_var_95_pct: float = -2.5) -> pd.DataFrame:
        """
        模拟四大极端宏观与地缘黑天鹅冲击下的资产估值回撤、敏感度传导与压力 VaR 膨胀：
        1. 美联储鹰派加息 (+50 bps 利率冲击 -> WACC 抬升与久期杀估值)
        2. 中东/地缘供应链危机 (原油暴涨 +30% -> 利润率压缩与滞胀冲击)
        3. 全球流动性闪崩 (标普/综指单周暴跌 -15% -> Beta 放大与相关性趋同为 1)
        4. VIX 恐慌指数飙升 (+50% 波动率休克 -> 尾部风险 VaR 倍增)
        """
        beta_use = float(port_beta) if (port_beta is not None and port_beta > 0) else max(self.beta, 0.6)
        duration_factor = max(1.0 / max(self.wacc - 0.025, 0.04), 8.0)

        scenarios = [
            {
                "Scenario_ZH": "🦅 美联储意外加息 +50 bps (利率冲击)",
                "Scenario_EN": "🦅 Fed Hawkish Hike +50 bps (Rate Shock)",
                "Macro_Trigger": "10Y Treasury +0.50%, WACC +50bps",
                "Est_Return_Pct": round(-0.005 * duration_factor * 100.0 * (0.7 + 0.3 * beta_use), 2),
                "Vol_Multiplier": 1.35
            },
            {
                "Scenario_ZH": "🛢️ 原油暴涨 +30% & 供应链中断 (滞胀冲击)",
                "Scenario_EN": "🛢️ Crude Oil +30% & Supply Shock (Stagflation)",
                "Macro_Trigger": "Brent +30%, COGS Margin -250bps",
                "Est_Return_Pct": round(-6.8 * (0.65 + 0.35 * beta_use), 2),
                "Vol_Multiplier": 1.45
            },
            {
                "Scenario_ZH": "📉 地缘黑天鹅引发大盘闪崩 -15% (Beta 杀跌)",
                "Scenario_EN": "📉 Geopolitical Crash -15% (Beta Drawdown)",
                "Macro_Trigger": "Equity Index -15%, Correlation -> 0.95",
                "Est_Return_Pct": round(-15.0 * beta_use, 2),
                "Vol_Multiplier": 1.85
            },
            {
                "Scenario_ZH": "⚡ VIX 恐慌指数暴涨 +50% (流动性挤兑)",
                "Scenario_EN": "⚡ VIX Volatility Spike +50% (Liquidity Freeze)",
                "Macro_Trigger": "VIX +50%, Bid-Ask Spread 3x",
                "Est_Return_Pct": round(-9.5 * beta_use, 2),
                "Vol_Multiplier": 2.10
            }
        ]

        rows = []
        for sc in scenarios:
            ret_pct = float(np.clip(sc["Est_Return_Pct"], -45.0, -1.0))
            pnl_impact = portfolio_val * (ret_pct / 100.0)
            stressed_var_pct = round(abs(base_var_95_pct) * sc["Vol_Multiplier"], 2)
            stressed_val = portfolio_val + pnl_impact
            rows.append({
                "Scenario_ZH": sc["Scenario_ZH"],
                "Scenario_EN": sc["Scenario_EN"],
                "Macro Trigger": sc["Macro_Trigger"],
                "Stressed Drawdown (%)": f"{ret_pct:+.2f}%",
                "Portfolio P&L Impact": f"{self.currency} {pnl_impact:+,.0f}",
                "Post-Shock Equity": f"{self.currency} {stressed_val:,.0f}",
                "Stressed Daily 95% VaR": f"-{stressed_var_pct:.2f}%",
                "Raw_Drawdown_Pct": ret_pct
            })
        return pd.DataFrame(rows)

    # ==========================================================================
    # 🌟 核心融合：TradingAgents 五阶段多智能体投委会与期权作战引擎
    # ==========================================================================
    def compute_technical_signals(self):
        """
        对应 TradingAgents 的 Market Technical Analyst 工具集
        🌟 V13.0 极致优化 A：引入 GARCH(1,1) 动态条件异方差波动率模型替代单一静态 HV30！
        """
        hist = fetch_candlestick_history(self.ticker)
        if hist.empty or len(hist) < 30:
            return {
                "rsi": 50.0, "macd": 0.0, "macd_signal": 0.0, "macd_hist": 0.0,
                "ma20": self.price, "ma50": self.price, "ma200": self.price,
                "atr": self.price * 0.025, "hv30": 0.30, "garch_vol": 0.30,
                "vol_regime": "NORMAL",
                "support": self.price * 0.93, "resistance": self.price * 1.08,
                "mdd_pct": -15.0, "var_95_pct": -2.5, "cvar_95_pct": -3.8,
                "trend": "NEUTRAL"
            }

        close = hist['Close']
        high = hist['High']
        low = hist['Low']

        ma20 = float(close.rolling(20).mean().iloc[-1])
        ma50 = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else ma20
        ma200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else ma50

        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = float((100.0 - (100.0 / (1.0 + rs))).iloc[-1]) if not np.isnan(rs.iloc[-1]) else 50.0

        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        macd_hist = float((macd_line - signal_line).iloc[-1])

        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = float(tr.rolling(14).mean().iloc[-1]) if len(tr) >= 14 else self.price * 0.025

        log_ret = np.log(close / close.shift(1)).dropna()
        hv30 = float(log_ret.tail(30).std() * np.sqrt(252)) if len(log_ret) >= 10 else 0.30

        # 🌟 V13.0 优化点 A：GARCH(1,1) 动态条件异方差波动率预测 (Volatility Clustering)
        # 递推方程：sigma_t^2 = omega + alpha * r_{t-1}^2 + beta * sigma_{t-1}^2
        garch_vol = hv30
        vol_regime = "NORMAL"
        if len(log_ret) >= 20:
            try:
                ret_arr = np.asarray(log_ret.values, dtype=float)
                ret_demean = ret_arr - float(np.mean(ret_arr))
                long_run_var = max(float(np.var(ret_demean)), 1e-6)
                alpha_g = 0.11
                beta_g = 0.85
                omega_g = long_run_var * (1.0 - alpha_g - beta_g)
                cond_var = long_run_var
                for r_val in ret_demean:
                    cond_var = omega_g + alpha_g * (r_val ** 2) + beta_g * cond_var
                # 预测未来 30 个交易日的平均条件方差 (均值回归项 + 指数衰减项)
                persistence = alpha_g + beta_g
                horizon = 21
                avg_fwd_var = long_run_var + ((1.0 - (persistence ** horizon)) / max(horizon * (1.0 - persistence), 1e-4)) * (cond_var - long_run_var)
                garch_vol = float(np.clip(np.sqrt(max(avg_fwd_var, 1e-6) * 252.0), 0.08, 2.50))
                if garch_vol >= hv30 * 1.12:
                    vol_regime = "CLUSTERING_EXPANSION"
                elif garch_vol <= hv30 * 0.90:
                    vol_regime = "MEAN_REVERTING_CALM"
            except Exception:
                garch_vol = hv30

        # 🌟 审计升级 III-3：计算 1 年历史最大回撤 (Max Drawdown, MDD %)、95% 日度 VaR 与 95% CVaR (期望亏空)
        simple_ret = close.pct_change().dropna()
        cum_max = close.cummax()
        drawdown_series = (close - cum_max) / cum_max.replace(0, np.nan)
        mdd_pct = float(drawdown_series.min() * 100.0) if not drawdown_series.empty else -15.0

        if len(simple_ret) >= 20:
            var_95 = float(np.percentile(simple_ret, 5))
            tail_losses = simple_ret[simple_ret <= var_95]
            cvar_95 = float(tail_losses.mean()) if len(tail_losses) > 0 else var_95 * 1.25
            var_95_pct = var_95 * 100.0
            cvar_95_pct = cvar_95 * 100.0
        else:
            var_95_pct = -2.5
            cvar_95_pct = -3.8

        support = float(low.tail(20).min())
        resistance = float(high.tail(20).max())

        if self.price > ma20 > ma50 and macd_hist > 0:
            trend = "STRONG_BULLISH"
        elif self.price > ma50:
            trend = "MODERATE_BULLISH"
        elif self.price < ma20 < ma50 and macd_hist < 0:
            trend = "STRONG_BEARISH"
        else:
            trend = "CHOPPY_SIDEWAYS"

        return {
            "rsi": rsi, "macd": float(macd_line.iloc[-1]), "macd_signal": float(signal_line.iloc[-1]),
            "macd_hist": macd_hist, "ma20": ma20, "ma50": ma50, "ma200": ma200,
            "atr": atr, "hv30": hv30, "garch_vol": garch_vol, "vol_regime": vol_regime,
            "support": support, "resistance": resistance,
            "mdd_pct": mdd_pct, "var_95_pct": var_95_pct, "cvar_95_pct": cvar_95_pct,
            "trend": trend
        }

    def compute_options_intelligence(self, hv30: float, garch_vol: float = None):
        """提取期权链 ATM IV (含 brentq 反解兜底)、GARCH(1,1) 动态波动率对比、Put-Call Skew 与财报日 IV Crush 预警"""
        ref_rv = float(garch_vol) if (garch_vol is not None and garch_vol > 0) else hv30
        default_iv = max(ref_rv * 1.1, 0.25)
        now = datetime.datetime.now()

        days_to_earnings = None
        earnings_date_str = "N/A"
        raw_ts = self.info.get('earningsTimestamp') or self.info.get('earningsTimestampStart')
        if raw_ts:
            try:
                e_dt = datetime.datetime.fromtimestamp(int(raw_ts))
                diff_d = (e_dt - now).days
                if -2 <= diff_d <= 120:
                    days_to_earnings = diff_d
                    earnings_date_str = e_dt.strftime("%Y-%m-%d")
            except Exception:
                pass

        try:
            exp_dates = fetch_option_expirations(self.ticker)
            if not exp_dates:
                T_y = 30 / 365.0
                bs_syn = self.black_scholes_pricing(self.price, self.price, T_y, self.rf, default_iv)
                imp_move_pct = ((bs_syn["Call"] + bs_syn["Put"]) / max(self.price, 1.0)) * 100.0
                return {
                    "has_options": False, "atm_iv": default_iv, "otm_put_iv": default_iv, "otm_call_iv": default_iv,
                    "hv30": hv30, "garch_vol": ref_rv, "iv_hv_ratio": default_iv / max(ref_rv, 0.05), "skew": 0.0,
                    "expiry": "30D (Synthetic)", "T_years": T_y, "days": 30, "strikes": [],
                    "earnings_date": earnings_date_str, "days_to_earnings": days_to_earnings,
                    "earnings_alert": bool(days_to_earnings is not None and 0 <= days_to_earnings <= 30),
                    "implied_move_pct": imp_move_pct
                }

            chosen_exp = exp_dates[0]
            chosen_days = 30
            for exp_str in exp_dates:
                d = (datetime.datetime.strptime(exp_str, "%Y-%m-%d") - now).days
                if 20 <= d <= 60:
                    chosen_exp = exp_str
                    chosen_days = d
                    break
            else:
                chosen_days = max((datetime.datetime.strptime(chosen_exp, "%Y-%m-%d") - now).days, 7)

            T_y = max(chosen_days / 365.0, 7 / 365.0)
            div_r = float(self.info.get('dividendRate') or self.info.get('trailingAnnualDividendRate') or 0.0)
            q_y = (div_r / self.price) if self.price > 0 else 0.0

            calls, puts = fetch_option_chain_df(self.ticker, chosen_exp)

            def _extract_valid_iv(df_sub, is_call_flag, fallback_val):
                if df_sub.empty:
                    return fallback_val
                if 'impliedVolatility' in df_sub.columns:
                    valid_s = df_sub['impliedVolatility'][df_sub['impliedVolatility'] > 0.015]
                    if not valid_s.empty:
                        return float(valid_s.mean())
                solved_list = []
                for _, r_row in df_sub.head(3).iterrows():
                    k_val = float(r_row.get('strike') or self.price)
                    bid_v = float(r_row.get('bid') or 0.0)
                    ask_v = float(r_row.get('ask') or 0.0)
                    last_v = float(r_row.get('lastPrice') or 0.0)
                    mkt_p = ((bid_v + ask_v) / 2.0) if (bid_v > 0 and ask_v > 0) else last_v
                    if mkt_p > 0:
                        s_iv, src = self.solve_implied_volatility(mkt_p, self.price, k_val, T_y, self.rf, q_y, is_call_flag, fallback_val)
                        if src == "brentq Solved":
                            solved_list.append(s_iv)
                return float(np.mean(solved_list)) if solved_list else fallback_val

            atm_iv = default_iv
            if not calls.empty:
                near_c = calls.iloc[(calls['strike'] - self.price).abs().argsort()[:3]]
                atm_iv = _extract_valid_iv(near_c, True, default_iv)

            otm_put_iv = atm_iv
            if not puts.empty:
                otm_p = puts[(puts['strike'] >= self.price * 0.88) & (puts['strike'] <= self.price * 0.96)]
                otm_put_iv = _extract_valid_iv(otm_p, False, atm_iv)

            otm_call_iv = atm_iv
            if not calls.empty:
                otm_c = calls[(calls['strike'] >= self.price * 1.04) & (calls['strike'] <= self.price * 1.12)]
                otm_call_iv = _extract_valid_iv(otm_c, True, atm_iv)

            skew = (otm_put_iv - atm_iv) * 100.0
            # 🌟 V13.0 优化点 A：使用 GARCH(1,1) 动态预期波动率 ref_rv 计算波动率溢价比率
            iv_hv_ratio = atm_iv / max(ref_rv, 0.05)
            avail_strikes = sorted(list(set(calls['strike'].dropna().tolist()))) if not calls.empty and 'strike' in calls.columns else []
            bs_atm = self.black_scholes_pricing(self.price, self.price, T_y, self.rf, atm_iv, q_y)
            imp_move_pct = ((bs_atm["Call"] + bs_atm["Put"]) / max(self.price, 1.0)) * 100.0
            earnings_alert = bool(days_to_earnings is not None and 0 <= days_to_earnings <= chosen_days)

            return {
                "has_options": True,
                "atm_iv": atm_iv,
                "otm_put_iv": otm_put_iv,
                "otm_call_iv": otm_call_iv,
                "hv30": hv30,
                "garch_vol": ref_rv,
                "iv_hv_ratio": iv_hv_ratio,
                "skew": skew,
                "expiry": chosen_exp,
                "T_years": T_y,
                "days": chosen_days,
                "strikes": avail_strikes,
                "earnings_date": earnings_date_str,
                "days_to_earnings": days_to_earnings,
                "earnings_alert": earnings_alert,
                "implied_move_pct": imp_move_pct
            }
        except Exception:
            T_y = 30 / 365.0
            return {
                "has_options": False, "atm_iv": default_iv, "otm_put_iv": default_iv, "otm_call_iv": default_iv,
                "hv30": hv30, "garch_vol": ref_rv, "iv_hv_ratio": 1.1, "skew": 0.0, "expiry": "30D (Synthetic)",
                "T_years": T_y, "days": 30, "strikes": [],
                "earnings_date": earnings_date_str, "days_to_earnings": days_to_earnings,
                "earnings_alert": False, "implied_move_pct": 6.5
            }

    def run_trading_agents_pipeline(self, portfolio_cash: float = 100000.0, current_shares: int = 0, lang_key: str = "zh"):
        """
        复刻并升级 TradingAgents V13.0 全链路状态机：
        Stage 1 (4 Analysts + GARCH(1,1) + Beneish M-Score Forensics)
        -> Stage 2 (Bull vs Bear Debate & Research Manager)
        -> Stage 3 (Equity + Options + Market-Neutral Long-Short Pairs Trading + Half-Kelly Sizing)
        -> Stage 4 (3-Way Risk Debate + Macro Stress Test)
        -> Stage 5 (Portfolio Manager 5-Tier Verdict)
        """
        tech = self.compute_technical_signals()
        opt_info = self.compute_options_intelligence(tech["hv30"], tech.get("garch_vol"))
        beneish = self.compute_beneish_m_score()
        news_list = fetch_recent_news(self.ticker)

        avail_strikes = opt_info.get("strikes") or []
        def snap_k(target_val: float) -> float:
            if avail_strikes:
                return float(min(avail_strikes, key=lambda x: abs(x - target_val)))
            return round(target_val, 2)

        mos_pct = ((self.fair_val - self.price) / self.price * 100.0) if self.price > 0 else 0.0
        implied_g_pct = (self.implied_g * 100.0) if self.implied_g is not None else 8.0
        target_mean = float(self.info.get('targetMeanPrice') or self.fair_val)
        ws_upside = ((target_mean - self.price) / self.price * 100.0) if self.price > 0 else 0.0
        div_rate = float(self.info.get('dividendRate') or self.info.get('trailingAnnualDividendRate') or 0.0)
        div_yield = (div_rate / self.price * 100.0) if self.price > 0 else 0.0

        pos_words = ('beat', 'surge', 'upgrade', 'record', 'growth', 'bull', 'soar', 'outperform', 'buy', 'profit', 'strong', 'gain', 'rally')
        neg_words = ('miss', 'downgrade', 'lawsuit', 'probe', 'drop', 'cut', 'risk', 'warn', 'bear', 'fall', 'slump', 'loss', 'weak', 'crash')
        news_lex_score = 0.0
        for hl in news_list:
            hl_low = hl.lower()
            news_lex_score += sum(2.5 for w in pos_words if w in hl_low)
            news_lex_score -= sum(2.5 for w in neg_words if w in hl_low)
        news_lex_score = float(np.clip(news_lex_score, -10.0, 10.0))

        # 🌟 V13.0 降维打击模块 1：将 Beneish M-Score 财务侦测惩罚因子并入基本面得分（若 M-Score > -1.78 直接扣减 20 分！）
        val_score = float(np.clip(mos_pct * 1.2 + beneish["penalty"], -55, 45))
        tech_score = (20 if tech["trend"] == "STRONG_BULLISH" else (10 if tech["trend"] == "MODERATE_BULLISH" else (-20 if tech["trend"] == "STRONG_BEARISH" else 0)))
        if tech["rsi"] < 32:
            tech_score += 12
        elif tech["rsi"] > 72:
            tech_score -= 12

        sent_score = float(np.clip(ws_upside * 0.45 + news_lex_score, -25, 25))
        total_score = val_score + tech_score + sent_score

        if total_score >= 28:
            final_rating = "Buy"
        elif total_score >= 10:
            final_rating = "Overweight"
        elif total_score >= -10:
            final_rating = "Hold"
        elif total_score >= -28:
            final_rating = "Underweight"
        else:
            final_rating = "Sell"

        # 🌟 V13.0 极致优化 C：联动 Tab 4 同行可比矩阵，生成【多空配对交易 (Market-Neutral Long-Short Pairs Trading)】指令
        best_peer_tk, best_peer_ev, best_peer_roe = ("AMD" if not self.is_malaysia else "1155.KL"), 18.5, 48.0
        worst_peer_tk, worst_peer_ev, worst_peer_roe = ("INTC" if not self.is_malaysia else "1023.KL"), 28.0, 32.0
        try:
            comps_df = self.run_comps_analysis()
            only_peers = comps_df[~comps_df["Ticker"].astype(str).str.contains("⭐", na=False)].copy()
            if not only_peers.empty and "P/E" in only_peers.columns and "Gross Margin %" in only_peers.columns:
                pe_num = pd.to_numeric(only_peers["P/E"], errors="coerce").fillna(20.0)
                gm_num = pd.to_numeric(only_peers["Gross Margin %"], errors="coerce").fillna(25.0)
                only_peers["Score_Rank"] = pe_num - gm_num * 0.35
                best_peer_row = only_peers.sort_values("Score_Rank", ascending=True).iloc[0]
                worst_peer_row = only_peers.sort_values("Score_Rank", ascending=False).iloc[-1]
                best_peer_tk = str(best_peer_row["Ticker"]).strip()
                best_peer_ev = float(best_peer_row.get("P/E") or 15.0)
                best_peer_roe = float(best_peer_row.get("Gross Margin %") or 30.0)
                worst_peer_tk = str(worst_peer_row["Ticker"]).strip()
                worst_peer_ev = float(worst_peer_row.get("P/E") or 28.0)
                worst_peer_roe = float(worst_peer_row.get("Gross Margin %") or 12.0)
        except Exception:
            pass

        target_ev_ebitda = self.ev / max(self.ebitda, 1.0)
        target_roe = float(self.info.get('returnOnEquity') or 0.15) * 100.0
        long_leg_notional = round(portfolio_cash * 0.50, 0)
        short_leg_notional = round(long_leg_notional * np.clip(self.beta, 0.75, 1.35), 0)

        if final_rating in ("Sell", "Underweight") or mos_pct < 0:
            pair_long_tk = best_peer_tk
            pair_short_tk = self.ticker
            pair_spread_desc = (
                f"**LONG (做多低估同行) `{pair_long_tk}`** (`EV/EBITDA {best_peer_ev:.1f}x`, `ROE {best_peer_roe:.1f}%`) "
                f"➕ **SHORT (做空高估标的) `{pair_short_tk}`** (`EV/EBITDA {target_ev_ebitda:.1f}x`, `MoS {mos_pct:+.1f}%`)"
            )
            pair_rationale = (
                f"当前标的 `{self.ticker}` 相对内在价值溢价（安全边际 `{mos_pct:+.1f}%`），单边做空面临大盘逼空风险。"
                f"通过构建 **Beta 中性统计套利配对 (`Long {pair_long_tk} / Short {pair_short_tk}`)**，剥离行业与大盘系统性波动 ($\\beta_{{net}} \\approx 0$)，纯粹捕获同行估值倍数收敛 Alpha！"
            ) if lang_key == "zh" else (
                f"`{self.ticker}` trades above intrinsic value (MoS `{mos_pct:+.1f}%`). A Beta-neutral pair (**Long `{pair_long_tk}` / Short `{pair_short_tk}`**) "
                f"hedges out market beta ($\\beta_{{net}} \\approx 0$) and isolates relative-value mean reversion Alpha."
            )
        else:
            pair_long_tk = self.ticker
            pair_short_tk = worst_peer_tk
            pair_spread_desc = (
                f"**LONG (做多折价标的) `{pair_long_tk}`** (`MoS {mos_pct:+.1f}%`, `ROE {target_roe:.1f}%`) "
                f"➕ **SHORT (做空弱势同行对冲) `{pair_short_tk}`** (`EV/EBITDA {worst_peer_ev:.1f}x`, `ROE {worst_peer_roe:.1f}%`)"
            )
            pair_rationale = (
                f"当前标的 `{self.ticker}` 具备显著估值优势（安全边际 `{mos_pct:+.1f}%`）。若担心宏观黑天鹅拖累行业板块，"
                f"可配对 **做多 `{pair_long_tk}` + 做空高估值弱质同行 `{pair_short_tk}`**，锁定行业内基本面强弱分化收益（Relative-Value Alpha）。"
            ) if lang_key == "zh" else (
                f"`{self.ticker}` offers attractive margin of safety (`{mos_pct:+.1f}%`). Pairing **Long `{pair_long_tk}` against Short `{pair_short_tk}`** "
                f"immunizes sector drawdown risk while capturing fundamental outperformance Alpha."
            )

        pair_info = {
            "long_tk": pair_long_tk,
            "short_tk": pair_short_tk,
            "long_notional": long_leg_notional,
            "short_notional": short_leg_notional,
            "spread_desc": pair_spread_desc,
            "rationale": pair_rationale
        }

        S = self.price
        atr = tech["atr"]
        iv = opt_info["atm_iv"]
        put_iv = opt_info.get("otm_put_iv", iv)
        call_iv = opt_info.get("otm_call_iv", iv)
        T_y = opt_info["T_years"]
        q_y = div_yield / 100.0
        garch_v = tech.get("garch_vol", tech["hv30"])

        # 预先对齐所有常用行权价，确保文字指令与画图引擎 100% 同步
        k_atm = snap_k(S)
        k_95_put = snap_k(S * 0.95)
        k_98_put = snap_k(S * 0.98)
        k_otm_put = snap_k(S * 0.92)
        k_far_put = snap_k(S * 0.85)
        k_otm_call = snap_k(S * 1.05)
        k_108_call = snap_k(S * 1.08)
        k_far_call = snap_k(S * 1.12)

        if k_108_call <= k_atm:
            k_108_call = round(k_atm * 1.06, 2)
        if k_otm_call <= k_atm:
            k_otm_call = round(k_atm * 1.05, 2)
        if k_far_call <= k_108_call:
            k_far_call = round(k_108_call * 1.05, 2)
        if k_otm_put >= k_98_put:
            k_otm_put = round(k_98_put * 0.92, 2)
        if k_far_put >= k_otm_put:
            k_far_put = round(k_otm_put * 0.92, 2)

        opt_legs_meta = {
            "k_atm": k_atm, "k_95_put": k_95_put, "k_98_put": k_98_put,
            "k_otm_put": k_otm_put, "k_far_put": k_far_put,
            "k_otm_call": k_otm_call, "k_108_call": k_108_call, "k_far_call": k_far_call,
            "atm_iv": iv, "put_iv": put_iv, "call_iv": call_iv, "q_yield": q_y
        }

        if final_rating in ("Buy", "Overweight"):
            trader_action = "BUY"
            entry_price = round(S, 2)
            stop_loss = round(max(tech["support"] * 0.98, S - 2.0 * atr), 2)
            take_profit = round(max(self.fair_val, S + 3.0 * atr), 2)

            if opt_info["iv_hv_ratio"] >= 1.15 and not opt_info.get("earnings_alert"):
                bs_put = self.black_scholes_pricing(S, k_95_put, T_y, self.rf, put_iv, q_y)
                prem = bs_put["Put"]
                breakeven = round(k_95_put - prem, 2)
                opt_strat_key = "cash_secured_put"
                opt_strategy_name = "现金担保卖出看跌期权 (Cash-Secured Put - 折价接货+收租)" if lang_key == "zh" else "Cash-Secured Short Put (Discount Entry + Yield)"
                opt_action_detail = (
                    f"**SELL 1x {opt_info['expiry']} Put @ Strike {self.currency} {k_95_put:.2f}** | "
                    f"收取权利金 (Credit): **{self.currency} {prem:.2f}/股** ({self.currency} {prem*100:.0f}/张) | "
                    f"实际盈亏平衡接货价: **{self.currency} {breakeven:.2f}** (比现价再折让 {((S-breakeven)/S)*100:.1f}%) | "
                    f"Delta: `{bs_put['Delta_P']:.2f}`, Theta: `+{abs(bs_put['Theta_P']):.3f}/天`"
                )
                opt_rationale = (
                    f"当前期权隐含波动率 (IV={iv*100:.1f}%) 高于 GARCH(1,1) 动态预测波动率 ({garch_v*100:.1f}%)，且无近期财报跳空地雷。"
                    f"通过**卖出 {k_95_put:.2f} 虚值 Put (Skew IV={put_iv*100:.1f}%)** 收取丰厚权利金；若回调则以 {breakeven:.2f} 折价接盘正股。"
                ) if lang_key == "zh" else (
                    f"Implied Volatility (IV={iv*100:.1f}%) trades at a premium to GARCH(1,1) Forecast Vol ({garch_v*100:.1f}%). "
                    f"Selling an OTM Cash-Secured Put @ {k_95_put:.2f} harvests rich theta while setting a limit entry at {breakeven:.2f}."
                )
            else:
                bs_l = self.black_scholes_pricing(S, k_atm, T_y, self.rf, iv, q_y)
                bs_s = self.black_scholes_pricing(S, k_108_call, T_y, self.rf, call_iv, q_y)
                net_debit = max(0.05, bs_l["Call"] - bs_s["Call"])
                max_gain = max(0.05, (k_108_call - k_atm) - net_debit)
                breakeven = round(k_atm + net_debit, 2)
                opt_strat_key = "bull_call_spread"
                opt_strategy_name = "牛市看涨价差 (Bull Call Spread - 抗IV坍塌杠杆做多)" if lang_key == "zh" else "Bull Call Vertical Spread (IV-Crush Resistant Upside)"
                opt_action_detail = (
                    f"**BUY 1x {opt_info['expiry']} Call @ {k_atm:.2f} + SELL 1x Call @ {k_108_call:.2f}** | "
                    f"净权利金成本 (Net Debit): **{self.currency} {net_debit:.2f}/股** | "
                    f"最大潜在收益: **{self.currency} {max_gain:.2f}/股** (赔率 {max_gain/net_debit:.1f}x) | "
                    f"到期盈亏平衡点: **{self.currency} {breakeven:.2f}**"
                )
                opt_rationale = (
                    f"估值具备安全边际。采用 **Bull Call Spread ({k_atm:.2f}/{k_108_call:.2f})** 用卖出高行权价 Call 补贴买 Call 成本，"
                    f"彻底免疫财报后 IV Crush（波动率坍塌）与 Theta 时间损耗，以锁定风险方式博取上涨。"
                ) if lang_key == "zh" else (
                    f"Attractive valuation. A Bull Call Spread ({k_atm:.2f}/{k_108_call:.2f}) offsets Theta decay and IV Crush risk, "
                    f"lowering breakeven to {breakeven:.2f} with a {max_gain/net_debit:.1f}x reward-to-risk ratio."
                )

        elif final_rating == "Hold":
            trader_action = "HOLD"
            entry_price = round(tech["support"], 2)
            stop_loss = round(tech["support"] * 0.95, 2)
            take_profit = round(tech["resistance"], 2)

            if current_shares >= 100:
                bs_cc = self.black_scholes_pricing(S, k_otm_call, T_y, self.rf, call_iv, q_y)
                prem = bs_cc["Call"]
                opt_strat_key = "covered_call"
                opt_strategy_name = "备兑看涨期权 (Covered Call - 持股收租增强收益)" if lang_key == "zh" else "Covered Call Overwrite (Yield Enhancement)"
                opt_action_detail = (
                    f"**针对已持有的 {current_shares} 股正股，SELL {current_shares // 100}x {opt_info['expiry']} Call @ {k_otm_call:.2f}** | "
                    f"立即落袋权利金: **{self.currency} {prem:.2f}/股** (年化增厚收益约 {(prem/S)*(365/max(opt_info['days'],1))*100:.1f}%)"
                )
                opt_rationale = (
                    f"正股处于估值平衡与震荡整理区，向上暴涨动能有限。通过卖出 {k_otm_call:.2f} 虚值 Call 持续收割 Theta 时间价值，降低持仓成本。"
                ) if lang_key == "zh" else (
                    f"Stock is fairly valued in a consolidation range. Selling OTM Covered Calls @ {k_otm_call:.2f} monetizes sideways action via Theta decay."
                )
            else:
                opt_strat_key = "iron_condor"
                opt_strategy_name = "铁鹰震荡收割策略 (Iron Condor - 赚取时间价值)" if lang_key == "zh" else "Iron Condor (Range-Bound Theta Harvester)"
                opt_action_detail = (
                    f"**构建 {opt_info['expiry']} 盈利走廊 [{self.currency} {k_otm_put:.2f} ~ {self.currency} {k_108_call:.2f}]** | "
                    f"Sell Put @ {k_otm_put:.2f} (Buy {k_far_put:.2f} Put) + Sell Call @ {k_108_call:.2f} (Buy {k_far_call:.2f} Call)"
                )
                opt_rationale = (
                    f"多空双方力量均衡 (RSI={tech['rsi']:.1f})，现价与模型公允价偏离度仅 {mos_pct:+.1f}%。适合用 **Iron Condor** 在上下支撑阻力位之间收割时间价值。"
                ) if lang_key == "zh" else (
                    f"Balanced bull/bear forces (RSI={tech['rsi']:.1f}) and minimal valuation gap ({mos_pct:+.1f}%). Iron Condor harvests time decay within [{k_otm_put:.2f}, {k_108_call:.2f}]."
                )

        else:
            trader_action = "SELL"
            entry_price = round(self.fair_val * 0.85, 2)
            stop_loss = round(S * 1.05, 2)
            take_profit = round(self.fair_val, 2)

            bs_p = self.black_scholes_pricing(S, k_otm_put, T_y, self.rf, put_iv, q_y)
            bs_c = self.black_scholes_pricing(S, k_otm_call, T_y, self.rf, call_iv, q_y)
            net_collar = bs_c["Call"] - bs_p["Put"]

            if current_shares >= 100:
                opt_strat_key = "collar"
                opt_strategy_name = "零成本领型对冲策略 (Zero-Cost Collar - 锁死下行风险)" if lang_key == "zh" else "Zero-Cost Collar Hedge (Downside Floor)"
                opt_action_detail = (
                    f"**BUY {current_shares // 100}x {opt_info['expiry']} Put @ {k_otm_put:.2f} + SELL {current_shares // 100}x Call @ {k_otm_call:.2f}** | "
                    f"净权利金收支: **{self.currency} {net_collar:+.2f}/股** | 最大回撤严格封死在 **{((k_otm_put-S)/S)*100:.1f}%** 以内"
                )
                opt_rationale = (
                    f"当前股价高于量化内在公允价 ({self.fair_val:.2f})，市场隐含增长率高达 {implied_g_pct:.1f}%。若不便直接清仓正股，"
                    f"使用 **Collar 领型策略**用卖 Call 的钱补贴买入 Put 保险，防范估值回归杀跌。"
                ) if lang_key == "zh" else (
                    f"Price exceeds intrinsic value ({self.fair_val:.2f}) with {implied_g_pct:.1f}% implied growth. A Collar finances protective puts by selling upside calls."
                )
            else:
                opt_strat_key = "bear_put_spread"
                opt_strategy_name = "熊市看跌期权价差 (Bear Put Spread - 锁定风险做空均值回归)" if lang_key == "zh" else "Bear Put Vertical Spread (Defined-Risk Mean Reversion)"
                opt_action_detail = (
                    f"**BUY 1x {opt_info['expiry']} Put @ {k_98_put:.2f} + SELL 1x Put @ {k_otm_put:.2f}** | "
                    f"单张合约最大风险严格锁定，博取高估值向公允价值 ({self.currency} {self.fair_val:.2f}) 均值回归"
                )
                opt_rationale = (
                    f"基本面安全边际不足 ({mos_pct:+.1f}%)，且下方跌破 {tech['ma20']:.2f} 均线时易引发多杀多。通过 **Bear Put Spread** 低成本做空估值回归。"
                ) if lang_key == "zh" else (
                    f"Negative margin of safety ({mos_pct:+.1f}%). Bear Put Spread provides defined-risk exposure to mean reversion toward {self.fair_val:.2f}."
                )

        # 🌟 审计升级 III-3：使用半凯利公式 (Half-Kelly Formula: f* = (b*p - q)/b) 动态计算最优仓位配比
        kelly_win_prob = float(np.clip(0.50 + (total_score / 180.0), 0.25, 0.78))
        upside_dist = abs(take_profit - entry_price)
        downside_dist = max(abs(entry_price - stop_loss), entry_price * 0.03, 1e-4)
        kelly_odds = float(np.clip(upside_dist / downside_dist, 0.5, 5.0))
        raw_kelly = (kelly_odds * kelly_win_prob - (1.0 - kelly_win_prob)) / kelly_odds
        kelly_full_pct = float(np.clip(raw_kelly * 100.0, 0.0, 50.0))
        kelly_half_pct = round(kelly_full_pct * 0.5, 1)

        if final_rating in ("Buy", "Overweight"):
            alloc_pct = float(np.clip(kelly_half_pct, 8.0, 28.0))
        elif final_rating == "Hold":
            alloc_pct = float(np.clip(kelly_half_pct, 5.0, 12.0))
        else:
            alloc_pct = 0.0

        return {
            "tech": tech,
            "opt_info": opt_info,
            "opt_legs_meta": opt_legs_meta,
            "beneish": beneish,
            "pair_info": pair_info,
            "news": news_list,
            "mos_pct": mos_pct,
            "implied_g_pct": implied_g_pct,
            "ws_upside": ws_upside,
            "target_mean": target_mean,
            "div_yield": div_yield,
            "total_score": total_score,
            "final_rating": final_rating,
            "trader_action": trader_action,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "alloc_pct": alloc_pct,
            "kelly_win_prob": kelly_win_prob * 100.0,
            "win_prob_p": kelly_win_prob,
            "kelly_odds": kelly_odds,
            "odds_b": kelly_odds,
            "kelly_full_pct": round(kelly_full_pct, 1),
            "full_kelly_pct": round(kelly_full_pct, 1),
            "kelly_half_pct": kelly_half_pct,
            "half_kelly_pct": kelly_half_pct,
            "opt_strat_key": opt_strat_key,
            "opt_strategy_name": opt_strategy_name,
            "opt_action_detail": opt_action_detail,
            "opt_rationale": opt_rationale
        }


# ==============================================================================
# 5. TradingAgents 持久化记忆账本与 T+N 交割复盘系统 (Memory Log & Settlement)
# ==============================================================================
MEMORY_FILE = Path.home() / ".tradingagents" / "quant_terminal_memory.json"


def load_memory_ledger() -> list[dict]:
    if not MEMORY_FILE.exists():
        return []
    try:
        return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_decision_to_ledger(engine, pipeline_res: dict):
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    entries = load_memory_ledger()
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    entries = [e for e in entries if not (e.get("ticker") == engine.ticker and e.get("date") == today_str)]
    entries.insert(0, {
        "date": today_str,
        "ticker": engine.ticker,
        "currency": engine.currency,
        "recorded_price": round(engine.price, 2),
        "fair_value": round(engine.fair_val, 2),
        "rating": pipeline_res["final_rating"],
        "trader_action": pipeline_res["trader_action"],
        "option_strategy": pipeline_res["opt_strategy_name"],
        "stop_loss": pipeline_res["stop_loss"],
        "take_profit": pipeline_res["take_profit"]
    })
    MEMORY_FILE.write_text(json.dumps(entries[:50], ensure_ascii=False, indent=2), encoding="utf-8")


# ==============================================================================
# 6. 图表生成 (热力图 + 估值足球场图 + K线 + 含Alpha的Beta回归 + 含PoP%与盈亏平衡点的双曲线期权图)
# ==============================================================================
def draw_sensitivity_heatmap(engine):
    if engine.cf <= 0:
        return None, None
    cache_k = f"heat_cache_v12_{engine.ticker}_{round(engine.wacc, 4)}_{round(engine.g2, 4)}"
    if cache_k in st.session_state:
        return st.session_state[cache_k]

    w_steps = np.array([-0.02, -0.01, 0.0, 0.01, 0.02])
    g_steps = np.array([-0.01, -0.005, 0.0, 0.005, 0.01])
    wacc_vals = engine.wacc + w_steps
    g2_vals = engine.g2 + g_steps
    z_vals, text_labels, hover_text = [], [], []

    for w in wacc_vals:
        row, label_row, text_row = [], [], []
        for g in g2_vals:
            val = engine.calc_specific_dcf(w, g)
            if val and val > 0:
                row.append(val)
                label_row.append(f"{val:.2f}")
                text_row.append(
                    f"WACC: {w*100:.1f}%<br>Tg: {g*100:.1f}%<br>"
                    f"Fair Value: {engine.currency} {val:.2f}<br>"
                    f"vs Price: {((val - engine.price) / engine.price) * 100:+.1f}%"
                )
            else:
                row.append(np.nan)
                label_row.append("N/A")
                text_row.append("Invalid (WACC ≤ g)")
        z_vals.append(row)
        text_labels.append(label_row)
        hover_text.append(text_row)

    valid_z = [v for row in z_vals for v in row if pd.notna(v)]
    if valid_z:
        max_val, min_val = max(valid_z), min(valid_z)
        max_diff = max(abs(max_val - engine.price), abs(min_val - engine.price)) or 1.0
        c_min, c_max = engine.price - max_diff, engine.price + max_diff
        green_cnt = sum(1 for v in valid_z if v >= engine.price)
        heat_summary = {
            'best': max_val,
            'worst': min_val,
            'green_count': green_cnt,
            'total': len(valid_z),
            'win_rate': green_cnt / len(valid_z)
        }
    else:
        c_min, c_max, heat_summary = 0, 1, None

    fig = go.Figure(data=go.Heatmap(
        z=z_vals,
        x=[f"{g*100:.1f}%" for g in g2_vals],
        y=[f"{w*100:.1f}%" for w in wacc_vals],
        text=text_labels,
        texttemplate="%{text}",
        hoverinfo="text",
        hovertext=hover_text,
        colorscale=[[0.0, '#ef4444'], [0.5, '#1e293b'], [1.0, '#10b981']],
        zmin=c_min,
        zmax=c_max,
        showscale=False
    ))
    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=0),
        height=320,
        xaxis_title="Terminal Growth Rate (g) ➡️",
        yaxis_title="WACC (Discount Rate) ⬇️",
        yaxis=dict(autorange='reversed', showgrid=False, zeroline=False),
        xaxis=dict(showgrid=False, zeroline=False),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#94a3b8')
    )
    st.session_state[cache_k] = (fig, heat_summary)
    return fig, heat_summary


def draw_football_field_chart(engine, heat_stats: dict | None = None, lang_key: str = "zh"):
    """
    🌟 审计升级 II-3：摩根士丹利/高盛投行级【估值足球场图 (Valuation Football Field Chart)】
    在同一横向浮动区间条形图上对比：52周高低点、两阶段DCF区间、三表动态NWC DCF、同业P/E与EV/EBITDA隐含区间、华尔街目标价区间。
    """
    S = engine.price
    if S <= 0:
        return None

    bars = []
    # 1. 52-Week Range
    w52_low = float(engine.info.get('fiftyTwoWeekLow') or S * 0.75)
    w52_high = float(engine.info.get('fiftyTwoWeekHigh') or S * 1.25)
    if w52_high > w52_low > 0:
        bars.append((
            "52周历史交易区间 (52W Range)" if lang_key == "zh" else "52-Week Trading Range",
            w52_low, w52_high, (w52_low + w52_high) / 2.0, "#64748b"
        ))

    # 2. Two-Stage Fading DCF Range
    if heat_stats and heat_stats.get("worst") and heat_stats.get("best"):
        dcf_low = float(heat_stats["worst"])
        dcf_high = float(heat_stats["best"])
        dcf_mid = float(engine.val_dcf or (dcf_low + dcf_high) / 2.0)
        bars.append((
            "两阶段衰减 DCF (敏感性区间)" if lang_key == "zh" else "2-Stage Fading DCF Range",
            dcf_low, dcf_high, dcf_mid, "#10b981"
        ))
    elif engine.val_dcf and engine.val_dcf > 0:
        bars.append((
            "两阶段衰减 DCF (±15% 区间)" if lang_key == "zh" else "2-Stage Fading DCF (±15%)",
            engine.val_dcf * 0.85, engine.val_dcf * 1.15, engine.val_dcf, "#10b981"
        ))

    # 3. 3-Statement Dynamic NWC DCF Range
    if engine.val_3stmt_dcf and engine.val_3stmt_dcf > 0:
        v3 = float(engine.val_3stmt_dcf)
        bars.append((
            "三表真实 NWC 动态 DCF (±12%)" if lang_key == "zh" else "3-Stmt Dynamic NWC DCF",
            v3 * 0.88, v3 * 1.12, v3, "#38bdf8"
        ))

    # 4. Peer Comps Implied Valuation Range
    csum = engine.comps_summary or {}
    imp_pe = csum.get("implied_pe_price")
    imp_ev = csum.get("implied_ev_price")
    comp_candidates = [v for v in [imp_pe, imp_ev, engine.val_pe] if v and v > 0]
    if comp_candidates:
        c_low = min(comp_candidates) * 0.90
        c_high = max(comp_candidates) * 1.10
        c_mid = float(np.mean(comp_candidates))
        bars.append((
            "同业可比倍数隐含估值 (Peer Comps)" if lang_key == "zh" else "Peer Comps (P/E & EV/EBITDA)",
            c_low, c_high, c_mid, "#a855f7"
        ))

    # 5. Wall Street Consensus Target Range
    ws_low = float(engine.info.get('targetLowPrice') or 0.0)
    ws_high = float(engine.info.get('targetHighPrice') or 0.0)
    ws_mean = float(engine.info.get('targetMeanPrice') or 0.0)
    if ws_high > ws_low > 0:
        bars.append((
            "华尔街投行目标价区间 (WS Targets)" if lang_key == "zh" else "Wall Street Analyst Targets",
            ws_low, ws_high, ws_mean if ws_mean > 0 else (ws_low + ws_high) / 2.0, "#f59e0b"
        ))

    if not bars:
        return None

    fig = go.Figure()
    for label, low_v, high_v, mid_v, color_hex in bars:
        span = max(high_v - low_v, S * 0.02)
        fig.add_trace(go.Bar(
            y=[label],
            x=[span],
            base=[low_v],
            orientation='h',
            marker=dict(color=color_hex, opacity=0.78, line=dict(color='#ffffff', width=1)),
            text=[f"{engine.currency} {low_v:.2f}  —  Mid: {mid_v:.2f}  —  {high_v:.2f}"],
            textposition="inside",
            insidetextanchor="middle",
            hovertemplate=f"<b>{label}</b><br>Floor: {engine.currency} {low_v:.2f}<br>Midpoint: {engine.currency} {mid_v:.2f}<br>Ceiling: {engine.currency} {high_v:.2f}<extra></extra>",
            name=label
        ))

    fig.add_vline(
        x=S, line_width=2.5, line_dash="dash", line_color="#facc15",
        annotation_text=f"Spot Price: {engine.currency} {S:.2f}",
        annotation_position="top",
        annotation_font=dict(color="#facc15", size=13)
    )
    fig.update_layout(
        title=dict(
            text="🏟️ 投行级多模型估值足球场全景图 (IB Valuation Football Field)" if lang_key == "zh" else "🏟️ Institutional Valuation Football Field Matrix",
            font=dict(color="#ffffff", size=15)
        ),
        xaxis_title=f"Implied Share Price ({engine.currency}) ➡️",
        barmode='overlay',
        showlegend=False,
        height=290,
        margin=dict(l=10, r=10, t=42, b=10),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#cbd5e1'),
        xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.06)'),
        yaxis=dict(showgrid=False)
    )
    return fig


def draw_pro_candlestick(ticker):
    hist = fetch_candlestick_history(ticker)
    if hist.empty:
        return None
    hist = hist.copy()
    hist['MA20'] = hist['Close'].rolling(20).mean()
    hist['MA50'] = hist['Close'].rolling(50).mean()
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=hist.index, open=hist['Open'], high=hist['High'],
        low=hist['Low'], close=hist['Close'], name='Price'
    ))
    fig.add_trace(go.Scatter(x=hist.index, y=hist['MA20'], line=dict(color='#f59e0b', width=1.5), name='20-Day SMA'))
    fig.add_trace(go.Scatter(x=hist.index, y=hist['MA50'], line=dict(color='#3b82f6', width=1.5), name='50-Day SMA'))
    fig.update_layout(
        xaxis_rangeslider_visible=False, height=350, margin=dict(l=0, r=0, t=10, b=0),
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#94a3b8'),
        xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )
    return fig


def draw_beta_scatter(engine):
    """
    🌟 审计升级 III-4：
    使用带截距项的线性回归 y = α + β_raw * x 绘制真实 OLS 回归线，并在标题同时展示 Blume β、Raw β、年化 Jensen's Alpha (α) 与 R²！
    """
    if engine.scatter_data is None or engine.scatter_data.empty:
        return None
    stock_ret = engine.scatter_data.iloc[:, 0]
    market_ret = engine.scatter_data.iloc[:, 1]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=market_ret, y=stock_ret, mode='markers',
        marker=dict(color='#38bdf8', size=7, opacity=0.82), name='Monthly Returns'
    ))
    x_range = np.linspace(market_ret.min(), market_ret.max(), 100)
    y_ols = engine.alpha_monthly + engine.raw_beta * x_range
    fig.add_trace(go.Scatter(
        x=x_range, y=y_ols, mode='lines',
        line=dict(color='#ef4444', width=2.2),
        name=f"OLS Fit (Raw β={engine.raw_beta:.2f}, α={engine.alpha_annual*100:+.1f}%/yr)"
    ))
    fig.update_layout(
        title=dict(
            text=f"Blume β={engine.beta:.2f} | Raw β={engine.raw_beta:.2f} | Jensen's α={engine.alpha_annual*100:+.1f}%/yr | R²={engine.r_squared:.2f}",
            font=dict(color='#ffffff', size=12.5)
        ),
        xaxis_title="Market Benchmark Monthly Return",
        yaxis_title="Stock Monthly Return",
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#94a3b8'),
        xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
        showlegend=True, legend=dict(yanchor="top", y=0.98, xanchor="left", x=0.01, font=dict(size=10)),
        height=330, margin=dict(l=0, r=0, t=35, b=0)
    )
    return fig


def draw_option_payoff_diagram(engine, strategy_key, T_years, iv, lang_key="zh", legs_meta: dict | None = None, return_stats: bool = False):
    """
    🌟 审计升级 III-1：
    1) 与交易台真实对齐行权价 (snap_k)、股息率 q 及波动率偏度 (Skew IV) 100% 同步；
    2) 同时绘制【到期日盈亏实线 (Expiration Payoff)】与【半周期/盘中 B-S 动态理论盈亏虚线 (50% DTE)】；
    3) 线性插值精确求根找出所有【真实盈亏平衡点 (Exact Breakevens)】并在图上用菱形高亮标注；
    4) 基于几何布朗运动 (GBM) 对数正态分布数值积分，精确算出【到期风险中性盈利概率 (PoP %)】！
    """
    S = engine.price
    r = engine.rf
    s_grid = np.linspace(S * 0.70, S * 1.30, 300)
    # 用于计算风险中性到期胜率 (PoP%) 的宽域积分网格
    s_pop_grid = np.linspace(max(0.1, S * 0.25), S * 2.20, 1200)
    meta = legs_meta or {}

    k_atm = meta.get("k_atm", round(S, 2))
    k_95_put = meta.get("k_95_put", round(S * 0.95, 2))
    k_98_put = meta.get("k_98_put", round(S * 0.98, 2))
    k_otm_put = meta.get("k_otm_put", round(S * 0.92, 2))
    k_far_put = meta.get("k_far_put", round(S * 0.85, 2))
    k_otm_call = meta.get("k_otm_call", round(S * 1.05, 2))
    k_108_call = meta.get("k_108_call", round(S * 1.08, 2))
    k_far_call = meta.get("k_far_call", round(S * 1.12, 2))

    atm_iv = max(float(meta.get("atm_iv", iv)), 0.05)
    put_iv = max(float(meta.get("put_iv", iv)), 0.05)
    call_iv = max(float(meta.get("call_iv", iv)), 0.05)
    q = float(meta.get("q_yield", 0.0))
    T_years = max(float(T_years), 1.0 / 365.0)
    T_mid = max(T_years * 0.5, 1.0 / 365.0)

    c_atm = engine.black_scholes_pricing(S, k_atm, T_years, r, atm_iv, q)["Call"]
    p_atm = engine.black_scholes_pricing(S, k_atm, T_years, r, atm_iv, q)["Put"]
    p_95 = engine.black_scholes_pricing(S, k_95_put, T_years, r, put_iv, q)["Put"]
    p_98 = engine.black_scholes_pricing(S, k_98_put, T_years, r, put_iv, q)["Put"]
    c_otm = engine.black_scholes_pricing(S, k_otm_call, T_years, r, call_iv, q)["Call"]
    c_108 = engine.black_scholes_pricing(S, k_108_call, T_years, r, call_iv, q)["Call"]
    p_otm = engine.black_scholes_pricing(S, k_otm_put, T_years, r, put_iv, q)["Put"]
    c_far = engine.black_scholes_pricing(S, k_far_call, T_years, r, call_iv, q)["Call"]
    p_far = engine.black_scholes_pricing(S, k_far_put, T_years, r, put_iv, q)["Put"]

    def _eval_exp_pnl(px_arr):
        if strategy_key == "cash_secured_put":
            return p_95 - np.maximum(k_95_put - px_arr, 0.0)
        elif strategy_key == "bear_put_spread":
            nd = max(0.05, p_98 - p_otm)
            return np.maximum(k_98_put - px_arr, 0.0) - np.maximum(k_otm_put - px_arr, 0.0) - nd
        elif strategy_key == "covered_call":
            return (px_arr - S) + c_otm - np.maximum(px_arr - k_otm_call, 0.0)
        elif strategy_key == "protective_put":
            return (px_arr - S) - p_otm + np.maximum(k_otm_put - px_arr, 0.0)
        elif strategy_key == "collar":
            return (px_arr - S) - p_otm + np.maximum(k_otm_put - px_arr, 0.0) + c_otm - np.maximum(px_arr - k_otm_call, 0.0)
        elif strategy_key == "bull_call_spread":
            nd = max(0.05, c_atm - c_108)
            return np.maximum(px_arr - k_atm, 0.0) - np.maximum(px_arr - k_108_call, 0.0) - nd
        elif strategy_key == "iron_condor":
            nc = max(0.05, (c_108 - c_far) + (p_otm - p_far))
            cs_l = np.maximum(px_arr - k_108_call, 0.0) - np.maximum(px_arr - k_far_call, 0.0)
            ps_l = np.maximum(k_otm_put - px_arr, 0.0) - np.maximum(k_far_put - px_arr, 0.0)
            return nc - cs_l - ps_l
        elif strategy_key == "long_call":
            return np.maximum(px_arr - k_atm, 0.0) - c_atm
        elif strategy_key == "long_put":
            return np.maximum(k_atm - px_arr, 0.0) - p_atm
        else:
            return np.maximum(px_arr - k_atm, 0.0) + np.maximum(k_atm - px_arr, 0.0) - (c_atm + p_atm)

    pnl = _eval_exp_pnl(s_grid)

    if strategy_key == "cash_secured_put":
        pnl_mid = p_95 - engine.black_scholes_pricing(s_grid, k_95_put, T_mid, r, put_iv, q)["Put"]
        label = f"Cash-Secured Short Put (Sell Put @ {k_95_put:.2f}, Credit: +{p_95:.2f})"
    elif strategy_key == "bear_put_spread":
        net_debit_bp = max(0.05, p_98 - p_otm)
        pnl_mid = (
            engine.black_scholes_pricing(s_grid, k_98_put, T_mid, r, put_iv, q)["Put"]
            - engine.black_scholes_pricing(s_grid, k_otm_put, T_mid, r, put_iv, q)["Put"]
            - net_debit_bp
        )
        label = f"Bear Put Spread (Buy {k_98_put:.2f} Put / Sell {k_otm_put:.2f} Put)"
    elif strategy_key == "covered_call":
        pnl_mid = (s_grid - S) + c_otm - engine.black_scholes_pricing(s_grid, k_otm_call, T_mid, r, call_iv, q)["Call"]
        label = f"Covered Call (Long Stock @ {S:.2f} + Short Call @ {k_otm_call:.2f})"
    elif strategy_key == "protective_put":
        pnl_mid = (s_grid - S) - p_otm + engine.black_scholes_pricing(s_grid, k_otm_put, T_mid, r, put_iv, q)["Put"]
        label = f"Protective Put (Long Stock @ {S:.2f} + Long Put @ {k_otm_put:.2f})"
    elif strategy_key == "collar":
        pnl_mid = (
            (s_grid - S) - p_otm
            + engine.black_scholes_pricing(s_grid, k_otm_put, T_mid, r, put_iv, q)["Put"]
            + c_otm
            - engine.black_scholes_pricing(s_grid, k_otm_call, T_mid, r, call_iv, q)["Call"]
        )
        label = f"Collar (Long Put @ {k_otm_put:.2f} + Short Call @ {k_otm_call:.2f})"
    elif strategy_key == "bull_call_spread":
        net_debit = max(0.05, c_atm - c_108)
        pnl_mid = (
            engine.black_scholes_pricing(s_grid, k_atm, T_mid, r, atm_iv, q)["Call"]
            - engine.black_scholes_pricing(s_grid, k_108_call, T_mid, r, call_iv, q)["Call"]
            - net_debit
        )
        label = f"Bull Call Spread (Buy {k_atm:.2f} Call / Sell {k_108_call:.2f} Call)"
    elif strategy_key == "iron_condor":
        net_credit = max(0.05, (c_108 - c_far) + (p_otm - p_far))
        pnl_mid = net_credit - (
            engine.black_scholes_pricing(s_grid, k_108_call, T_mid, r, call_iv, q)["Call"]
            - engine.black_scholes_pricing(s_grid, k_far_call, T_mid, r, call_iv, q)["Call"]
        ) - (
            engine.black_scholes_pricing(s_grid, k_otm_put, T_mid, r, put_iv, q)["Put"]
            - engine.black_scholes_pricing(s_grid, k_far_put, T_mid, r, put_iv, q)["Put"]
        )
        label = f"Iron Condor (Profit Zone: {k_otm_put:.2f} ~ {k_108_call:.2f})"
    elif strategy_key == "long_call":
        pnl_mid = engine.black_scholes_pricing(s_grid, k_atm, T_mid, r, atm_iv, q)["Call"] - c_atm
        label = f"Long Call (Buy Call @ {k_atm:.2f}, Cost: {c_atm:.2f})"
    elif strategy_key == "long_put":
        pnl_mid = engine.black_scholes_pricing(s_grid, k_atm, T_mid, r, atm_iv, q)["Put"] - p_atm
        label = f"Long Put (Buy Put @ {k_atm:.2f}, Cost: {p_atm:.2f})"
    else:
        total_prem = c_atm + p_atm
        pnl_mid = (
            engine.black_scholes_pricing(s_grid, k_atm, T_mid, r, atm_iv, q)["Call"]
            + engine.black_scholes_pricing(s_grid, k_atm, T_mid, r, atm_iv, q)["Put"]
            - total_prem
        )
        label = f"Long Straddle (ATM Strike @ {k_atm:.2f}, Cost: {total_prem:.2f})"

    # 🌟 1. 线性插值精确求根找出所有盈亏平衡点 (Exact Breakevens)
    pnl_pop = _eval_exp_pnl(s_pop_grid)
    breakevens = []
    for idx in range(len(s_pop_grid) - 1):
        y0, y1 = pnl_pop[idx], pnl_pop[idx + 1]
        if (y0 <= 0 < y1) or (y0 >= 0 > y1):
            x0, x1 = s_pop_grid[idx], s_pop_grid[idx + 1]
            be_x = x0 - y0 * (x1 - x0) / (y1 - y0) if abs(y1 - y0) > 1e-9 else x0
            if not breakevens or abs(be_x - breakevens[-1]) > (S * 0.005):
                breakevens.append(round(float(be_x), 2))

    # 🌟 2. 基于 GBM 对数正态分布计算风险中性到期盈利概率 (Probability of Profit, PoP %)
    mu_log = np.log(max(S, 1e-4)) + (r - q - 0.5 * (atm_iv ** 2)) * T_years
    std_log = max(atm_iv * np.sqrt(T_years), 1e-4)
    pdf_vals = (1.0 / (s_pop_grid * std_log * np.sqrt(2.0 * np.pi))) * np.exp(-0.5 * ((np.log(s_pop_grid) - mu_log) / std_log) ** 2)
    _trapz_fn = getattr(np, "trapezoid", getattr(np, "trapz", None))
    if _trapz_fn is not None:
        total_prob = float(_trapz_fn(pdf_vals, s_pop_grid))
        profit_prob = float(_trapz_fn(np.where(pnl_pop > 0, pdf_vals, 0.0), s_pop_grid))
    else:
        dx = np.diff(s_pop_grid)
        total_prob = float(np.sum(0.5 * (pdf_vals[:-1] + pdf_vals[1:]) * dx))
        prof_y = np.where(pnl_pop > 0, pdf_vals, 0.0)
        profit_prob = float(np.sum(0.5 * (prof_y[:-1] + prof_y[1:]) * dx))
    pop_pct = float(np.clip((profit_prob / total_prob) * 100.0 if total_prob > 0 else 50.0, 1.0, 99.0))

    pnl_contract = pnl * 100.0
    pnl_mid_contract = pnl_mid * 100.0

    be_str = ", ".join([f"{engine.currency} {b:.2f}" for b in breakevens]) if breakevens else "N/A"
    full_title = f"{label}  |  🎯 PoP (到期胜率): {pop_pct:.1f}%  |  ⚖️ Breakeven: {be_str}"

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=s_grid, y=np.where(pnl_contract >= 0, pnl_contract, 0),
        fill='tozeroy', mode='none', fillcolor='rgba(16, 185, 129, 0.20)',
        name='Expiration Profit' if lang_key == 'en' else '到期盈利区'
    ))
    fig.add_trace(go.Scatter(
        x=s_grid, y=np.where(pnl_contract < 0, pnl_contract, 0),
        fill='tozeroy', mode='none', fillcolor='rgba(239, 68, 68, 0.20)',
        name='Expiration Loss' if lang_key == 'en' else '到期亏损区'
    ))
    fig.add_trace(go.Scatter(
        x=s_grid, y=pnl_mid_contract, mode='lines',
        line=dict(color='#c084fc', width=2, dash='dash'),
        name='Mid-Term Theoretical B-S P&L (50% DTE)' if lang_key == 'en' else '盘中/半周期 B-S 动态盈亏曲线 (50% DTE)'
    ))
    fig.add_trace(go.Scatter(
        x=s_grid, y=pnl_contract, mode='lines',
        line=dict(color='#38bdf8', width=2.8),
        name='Expiration Payoff (100 Shares)' if lang_key == 'en' else '到期日终极盈亏折线 (1张=100股)'
    ))

    # 在图上高亮标注所有精确盈亏平衡点 (Breakevens)
    vis_bes = [b for b in breakevens if s_grid[0] <= b <= s_grid[-1]]
    if vis_bes:
        fig.add_trace(go.Scatter(
            x=vis_bes,
            y=[0.0] * len(vis_bes),
            mode='markers+text',
            marker=dict(color='#facc15', size=11, symbol='diamond', line=dict(color='#0f172a', width=1.5)),
            text=[f"BE: {b:.2f}" for b in vis_bes],
            textposition="top center",
            textfont=dict(color='#facc15', size=11),
            name='Breakeven Point' if lang_key == 'en' else '精确盈亏平衡点 (BE)'
        ))

    fig.add_hline(y=0, line_dash="dot", line_color="#94a3b8")
    fig.add_vline(x=S, line_dash="dash", line_color="#facc15", annotation_text=f"Spot: {engine.currency} {S:.2f}")

    fig.update_layout(
        title=dict(text=full_title, font=dict(color='#ffffff', size=13)),
        xaxis_title="Underlying Stock Price ➡️" if lang_key == "en" else "标的股票价格 ➡️",
        yaxis_title=f"Net P&L ({engine.currency} / 1 Contract)" if lang_key == "en" else f"净盈亏 ({engine.currency} / 每张合约100股)",
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#94a3b8'),
        xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=390, margin=dict(l=0, r=0, t=58, b=0)
    )
    if return_stats:
        return fig, float(np.max(pnl_contract)), float(np.min(pnl_contract)), {"breakevens": breakevens, "pop_pct": pop_pct}
    return fig, float(np.max(pnl_contract)), float(np.min(pnl_contract))


# ==============================================================================
# 7. 原生 Google Gemini API 投委会深度推演与双向闭环修正引擎 (V12.0: 审计级会话隔离 + 真实 2.5 模型)
# ==============================================================================
# 💡 如果您是私人单机使用且不想在网页端输入，可将免费的 Google AI Studio Key (AIzaSy...) 填在下方引号内：
DEFAULT_GEMINI_API_KEY = ""
GEMINI_CONFIG_FILE = Path.home() / ".tradingagents" / "gemini_config.json"


def is_cloud_shared_environment() -> bool:
    """
    🌟 审计修复 I-1：自动检测是否运行在 Streamlit Cloud / Docker 公网多租户容器环境。
    在公网云端环境下，严禁把用户在网页输入的 API Key 写入服务器共享磁盘文件，防止跨访客泄露！
    """
    if os.environ.get("ALLOW_LOCAL_KEY_SAVE") == "1":
        return False
    cloud_markers = (
        os.environ.get("STREAMLIT_SHARING_MODE"),
        os.environ.get("IS_STREAMLIT_CLOUD"),
        os.environ.get("STREAMLIT_SERVER_HEADLESS") == "true" and Path("/mount/src").exists(),
        Path("/mount/src").exists(),
        Path("/home/appuser").exists(),
    )
    return any(bool(m) for m in cloud_markers)


def load_saved_gemini_key() -> str:
    """优先从当前浏览器隔离会话 st.session_state 读取 Key；仅在单机环境下才允许读取本地磁盘配置"""
    sess_key = str(st.session_state.get("user_gemini_key") or "").strip()
    if sess_key:
        return sess_key
    if DEFAULT_GEMINI_API_KEY.strip():
        return DEFAULT_GEMINI_API_KEY.strip()
    try:
        sec_key = st.secrets.get("GEMINI_API_KEY") or st.secrets.get("GOOGLE_API_KEY") or ""
        if str(sec_key).strip():
            return str(sec_key).strip()
    except Exception:
        pass
    env_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""
    if env_key.strip():
        return env_key.strip()
    if not is_cloud_shared_environment() and GEMINI_CONFIG_FILE.exists():
        try:
            data = json.loads(GEMINI_CONFIG_FILE.read_text(encoding="utf-8"))
            return str(data.get("gemini_api_key") or "").strip()
        except Exception:
            return ""
    return ""


def save_gemini_key_local(api_key: str, allow_disk: bool = False):
    """
    🌟 审计修复 I-1：
    网页端输入的 API Key 默认仅保存在当前访客独立的浏览器会话 st.session_state["user_gemini_key"] 中（关闭网页即销毁）。
    只有当处于本地单机环境且用户勾选 allow_disk 时，才写入本地磁盘文件。
    """
    clean_k = api_key.strip()
    st.session_state["user_gemini_key"] = clean_k
    if allow_disk and not is_cloud_shared_environment():
        GEMINI_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        GEMINI_CONFIG_FILE.write_text(
            json.dumps({"gemini_api_key": clean_k}, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )


def build_committee_prompts(engine, pipe: dict, user_cash: float, user_shares: int, lang_key: str):
    lang_str = "请全程使用专业、犀利的华尔街机构中文输出" if lang_key == "zh" else "Respond entirely in institutional Wall Street English"
    system_prompt = (
        f"You are the Chief Investment Officer and Multi-Agent TradingAgents Committee (powered by Google Gemini) "
        f"for {engine.name} ({engine.ticker}). {lang_str}. "
        f"CRITICAL RULE: Never hallucinate financial numbers. Strictly anchor all valuation, technical, and options "
        f"arguments to the exact quantitative & Black-Scholes metrics provided below."
    )
    headlines_formatted = "\n".join([f"  * {h}" for h in pipe['news']]) if pipe['news'] else "  * No major breaking headlines."
    strikes_sample = ", ".join([f"{k:.2f}" for k in (pipe['opt_info'].get('strikes') or []) if abs(k - engine.price) / max(engine.price, 1) <= 0.18][:15])

    past_memories = [m for m in load_memory_ledger() if m.get("ticker") == engine.ticker][:3]
    if past_memories:
        mem_lines = []
        for m in past_memories:
            rec_p = float(m.get("recorded_price") or engine.price)
            chg = ((engine.price - rec_p) / rec_p * 100.0) if rec_p > 0 else 0.0
            mem_lines.append(
                f"  * 日期 {m.get('date')}: 当时评级={m.get('rating')} ({m.get('trader_action')}), "
                f"记录价={rec_p:.2f} -> 现价={engine.price:.2f} (真实涨跌: {chg:+.2f}%), 当时推荐期权={m.get('option_strategy')}"
            )
        memory_context_str = "\n".join(mem_lines)
    else:
        memory_context_str = "  * 暂无该标的的历史归档记录（本次为首次建档研判）。"

    user_context = f"""
[1. 标的基本面与多模型估值底稿 (Quantitative Valuation Grounding)]
- 股票代码与名称: {engine.ticker} ({engine.name}) | 行业: {engine.sector} | 计价货币: {engine.currency}
- 当前最新市价 (Spot Price): {engine.currency} {engine.price:.2f}
- 系统主推模型 ({engine.model_name}) 内在公允价: {engine.currency} {engine.fair_val:.2f} (安全边际 MoS: {pipe['mos_pct']:+.1f}%)
- 两阶段衰减 DCF 公允价: {engine.currency} {(engine.val_dcf or 0):.2f} | 三表真实营运资本动态 DCF (DSO={engine.hist_dso}/DIO={engine.hist_dio}/DPO={engine.hist_dpo}): {engine.currency} {(engine.val_3stmt_dcf or 0):.2f} | 同业中位数 P/E 倍数估值: {engine.currency} {(engine.val_pe or 0):.2f}
- WACC 折现门槛: {engine.wacc*100:.2f}% (Rf={engine.rf*100:.2f}%, {engine.kd_tag}, {engine.tax_tag}) | Blume β={engine.beta:.2f} (Raw β={engine.raw_beta:.2f}, 年化 Jensen's α={engine.alpha_annual*100:+.1f}%) | 测谎仪市场隐含年化增长率: {pipe['implied_g_pct']:.2f}%
- 华尔街投行平均目标价: {engine.currency} {pipe['target_mean']:.2f} (华尔街预期空间: {pipe['ws_upside']:+.1f}%) | 股息率: {pipe['div_yield']:.2f}%

[2. 技术面量价、尾部风险与凯利仓位信号 (Technical, Tail-Risk & Kelly Sizing)]
- 趋势结构判定: {pipe['tech']['trend']} | RSI(14): {pipe['tech']['rsi']:.1f} | MACD 柱状图: {pipe['tech']['macd_hist']:+.3f}
- 均线系统: MA20={pipe['tech']['ma20']:.2f}, MA50={pipe['tech']['ma50']:.2f}, MA200={pipe['tech']['ma200']:.2f}
- 14日真实波幅 (ATR): {engine.currency} {pipe['tech']['atr']:.2f} | 20日关键支撑位: {pipe['tech']['support']:.2f} | 20日关键阻力位: {pipe['tech']['resistance']:.2f}
- 1年历史最大回撤 (Max Drawdown): {pipe['tech']['mdd_pct']:.1f}% | 95% 日度在险价值 (VaR): {pipe['tech']['var_95_pct']:.2f}% | 95% 条件在险价值 (CVaR/Expected Shortfall): {pipe['tech']['cvar_95_pct']:.2f}%
- 半凯利公式 (Half-Kelly) 推算参数: 量化胜率 p={pipe['kelly_win_prob']:.1f}%, 盈亏赔率 b={pipe['kelly_odds']:.2f}x -> 全凯利={pipe['kelly_full_pct']:.1f}%, 半凯利建议仓位={pipe['alloc_pct']:.1f}%

[3. 期权链、波动率曲面与财报日预警 (Options Chain, Vol Skew & Earnings Radar)]
- 主力期权到期日: {pipe['opt_info']['expiry']} (剩余 {pipe['opt_info'].get('days', 30)} 天)
- 下一季财报日 (Earnings Date): {pipe['opt_info'].get('earnings_date', 'N/A')} (距离今天: {pipe['opt_info'].get('days_to_earnings', 'N/A')} 天 | 跨财报IV坍塌预警: {pipe['opt_info'].get('earnings_alert', False)})
- 平值跨式隐含波幅 (ATM Straddle Implied Move): ±{pipe['opt_info'].get('implied_move_pct', 0.0):.1f}%
- 平值隐含波动率 (ATM IV): {pipe['opt_info']['atm_iv']*100:.1f}% vs 30日历史波动率 (HV30): {pipe['tech']['hv30']*100:.1f}%
- IV/HV 波动率溢价倍数: {pipe['opt_info']['iv_hv_ratio']:.2f}x | Put-Call 偏度 (Skew): {pipe['opt_info']['skew']:+.1f}%
- 现价附近真实可交易行权价 (Tradable Strikes): {strikes_sample or 'Synthetic Strikes'}
- 量化模型初步评级: {pipe['final_rating']} (综合得分 {pipe['total_score']:+.1f}) | 初选期权方案: {pipe['opt_strategy_name']} ({pipe['opt_action_detail']})

[4. 投资者账户当前持仓上下文 (Portfolio Context)]
- 可用现金: {engine.currency} {user_cash:,.2f} | 当前已持有正股数量: {user_shares} 股

[5. 实时抓取的最新财经新闻标题 (Live Yahoo Finance Headlines)]
{headlines_formatted}

[6. 历史记忆账本与自我反思 (Episodic Memory & Past Verdicts)]
{memory_context_str}

请严格基于以上真实量化数据与新闻，与本地量化模型的初判（{pipe['final_rating']} / {pipe['opt_strategy_name']}）展开深度交叉辩论，输出结构化报告：
1. **📰 实时新闻、历史反思与预期差研判**：结合最新新闻标题、历史记忆账本盈亏以及测谎仪隐含增长率 ({pipe['implied_g_pct']:.1f}%)，剖析市场是否存在泡沫或错杀。
2. **⚔️ 多空研究员深度交锋 (Bull vs. Bear Deep Debate)**：
   - 🐂 **看多研究员 (Bull Case)**：从现金流护城河、三表营运资本优势与期权收租胜率展开立论并反驳空头。
   - 🐻 **看空研究员 (Bear Case)**：从 WACC 折现压力、最大回撤/CVaR 尾部风险与财报波动率风险展开立论并反驳多头。
3. **💵 正股精准交易与半凯利仓位执行计划 (Spot Equity & Half-Kelly Execution Plan)**：结合账户可用现金 ({engine.currency} {user_cash:,.0f})、现有持仓 ({user_shares} 股) 及半凯利建议仓位 ({pipe['alloc_pct']:.1f}%)，给出分批建仓区间、2x ATR 硬止损价 ({engine.currency} {pipe['stop_loss']:.2f}) 及分批止盈目标位。
4. **🎯 期权（Options）实战组合策略手册 (Options Tactical Playbook)**：
   - **主推期权策略**：明确给出到期日 ({pipe['opt_info']['expiry']})、具体 Buy/Sell 哪一个真实行权价 (Strike)、预估权利金收支、精确盈亏平衡点以及财报 IV Crush 防护逻辑。
   - **动态移仓 (Roll) 应对手册**：说明若正股大涨突破阻力位、大跌触及支撑位或横盘损耗殆尽时，该如何动态向上/向下/向远期移仓 (Roll)。
5. **👑 基金经理终审裁决**：给出最终五档评级（Buy / Overweight / Hold / Underweight / Sell）与一句话行动纲领。

【重要机器可读闭环指令】：在报告的最末尾，请务必附带以下单行 XML 包裹的 JSON 块（用于反向同步更新系统主控台与期权盈亏图，合法 opt_strat_key 仅限：cash_secured_put, bull_call_spread, covered_call, iron_condor, collar, bear_put_spread, protective_put, straddle）：
<GEMINI_VERDICT_JSON>{{"gemini_rating": "Buy", "gemini_action": "BUY", "gemini_alloc_pct": {pipe['alloc_pct']:.0f}, "gemini_opt_strat_key": "{pipe['opt_strat_key']}", "override_summary": "一句话说明Gemini维持或修正量化模型初判的核心原因"}}</GEMINI_VERDICT_JSON>
"""
    return system_prompt, user_context


def parse_gemini_verdict(raw_text: str, default_pipe: dict) -> tuple[str, dict]:
    """解析 Gemini 返回的双向闭环裁决 JSON，并将标签从展示文本中剥离"""
    verdict = {
        "gemini_rating": default_pipe["final_rating"],
        "gemini_action": default_pipe["trader_action"],
        "gemini_alloc_pct": default_pipe["alloc_pct"],
        "gemini_opt_strat_key": default_pipe["opt_strat_key"],
        "override_summary": "Gemini 复核后确认维持本地量化模型的核心判断。"
    }
    clean_md = raw_text
    match = re.search(r"<GEMINI_VERDICT_JSON>\s*(\{.*?\})\s*</GEMINI_VERDICT_JSON>", raw_text, flags=re.DOTALL)
    if match:
        clean_md = raw_text[:match.start()].rstrip()
        try:
            parsed = json.loads(match.group(1))
            if isinstance(parsed, dict):
                for k in verdict:
                    if k in parsed and parsed[k] is not None:
                        verdict[k] = parsed[k]
        except Exception:
            pass
    return clean_md, verdict


def invoke_gemini_committee(api_key: str, model_name: str, engine, pipe: dict, user_cash: float, user_shares: int, lang_key: str) -> str:
    """
    🌟 审计修复 I-2：
    采用 Google 官方真实生产模型 ID (gemini-2.5-flash / gemini-2.5-pro / gemini-2.5-flash-lite / gemini-2.0-flash)，
    优先通过 google-genai SDK 或官方 REST v1beta generateContent 接口直接命中，彻底杜绝 404 NOT_FOUND！
    """
    clean_key = api_key.strip()
    system_prompt, user_context = build_committee_prompts(engine, pipe, user_cash, user_shares, lang_key)

    # 路径 A：如果安装了 google-genai SDK，优先调用
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=clean_key)
        resp_sdk = client.models.generate_content(
            model=model_name.strip(),
            contents=user_context,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.3,
            ),
        )
        if getattr(resp_sdk, "text", None):
            return resp_sdk.text
    except Exception:
        pass

    # 路径 B：零依赖官方 HTTPS REST 接口 (兼容所有真实 Gemini 2.5 / 2.0 模型)
    fallback_models = [model_name.strip(), "gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.5-flash-lite", "gemini-2.0-flash"]
    last_err = ""
    for m_try in dict.fromkeys(fallback_models):
        url_fallback = f"https://generativelanguage.googleapis.com/v1beta/models/{m_try}:generateContent?key={clean_key}"
        payload_fb = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_context}]}],
            "generationConfig": {"temperature": 0.3},
        }
        r_fb = requests.post(url_fallback, json=payload_fb, timeout=90)
        if r_fb.status_code == 200:
            cands = r_fb.json().get("candidates", [])
            if cands:
                parts = cands[0].get("content", {}).get("parts", [])
                return "".join(p.get("text", "") for p in parts if "text" in p)
        else:
            last_err = f"[{r_fb.status_code}] {r_fb.text[:300]}"

    raise RuntimeError(f"Gemini API 调用失败，请检查 API Key 或网络: {last_err}")


def invoke_live_llm_committee(api_key: str, base_url: str, model_name: str, engine, pipe: dict, user_cash: float, user_shares: int, lang_key: str):
    """其他人员可选的兼容接口 (OpenAI / DeepSeek / OpenRouter)"""
    system_prompt, user_context = build_committee_prompts(engine, pipe, user_cash, user_shares, lang_key)
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key.strip()}", "Content-Type": "application/json"}
    payload = {
        "model": model_name.strip(),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_context}
        ],
        "temperature": 0.3
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


# ==============================================================================
# 8. 主程序与 8 大 Tabs 渲染
# ==============================================================================
def main():
    col_title, col_lang = st.columns([3, 1.2])
    with col_lang:
        selected_lang = st.selectbox("🌐 Language / 语言", options=["中文", "English"], index=0)
        lang_key = "zh" if selected_lang == "中文" else "en"
        T = TEXTS[lang_key]

    with col_title:
        st.markdown(f"<h1 style='color: #ffffff; font-weight: 800; font-size: 2rem;'>{T['title']}</h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: #38bdf8; font-weight: 600; font-size: 14px; margin-top: -5px;'>{T['subtitle']}</p>", unsafe_allow_html=True)

    st.write("---")

    with st.container(border=True):
        if "ticker_input" not in st.session_state:
            st.session_state.ticker_input = "NVDA"

        def set_ticker(t):
            st.session_state.ticker_input = t

        st.write(T['quick_tag'])
        q1, q2, q3, q4 = st.columns(4)
        q1.button("🇺🇸 NVDA", on_click=set_ticker, args=("NVDA",), use_container_width=True)
        q2.button("🇺🇸 AAPL", on_click=set_ticker, args=("AAPL",), use_container_width=True)
        q3.button("🇲🇾 MAYBANK (1155.KL)", on_click=set_ticker, args=("1155.KL",), use_container_width=True)
        q4.button("🇲🇾 TENAGA (5347.KL)", on_click=set_ticker, args=("5347.KL",), use_container_width=True)

        col_in1, col_in2 = st.columns([2, 2])
        with col_in1:
            ticker_input = st.text_input(T['input_label'], key="ticker_input")

        with st.expander(T['param_title'], expanded=False):
            st.info(T['param_tip'])
            c_erp, c_g2 = st.columns(2)
            custom_erp = c_erp.slider(T['erp_label'], 4.0, 7.0, 5.0, 0.1) / 100.0
            custom_g2 = c_g2.slider(T['g2_label'], 1.0, 3.5, 2.0, 0.1) / 100.0

        st.caption(T['esg_caption'])

    if ticker_input:
        with st.spinner("Compiling Hardcore Institutional Engine & TradingAgents Graph..." if lang_key == 'en' else "正在拉取华尔街核心引擎与 TradingAgents 多智能体数据..."):
            engine = UltimateHardcoreEngine(ticker_input)
            val, implied_g = engine.run_valuation(custom_erp, custom_g2)

            st.markdown(
                f"<h3 style='margin-top: 25px;'>🏢 {engine.name} ({engine.ticker}) "
                f"<span style='font-size:14px; color:#94a3b8;'>| Sector: {engine.sector}</span></h3>",
                unsafe_allow_html=True
            )

            tabs_names = [
                "📊 [1] Quant Valuation (量化估值)" if lang_key == "zh" else "📊 [1] Quant Valuation",
                "⚙️ [2] 3-Statement & NWC (硬核三表)" if lang_key == "zh" else "⚙️ [2] 3-Statement & NWC",
                "🏛️ [3] Dynamic LBO (收购沙盘)" if lang_key == "zh" else "🏛️ [3] Dynamic LBO",
                "🏢 [4] Comps Matrix (同业对比)" if lang_key == "zh" else "🏢 [4] Comps Matrix",
                "🎲 [5] Monte Carlo (蒙特卡洛)" if lang_key == "zh" else "🎲 [5] Monte Carlo",
                "📈 [6] Efficient Frontier (有效前沿)" if lang_key == "zh" else "📈 [6] Efficient Frontier",
                "📉 [7] Options Chain & BS (期权沙盘)" if lang_key == "zh" else "📉 [7] Options Chain & BS",
                "🤖 [8] TradingAgents IC & Options Desk (多智能体投委会) ⭐" if lang_key == "zh" else "🤖 [8] TradingAgents IC & Options Desk ⭐"
            ]

            tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs(tabs_names)

            # ==========================================
            # TAB 1: 估值面板
            # ==========================================
            with tab1:
                with st.container(border=True):
                    st.markdown(f"**{T['macro_title']}**")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Beta Risk", f"{engine.beta:.2f}", delta=engine.beta_type, delta_color="off")
                    c2.metric("Rf Rate (10Y Yield)", f"{engine.rf * 100:.2f}%", delta=engine.tax_tag, delta_color="off")
                    c3.metric("WACC", f"{engine.r * 100:.2f}%", engine.esg_tag)
                    st.caption(T['macro_exp'])

                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

                st.markdown(f"#### {T['matrix_header']}")
                m_col1, m_col2, m_col3 = st.columns(3)

                def render_matrix_card(title, model_val, price, is_rec, currency, note, empty_msg):
                    badge_text = T["badge_recommended"] if is_rec else T["badge_reference"]
                    card_border = "#10b981" if is_rec else "#334155"
                    if model_val and model_val > 0:
                        val_str = f"{currency} {model_val:.2f}"
                        diff = (model_val - price) / price * 100.0 if price > 0 else 0
                        diff_sign = "+" if diff > 0 else ""
                        pill_color = "#22c55e" if diff > 0 else "#f43f5e"
                        status_html = f"<div style='color: {pill_color}; font-weight: 700; font-size: 13px;'>{diff_sign}{diff:.1f}% {T['vs_market']}</div>"
                    else:
                        val_str = "N/A"
                        status_html = f"<div style='color: #f87171; font-size: 12px;'>⚠️ {empty_msg}</div>"

                    return f"""
                    <div style="background: linear-gradient(135deg, rgba(30, 41, 59, 0.9) 0%, rgba(15, 23, 42, 0.95) 100%); border: 1.5px solid {card_border}; border-radius: 12px; padding: 18px; min-height: 175px; display: flex; flex-direction: column; justify-content: space-between;">
                        <div>
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                <span style="font-size: 14px; font-weight: 700; color: #f8fafc;">{title}</span>
                                <span style="background: rgba(56, 189, 248, 0.15); color: #38bdf8; font-size: 10.5px; font-weight: 700; padding: 2px 8px; border-radius: 12px;">{badge_text}</span>
                            </div>
                            <div style="font-family: 'JetBrains Mono', monospace; font-size: 26px; font-weight: 800; color: #ffffff; margin: 4px 0;">{val_str}</div>
                            <div>{status_html}</div>
                        </div>
                        <div style="color: #94a3b8; font-size: 11.5px; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 8px; margin-top: 8px;">💡 {note}</div>
                    </div>
                    """

                with m_col1:
                    st.markdown(render_matrix_card(T["model_dcf_name"], engine.val_dcf, engine.price, engine.model_name == 'Discounted Cash Flow (DCF)', engine.currency, T["note_dcf"], T["no_data_dcf"]), unsafe_allow_html=True)
                with m_col2:
                    st.markdown(render_matrix_card(T["model_ddm_name"], engine.val_ddm, engine.price, engine.model_name == 'Dividend Discount Model (DDM)', engine.currency, T["note_ddm"], T["no_data_ddm"]), unsafe_allow_html=True)
                with m_col3:
                    st.markdown(render_matrix_card(T["model_pe_name"], engine.val_pe, engine.price, engine.model_name == 'P/E Multiples Valuation', engine.currency, T["note_pe"], T["no_data_pe"]), unsafe_allow_html=True)

                st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)

                p1, p2, p3 = st.columns(3)
                p1.metric(T['price'], f"{engine.currency} {engine.price:.2f}")
                p2.metric(T['fair_val'], f"{engine.currency} {val:.2f}")
                p3.metric(T['safe_buy'], f"{engine.currency} {(val * 0.8):.2f}", "20% Margin of Safety")

                st.info(T['fair_val_desc'])

                if val > 0 and engine.price > 0:
                    price_to_val = engine.price / val
                    fig_heat, heat_stats = (draw_sensitivity_heatmap(engine) if (engine.val_dcf and engine.val_dcf > 0) else (None, None))

                    # 🏛️ 投行升级 #3：估值足球场图 (Valuation Football Field Chart)
                    fig_ff = draw_football_field_chart(engine, heat_stats, lang_key)
                    if fig_ff:
                        ff_hdr = "### 🏟️ 投行级估值足球场图 (IB Valuation Football Field)" if lang_key == "zh" else "### 🏟️ Investment Banking Valuation Football Field"
                        st.markdown(ff_hdr)
                        with st.container(border=True):
                            st.caption(
                                "💡 横向对比 5 种核心估值维度的公允价值区间（52周历史交易区间、两阶段DCF、三表营运资本DCF、同业可比P/E估值、华尔街目标价），黄色虚线为当前现价。"
                                if lang_key == "zh" else
                                "💡 Compares fair value ranges across 5 valuation methodologies against the yellow dashed current spot price."
                            )
                            st.plotly_chart(fig_ff, use_container_width=True)

                    if engine.val_dcf and engine.val_dcf > 0:
                        st.markdown(f"### {T['heat_title']}")
                        with st.container(border=True):
                            st.markdown(T['heat_desc'], unsafe_allow_html=True)
                            if fig_heat and heat_stats:
                                st.plotly_chart(fig_heat, use_container_width=True)

                                wr = heat_stats['win_rate']
                                if wr >= 0.70:
                                    ai_insight = f"🟢 <b>高胜率 / 低估 (High Margin of Safety):</b> 无论宏观折现率如何波动，绝大多数预测情景（{heat_stats['green_count']}/{heat_stats['total']}）都显示该公司当前市价被严重低估，具备极厚的安全垫。" if lang_key == "zh" else f"🟢 <b>High Margin of Safety:</b> Across fluctuating discount rates, the majority of scenarios ({heat_stats['green_count']}/{heat_stats['total']}) show the stock is severely undervalued with a deep safety cushion."
                                elif wr <= 0.30:
                                    ai_insight = f"🔴 <b>高风险 / 高估 (Overvalued & Fragile):</b> 当前市价已透支未来。除非公司能在极低利率下保持疯狂增长，否则面临估值杀跌风险。" if lang_key == "zh" else f"🔴 <b>Overvalued & Fragile:</b> The current price has front-run its future. Unless it sustains hyper-growth in a zero-interest environment, it faces severe multiple contraction risk."
                                else:
                                    ai_insight = "🟡 <b>高度敏感 / 合理偏高 (Highly Sensitive):</b> 估值处于微妙的平衡点。当前价格对宏观利率(WACC)极为敏感，没有单边套利空间，属于“买定离手”的博弈区。" if lang_key == "zh" else "🟡 <b>Highly Sensitive:</b> Valuation is at a delicate equilibrium. The current price is extremely sensitive to macro rates (WACC), offering no clear margin of safety. It's a speculative play."

                                win_str = "胜率测算:" if lang_key == "zh" else "Win Rate Estimate:"
                                in_str = "在" if lang_key == "zh" else "In"
                                sc_str = "种宏观情景中，有" if lang_key == "zh" else "macro scenarios,"
                                safe_str = "种具备安全边际。" if lang_key == "zh" else "offer a solid margin of safety."
                                worst_str = "最悲观底线:" if lang_key == "zh" else "Pessimistic Floor:"
                                best_str = "最乐观上限:" if lang_key == "zh" else "Optimistic Ceiling:"
                                ai_header = "🤖 AI 矩阵智能解析 (Sensitivity Summary)" if lang_key == "zh" else "🤖 AI Sensitivity Summary Matrix"

                                st.markdown(f"""
                                <div style="background: rgba(15, 23, 42, 0.6); border-left: 4px solid #38bdf8; padding: 16px; border-radius: 6px; margin-top: 10px;">
                                    <div style="color: #38bdf8; font-weight: 800; font-size: 15px; margin-bottom: 8px;">
                                        {ai_header}
                                    </div>
                                    <div style="color: #e2e8f0; font-size: 14px; margin-bottom: 12px; line-height: 1.6;">
                                        {ai_insight}
                                    </div>
                                    <div style="display: flex; gap: 20px; color: #94a3b8; font-size: 12.5px; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 10px;">
                                        <div>⚡ <b>{win_str}</b> {in_str} {heat_stats['total']} {sc_str} <span style="color:#10b981; font-weight:bold;">{heat_stats['green_count']}</span> {safe_str}</div>
                                        <div>📉 <b>{worst_str}</b> {engine.currency} {heat_stats['worst']:.2f}</div>
                                        <div>🚀 <b>{best_str}</b> {engine.currency} {heat_stats['best']:.2f}</div>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)

                    col_lie, col_ai = st.columns(2)

                    with col_lie:
                        with st.container(border=True):
                            st.markdown(f"**{T['lie_title']}**")
                            implied_g_str = f"{implied_g * 100:.2f}%" if implied_g is not None else "N/A"
                            st.warning(f"To justify the current price of **{engine.price:.2f}**, the market implies a Growth Rate of **{implied_g_str} per year for {engine.horizon} years**.")

                            if implied_g is not None:
                                if implied_g > 0.40:
                                    diag = "-> **Diagnosis: EXTREME HYPE (Bubble Territory).**"
                                elif implied_g < 0.0:
                                    diag = "-> **Diagnosis: EXTREME PESSIMISM.**"
                                else:
                                    diag = "-> **Diagnosis: MODERATE EXPECTATIONS.**"
                                st.write(diag)
                            st.caption(T['lie_exp'])

                    with col_ai:
                        with st.container(border=True):
                            st.markdown(f"**{T['ai_title']}**")
                            div_rate = float(engine.info.get('dividendRate') or engine.info.get('trailingAnnualDividendRate') or 0.0)
                            div_yield = (div_rate / engine.price) * 100.0 if engine.price > 0 else 0.0

                            st.markdown(T['inc_title'])
                            st.write(f"- Dividend Yield: {div_yield:.2f}% | Beta Risk: {engine.beta:.2f}")
                            if engine.sector in ['Financial Services', 'Utilities', 'Real Estate'] and div_yield > 3.0:
                                st.success("-> **Verdict:** 🟢 SUITABLE FOR INCOME." if lang_key == "en" else "-> **结论:** 🟢 适合保守收息策略。")
                            else:
                                st.error("-> **Verdict:** 🔴 NOT IDEAL FOR INCOME." if lang_key == "en" else "-> **结论:** 🔴 不适合收息。")

                            st.markdown(T['cap_title'])
                            st.write(f"- Implied Growth: {implied_g_str} | Model Valuation: {val:.2f}")
                            if implied_g is not None and implied_g < 0.0 and engine.price < val:
                                st.success("-> **Verdict:** 🟢 MULTI-BAGGER POTENTIAL." if lang_key == "en" else "-> **结论:** 🟢 具备翻倍潜力。")
                            elif implied_g is not None and implied_g > 0.40:
                                st.error("-> **Verdict:** 🔴 HIGH SPECULATION RISK." if lang_key == "en" else "-> **结论:** 🔴 极度投机风险。")
                            else:
                                st.info("-> **Verdict:** 🟢 / 🟡 FAIRLY PRICED." if lang_key == "en" else "-> **结论:** 🟢 / 🟡 估值适中。")

                    st.markdown(f"### {T['exec_title']}")
                    if price_to_val <= 0.70 and (implied_g is not None and implied_g < 0.0):
                        rating, reason = '🟢 STRONG BUY', f"Extreme pessimism creates massive margin of safety. Price ({engine.price:.2f}) heavily discounted vs intrinsic value ({val:.2f})." if lang_key == "en" else f"极端悲观情绪砸出了巨大的安全垫。现价 ({engine.price:.2f}) 远低于内在公允价 ({val:.2f})。"
                    elif price_to_val <= 0.85:
                        rating, reason = '🟢 BUY', f"Solid value mispricing. Price ({engine.price:.2f}) meets 20% margin of safety." if lang_key == "en" else f"优秀的价值错配。现价 ({engine.price:.2f}) 满足20%安全边际要求。"
                    elif 0.85 < price_to_val <= 1.15:
                        rating, reason = '🟡 HOLD', f"Fairly valued. Price ({engine.price:.2f}) aligns with intrinsic value ({val:.2f})." if lang_key == "en" else f"估值合理。现价 ({engine.price:.2f}) 与其真实基本面价值 ({val:.2f}) 相符。"
                    elif 1.15 < price_to_val <= 1.40:
                        rating, reason = '🔴 SELL', f"Overvalued. Price ({engine.price:.2f}) exceeds intrinsic value ({val:.2f})." if lang_key == "en" else f"估值偏高。现价 ({engine.price:.2f}) 已透支未来，缺乏安全边际。"
                    else:
                        rating, reason = '🔴 STRONG SELL', f"Severe bubble risk. Implied growth is priced for perfection." if lang_key == "en" else f"严重的泡沫风险。市场对未来增长的定价过于完美且不切实际。"

                    with st.container(border=True):
                        st.markdown(f"- **Final Investment Rating : {rating}**")
                        st.markdown(f"- **Core Justification : {reason}**")
                        st.markdown("")
                        st.caption(T['rating_explain'])

                    col_t1, col_t2 = st.columns(2)
                    with col_t1:
                        with st.container(border=True):
                            st.markdown(f"**{T['plain_title']}**")
                            st.markdown(f"- **Required Hurdle Rate / Discount Rate:** {engine.r * 100:.2f}%")
                            st.markdown("  👉 Minimum required return." if lang_key == "en" else "  👉 您买入这家公司应当要求的最低回报门槛。")
                            if implied_g is not None:
                                st.markdown(f"- **Market Sentiment / Implied Growth:** {implied_g * 100:.2f}%")
                                if implied_g > 0.35:
                                    st.markdown("  👉 **【⚠️ SEVERE BUBBLE WARNING】**" if lang_key == "en" else "  👉 **【⚠️ 严重泡沫警示】市场极度狂热**")
                                elif implied_g < 0.0:
                                    st.markdown("  👉 **【🔥 EXTREME PESSIMISM / DEEP VALUE】**" if lang_key == "en" else "  👉 **【🔥 极度悲观 / 深度价值】情绪错杀**")
                                else:
                                    st.markdown("  👉 **【⚖️ BALANCED & RATIONAL】**" if lang_key == "en" else "  👉 **【⚖ 平衡理性】无盲目炒作**")

                    with col_t2:
                        with st.container(border=True):
                            st.markdown(f"**{T['fx_title']}**")
                            if not engine.is_malaysia:
                                st.warning(T['fx_content'])
                            else:
                                st.warning("- 🇲🇾 本地资产计价 (MYR)，无直接跨境外汇风险暴露。" if lang_key == "zh" else "- 🇲🇾 Local asset (MYR), no direct cross-border FX exposure.")

                    if not engine.is_malaysia:
                        target_mean = engine.info.get('targetMeanPrice')
                        target_high = engine.info.get('targetHighPrice')
                        target_low = engine.info.get('targetLowPrice')
                        num_analysts = engine.info.get('numberOfAnalystOpinions', 0)
                        rec_key = str(engine.info.get('recommendationKey', 'N/A')).upper()

                        if target_mean and num_analysts > 0:
                            st.markdown(f"<br><h3>{T['ws_title']}</h3>", unsafe_allow_html=True)
                            ws_col1, ws_col2, ws_col3 = st.columns(3)

                            with ws_col1:
                                with st.container(border=True):
                                    st.markdown(f"<div style='color:#94a3b8; font-size:13px; font-weight:600; text-align:center;'>{T['ws_mean']}</div>", unsafe_allow_html=True)
                                    st.markdown(f"<div style='font-size:30px; font-weight:800; font-family:JetBrains Mono; text-align:center; color:#ffffff; margin: 10px 0;'>${target_mean:.2f}</div>", unsafe_allow_html=True)
                                    st.markdown(f"<div style='color:#38bdf8; font-size:12.5px; text-align:center;'>👥 {num_analysts} Analysts</div>", unsafe_allow_html=True)

                            with ws_col2:
                                with st.container(border=True):
                                    st.markdown(f"<div style='color:#94a3b8; font-size:13px; font-weight:600; text-align:center;'>{T['ws_range']}</div>", unsafe_allow_html=True)
                                    low_str = f"${target_low:.2f}" if target_low else "N/A"
                                    high_str = f"${target_high:.2f}" if target_high else "N/A"
                                    st.markdown(f"<div style='font-size:24px; font-weight:800; font-family:JetBrains Mono; text-align:center; color:#ffffff; margin: 12px 0;'>{low_str} ~ {high_str}</div>", unsafe_allow_html=True)
                                    st.markdown(f"<div style='color:#cbd5e1; font-size:12px; text-align:center;'>Low / High Target</div>", unsafe_allow_html=True)

                            with ws_col3:
                                with st.container(border=True):
                                    st.markdown(f"<div style='color:#94a3b8; font-size:13px; font-weight:600; text-align:center;'>{T['ws_rating']}</div>", unsafe_allow_html=True)
                                    st.markdown(f"<div style='font-size:28px; font-weight:800; font-family:JetBrains Mono; text-align:center; color:#38bdf8; margin: 10px 0;'>{rec_key}</div>", unsafe_allow_html=True)
                                    st.markdown(f"<div style='color:#4ade80; font-size:12px; text-align:center;'>🏛️ {T['ws_tag']}</div>", unsafe_allow_html=True)

                            with st.container(border=True):
                                st.markdown(f"**{T['gap_title']}**")
                                gap_pct = ((target_mean - val) / val) * 100.0
                                st.write(f"- **{T['gap_line1']}:** `${val:.2f}` | **{T['gap_line2']}:** `${target_mean:.2f}`")
                                st.write(f"- **{T['gap_line3']}:** `{gap_pct:+.1f}%` ({T['gap_desc_high']} {gap_pct:.1f}%)")

                                if gap_pct > 25.0 and rec_key in ["BUY", "STRONG_BUY"]:
                                    st.error(T['gap_alert_high'])
                                elif abs(gap_pct) <= 15.0:
                                    st.success(T['ws_match'])
                                elif gap_pct < -15.0:
                                    st.info(T['gap_alert_low'])

                    st.markdown(f"### {T['chart_title']}")
                    c_chart1, c_chart2 = st.columns(2)
                    with c_chart1:
                        with st.container(border=True):
                            st.markdown("**1-Year Candlestick (MA20 & MA50)**")
                            fig_candle = draw_pro_candlestick(engine.ticker)
                            if fig_candle:
                                st.plotly_chart(fig_candle, use_container_width=True)
                    with c_chart2:
                        with st.container(border=True):
                            st.markdown(f"**3-Year CAPM Regression (Blume β = {engine.beta:.2f} | Jensen's α = {engine.alpha_annual*100:+.1f}%/yr)**")
                            fig_beta = draw_beta_scatter(engine)
                            if fig_beta:
                                st.plotly_chart(fig_beta, use_container_width=True)
                            st.caption(T['beta_desc'])

                    st.markdown(f"### {T['glossary_title']}")
                    g1, g2, g3, g4 = st.columns(4)
                    with g1:
                        with st.container(border=True):
                            st.markdown(T['g_beta_title'])
                            st.caption(T['g_beta_desc'])
                    with g2:
                        with st.container(border=True):
                            st.markdown(T['g_growth_title'])
                            st.caption(T['g_growth_desc'])
                    with g3:
                        with st.container(border=True):
                            st.markdown(T['g_wacc_title'])
                            st.caption(T['g_wacc_desc'])
                    with g4:
                        with st.container(border=True):
                            st.markdown(T['g_fv_title'])
                            st.caption(T['g_fv_desc'])

            # ==========================================
            # TAB 2: 硬核财报排程 (Year 0 锚定历史真实资产负债表，Year 1-5 反映滑块冲击)
            # ==========================================
            with tab2:
                st.markdown("#### ⚙️ Hardcore 3-Statement Forecast (Real Balance Sheet NWC & Depreciation Engine)")
                tab2_desc = (
                    f"已自动从 `{engine.ticker}` 真实资产负债表与现金流量表反推历史基准参数（Year 0 严格锚定历史事实）："
                    f"**DSO={engine.hist_dso}天, DIO={engine.hist_dio}天, DPO={engine.hist_dpo}天, Capex={engine.hist_capex_pct:.1f}%**。"
                    if lang_key == "zh" else
                    f"Automatically initialized from `{engine.ticker}` balance sheet & cash flow statement (Year 0 strictly anchored to historical facts): "
                    f"**DSO={engine.hist_dso}d, DIO={engine.hist_dio}d, DPO={engine.hist_dpo}d, Capex={engine.hist_capex_pct:.1f}%**."
                )
                st.caption(tab2_desc)

                exp_title_t2 = "📖 【新手必读 / 核心参数调整指南】营运资本与资本开支 (点击展开)" if lang_key == "zh" else "📖 [Beginner's Guide] Working Capital & Capex Drivers (Click to Expand)"

                guide_t2_zh = """
                * **DSO (应收账款天数 - Days Sales Outstanding)**：衡量公司卖出产品后，客户平均需要多少天把现金付清。调大代表客户拖欠加剧（Year 1 现金流立刻承受 $\\Delta \\text{NWC}$ 抽血冲击）。
                * **DIO (存货天数 - Days Inventory Outstanding)**：衡量货物从生产出来到卖掉平均在仓库躺几天。调大代表存货积压。
                * **DPO (应付账款天数 - Days Payable Outstanding)**：公司平均多少天付钱给上游供应商。调大代表公司对供应链占款能力强（短期自由现金流变好）。
                * **Capex % of Revenue (资本开支占营收比例)**：每年拿多少比例收入买厂房、服务器等固定资产。扩产期调高，维护期调低。
                """
                guide_t2_en = """
                * **DSO (Days Sales Outstanding)**: Days to collect cash from customers after a sale. Higher DSO ties up working capital and immediately shocks Year 1 FCF via $\\Delta \\text{NWC}$.
                * **DIO (Days Inventory Outstanding)**: Days inventory sits in storage before sale. Higher DIO signals inventory buildup.
                * **DPO (Days Payable Outstanding)**: Days taken to pay suppliers. Higher DPO preserves short-term cash flow.
                * **Capex % of Revenue**: Percentage of revenue spent on PP&E/servers. Increase for heavy expansion phases.
                """

                with st.expander(exp_title_t2, expanded=False):
                    st.markdown(guide_t2_zh if lang_key == "zh" else guide_t2_en)

                with st.container(border=True):
                    st.markdown("**🔧 Operating Assumptions (Year 1 ~ Year 5 Forecast Drivers)**")
                    o_col1, o_col2, o_col3, o_col4 = st.columns(4)
                    dso = o_col1.number_input("Days Sales Outstanding (DSO)", value=int(engine.hist_dso), min_value=0, max_value=365, key=f"dso_{engine.ticker}")
                    dio = o_col2.number_input("Days Inventory Outstanding (DIO)", value=int(engine.hist_dio), min_value=0, max_value=365, key=f"dio_{engine.ticker}")
                    dpo = o_col3.number_input("Days Payable Outstanding (DPO)", value=int(engine.hist_dpo), min_value=0, max_value=365, key=f"dpo_{engine.ticker}")
                    capex_pct = o_col4.number_input("Capex as % of Revenue", value=float(engine.hist_capex_pct), min_value=0.5, max_value=50.0, step=0.5, key=f"capex_{engine.ticker}") / 100.0

                df_is = engine.build_hardcore_3_statement(dso, dio, dpo, capex_pct)

                if engine.val_dcf and engine.val_3stmt_dcf is not None:
                    wc_col1, wc_col2, wc_col3 = st.columns(3)
                    diff_3stmt = engine.val_3stmt_dcf - engine.val_dcf
                    diff_pct_3stmt = (diff_3stmt / engine.val_dcf * 100.0) if engine.val_dcf > 0 else 0.0
                    wc_col1.metric(
                        "基准线性衰减 DCF (Baseline DCF)" if lang_key == "zh" else "Baseline Fading DCF",
                        f"{engine.currency} {engine.val_dcf:.2f}"
                    )
                    wc_col2.metric(
                        "三表营运资本驱动 DCF (3-Stmt DCF)" if lang_key == "zh" else "3-Statement Dynamic DCF",
                        f"{engine.currency} {engine.val_3stmt_dcf:.2f}",
                        f"{diff_pct_3stmt:+.1f}% vs Baseline"
                    )
                    wc_col3.metric(
                        "预测供应链现金周期 (CCC = DSO+DIO-DPO)" if lang_key == "zh" else "Forecast Cash Conversion Cycle (CCC)",
                        f"{dso + dio - dpo} Days",
                        f"Year 0 Hist CCC: {engine.hist_dso + engine.hist_dio - engine.hist_dpo} Days",
                        delta_color="off"
                    )

                styled_df = df_is.copy()
                for col in styled_df.columns:
                    styled_df[col] = styled_df[col].apply(lambda x: f"{x:,.0f}" if isinstance(x, (int, float)) else x)

                st.dataframe(styled_df, use_container_width=True, height=320)

            # ==========================================
            # TAB 3: LBO (含收购溢价 Buyout Premium + 利息税盾 Tax Shield + PIK 实物付息)
            # ==========================================
            with tab3:
                st.markdown("#### 🏛️ Institutional LBO Model (with Acquisition Premium, Interest Tax Shield & PIK Debt)")
                tab3_desc = (
                    "此 PE 并购模型已与 Tab 2 硬核 UFCF 及第 5 年预测 EBITDA 100% 闭环联动，并内置 **利息抵税盾 (Interest Tax Shield)**、**收购控制权溢价 (Acquisition Premium)** 与 **现金流不足时的 PIK 利滚利机制**。"
                    if lang_key == "zh" else
                    "100% linked to Tab 2 UFCF & Year-5 EBITDA, incorporating **Interest Tax Shield**, **Acquisition Control Premium**, and **PIK (Payment-in-Kind) Interest Accrual** when FCF < After-Tax Interest."
                )
                st.caption(tab3_desc)

                exp_title_t3 = "📖 【新手必读 / PE 并购指南】什么是杠杆收购 (LBO)、利息税盾与 PIK？ (点击展开)" if lang_key == "zh" else "📖 [Beginner's Guide] LBO Mechanics, Tax Shield & PIK Interest (Click to Expand)"
                with st.expander(exp_title_t3, expanded=False):
                    if lang_key == "zh":
                        st.markdown("""
                        * **Acquisition Premium (私有化收购溢价)**：私募基金买断一家上市公司控制权时，通常需要比当前二级市场股价多付 **15% ~ 30%** 的溢价，全体股东才会投票同意退市。
                        * **Interest Tax Shield (利息税盾)**：LBO 借入的巨额并购贷款产生的利息可以在税前抵扣企业所得税（节税金额 = $\\text{Interest} \\times \\text{Tax Rate}$），从而加速现金流清扫还债（Cash Sweep）。
                        * **PIK (Payment-in-Kind 实物付息 / 利滚利)**：如果某一年经济恶化导致公司自由现金流连税后利息都付不起（$\\text{UFCF} < \\text{After-Tax Interest}$），未付清的利息差额会自动加进期末本金里利滚利。
                        * **IRR & MOIC**：顶级华尔街 PE 基金（如黑石、KKR）通常要求 5 年期 **IRR > 20%** 且 **MOIC > 2.5x** 才会扣动收购扳机。
                        """)
                    else:
                        st.markdown("""
                        * **Acquisition Premium**: Control premium (typically **15%–30%**) paid above current Enterprise Value to take a public company private.
                        * **Interest Tax Shield**: High LBO debt interest reduces taxable income ($\\text{Tax Shield} = \\text{Interest} \\times \\text{Tax Rate}$), accelerating debt paydown.
                        * **PIK (Payment-in-Kind) Interest**: If $\\text{UFCF} < \\text{After-Tax Interest}$ in a downturn, the unpaid interest shortfall is capitalized into the ending debt balance.
                        """)

                col_l1, col_l2, col_l3, col_l4 = st.columns(4)
                buyout_prem = col_l1.slider("Acquisition Premium (%)", 0, 50, 15, 5) / 100.0
                ltv = col_l2.slider("Debt Leverage (LTV %)", 30, 80, 60, 5) / 100.0
                int_rate = col_l3.slider("Debt Interest Rate (%)", 4.0, 15.0, 7.5, 0.5) / 100.0
                default_mult = float(np.clip(engine.ev / engine.ebitda if engine.ebitda > 0 else 10.0, 5.0, 25.0))
                exit_mult = col_l4.slider("Exit EV/EBITDA Multiple", 5.0, 25.0, round(default_mult * 2) / 2, 0.5)

                lbo_res = engine.run_lbo_model(ltv, int_rate, exit_mult, buyout_prem)

                c_res1, c_res2, c_res3, c_res4 = st.columns(4)
                c_res1.metric("Sponsor IRR (5-Year)", f"{lbo_res['IRR']*100:.1f}%", f"Buyout Prem: +{buyout_prem*100:.0f}%", delta_color="off")
                c_res2.metric("MOIC (Cash-on-Cash)", f"{lbo_res['MOIC']:.2f}x")
                c_res3.metric("Net Debt Paid Down", f"{engine.currency} {(lbo_res['Debt'] - lbo_res['Exit Debt'])/1e9:.2f}B")
                c_res4.metric("5Y Cumulative Tax Shield", f"{engine.currency} {lbo_res['Total Tax Shield']/1e9:.2f}B", f"Tax Rate: {engine.tax*100:.1f}%", delta_color="off")

                st.markdown("**Sources & Uses (Entry with Control Premium)**")
                su_df = pd.DataFrame({
                    "Sources & Uses": [
                        "Current Spot EV (0% Premium)",
                        f"Acquisition Control Premium (+{buyout_prem*100:.0f}%)",
                        "Total Buyout Purchase EV",
                        "Sponsor Equity Contribution",
                        "Senior LBO Debt Issued"
                    ],
                    "Amount": [
                        f"{engine.ev:,.0f}",
                        f"{(lbo_res['Entry EV'] - engine.ev):,.0f}",
                        f"{lbo_res['Entry EV']:,.0f}",
                        f"{lbo_res['Equity']:,.0f}",
                        f"{lbo_res['Debt']:,.0f}"
                    ],
                    "% of Deal": [
                        f"{(engine.ev / lbo_res['Entry EV'] * 100):.1f}%" if lbo_res['Entry EV'] > 0 else "0%",
                        f"{((lbo_res['Entry EV'] - engine.ev) / lbo_res['Entry EV'] * 100):.1f}%" if lbo_res['Entry EV'] > 0 else "0%",
                        "100.0%",
                        f"{(1-ltv)*100:.1f}%",
                        f"{ltv*100:.1f}%"
                    ]
                })
                st.table(su_df)

                st.markdown("**Institutional Debt Schedule, Interest Tax Shield & PIK Accrual**")
                debt_df = pd.DataFrame({
                    "Year": ["0 (Entry)", "1", "2", "3", "4", "5"],
                    "Ending Debt Balance": [f"{x:,.0f}" for x in lbo_res['Debt Schedule'][:6]],
                    "Gross Interest": ["—"] + [f"{x:,.0f}" for x in lbo_res['Interest Schedule'][-5:]],
                    "Interest Tax Shield (+)": ["—"] + [f"{x:,.0f}" for x in lbo_res['Tax Shield Schedule'][-5:]],
                    "PIK Interest Capitalized": ["—"] + [f"{x:,.0f}" for x in lbo_res['PIK Schedule'][-5:]]
                })
                st.table(debt_df.set_index('Year').T)

            # ==========================================
            # TAB 4, 5, 6 (同业隐含估值反哺 + 跨国日历对齐 + MDD/VaR/CVaR)
            # ==========================================
            with tab4:
                comp_title = "#### 🏢 相对估值矩阵与同业隐含股价 (Parallel Peer Comps & Implied Valuation)" if lang_key == "zh" else "#### 🏢 Comparable Company Analysis & Peer-Implied Share Price"
                st.markdown(comp_title)
                comps_df = engine.run_comps_analysis()
                cs = getattr(engine, "comps_summary", {}) or {}
                if cs:
                    cp1, cp2, cp3, cp4 = st.columns(4)
                    cp1.metric(
                        "同业中位数 P/E (Peer Median)" if lang_key == "zh" else "Peer Median P/E",
                        f"{cs.get('peer_median_pe', 0):.2f}x",
                        f"Mean: {cs.get('peer_mean_pe', 0):.2f}x",
                        delta_color="off"
                    )
                    cp2.metric(
                        "同业中位数 EV/EBITDA" if lang_key == "zh" else "Peer Median EV/EBITDA",
                        f"{cs.get('peer_median_ev_ebitda', 0):.2f}x",
                        f"Mean: {cs.get('peer_mean_ev_ebitda', 0):.2f}x",
                        delta_color="off"
                    )
                    imp_pe_p = cs.get("implied_price_pe", 0.0)
                    imp_pe_diff = ((imp_pe_p - engine.price) / engine.price * 100.0) if (imp_pe_p > 0 and engine.price > 0) else 0.0
                    cp3.metric(
                        "同业 P/E 隐含公允股价" if lang_key == "zh" else "Implied Price (Peer P/E)",
                        f"{engine.currency} {imp_pe_p:.2f}" if imp_pe_p > 0 else "N/A",
                        f"{imp_pe_diff:+.1f}% vs Spot" if imp_pe_p > 0 else "EPS <= 0"
                    )
                    imp_ev_p = cs.get("implied_price_ev_ebitda", 0.0)
                    imp_ev_diff = ((imp_ev_p - engine.price) / engine.price * 100.0) if (imp_ev_p > 0 and engine.price > 0) else 0.0
                    cp4.metric(
                        "同业 EV/EBITDA 隐含股价" if lang_key == "zh" else "Implied Price (Peer EV/EBITDA)",
                        f"{engine.currency} {imp_ev_p:.2f}" if imp_ev_p > 0 else "N/A",
                        f"{imp_ev_diff:+.1f}% vs Spot" if imp_ev_p > 0 else "EBITDA <= 0"
                    )
                    st.caption(
                        "💡 **反哺闭环说明**：上方算出的【同业中位数 P/E】与【同业隐含股价区间】已自动反哺至 **Tab 1 的 P/E 倍数估值卡片** 与 **估值足球场图 (Football Field)** 中，彻底告别写死的固定行业倍数！"
                        if lang_key == "zh" else
                        "💡 **Closed-Loop Feedback**: The Peer Median P/E and Implied Share Price range above are automatically fed back into Tab 1's P/E Valuation Card and Football Field chart."
                    )
                st.dataframe(comps_df, use_container_width=True)

            with tab5:
                mc_title = "#### 🎲 蒙特卡洛估值模拟 (2,000次随机漫步)" if lang_key == "zh" else "#### 🎲 Monte Carlo Valuation Simulation (2,000 Iterations)"
                st.markdown(mc_title)
                mc_results = engine.run_monte_carlo(2000)
                if mc_results:
                    mc_mean = float(np.mean(mc_results))
                    mc_p10, mc_p90 = np.percentile(mc_results, [10, 90])
                    mc1, mc2, mc3 = st.columns(3)

                    mc1.metric("Monte Carlo Mean Value" if lang_key == "en" else "蒙特卡洛均值公道价", f"{engine.currency} {mc_mean:.2f}")
                    mc2.metric("10% Bear Case (Floor)" if lang_key == "en" else "10% 最差情况底线", f"{engine.currency} {mc_p10:.2f}")
                    mc3.metric("90% Bull Case (Ceiling)" if lang_key == "en" else "90% 极佳情况上限", f"{engine.currency} {mc_p90:.2f}")

                    fig_mc = px.histogram(
                        x=mc_results, nbins=50,
                        title="Intrinsic Value Probability Distribution" if lang_key == "en" else "内在价值概率分布图",
                        labels={'x': f'Fair Value ({engine.currency})', 'y': 'Frequency'}
                    )
                    fig_mc.add_vline(x=engine.price, line_dash="dash", line_color="#facc15", annotation_text=f"Spot: {engine.price:.2f}")
                    fig_mc.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#94a3b8'))
                    st.plotly_chart(fig_mc, use_container_width=True)

            with tab6:
                st.markdown("#### 📈 Markowitz Efficient Frontier, Bridgewater Risk Parity (ERC) & Macro Stress Testing Engine (V13.0)")
                exp_title_t6 = "📖 【新手必读 / 现代投资组合理论】SLSQP 切点组合、桥水风险平价 (ERC) 与尾部风险 VaR/CVaR (点击展开)" if lang_key == "zh" else "📖 [Beginner's Guide] SLSQP Tangency, Bridgewater Risk Parity (ERC) & Tail Risk VaR/CVaR (Click to Expand)"
                with st.expander(exp_title_t6, expanded=False):
                    if lang_key == "zh":
                        st.markdown("""
                        * **SLSQP 精确解析切点组合 (黄色五角星 ⭐)**：使用 `scipy.optimize.minimize` 二次规划直接求解资本市场线 (CML) 与有效前沿的精确切点，即**全局最大夏普比率组合 (Max Sharpe)**。
                        * **桥水“全天候”风险平价组合 Risk Parity / ERC (紫色六芒星 🟣)**：马科维茨模型容易将 90% 资金押注在单一高动量股票上；而**风险平价 (Equal Risk Contribution, ERC)** 强制让每只资产对组合总波动率的风险贡献度完全相等 ($RC_i = w_i (\\Sigma w)_i / \\sigma_p = \\sigma_p / N$)，实现真正的机构级全天候抗跌配置！
                        * **全局最小方差组合 GMV (绿色菱形 💎)**：纯粹将投资组合波动率降到全市场最低的防御型配比。
                        * **跨国交易日历无时区对齐 (`tz_localize(None)` + `.ffill().dropna()`)**：当您把马股（`.KL`）与美股混在一个篮子时，系统会自动剥离多重索引与时区差异并对齐跨国节假日。
                        """)
                    else:
                        st.markdown("""
                        * **SLSQP Tangency Portfolio (Yellow Star ⭐)**: Analytical quadratic programming solution maximizing the Sharpe Ratio along the Capital Market Line (CML).
                        * **Bridgewater Risk Parity / Equal Risk Contribution (Purple Star 🟣)**: Balances portfolio weights so every asset contributes an equal share of total portfolio risk ($RC_i = \\sigma_p / N$).
                        * **Global Minimum Variance (Green Diamond 💎)**: Portfolio weights minimizing annualized volatility.
                        * **Tail Risk & Macro Stress Test**: Measures historical MDD, 95% Daily VaR, 95% CVaR, and 4 extreme macro/geopolitical shock scenarios.
                        """)

                basket_input = st.text_input(
                    "Asset Basket Tickers (Comma-separated)",
                    value="NVDA, AAPL, MSFT, GOOGL, AMZN" if not engine.is_malaysia else "1155.KL, 1023.KL, 1295.KL, 5819.KL"
                )
                tickers_list = [t.strip().upper() for t in basket_input.split(",") if t.strip()]

                has_kl = any(t.endswith(".KL") for t in tickers_list)
                has_us = any(not t.endswith(".KL") for t in tickers_list)
                if has_kl and has_us:
                    st.info(
                        "🌏 **跨境多市场组合提示**：检测到您的资产篮子同时包含 **马股 (MYR)** 与 **美股 (USD)**。系统已自动剥离时区冲突并启用 `.ffill().dropna()` 跨国节假日日历对齐算法。"
                        if lang_key == "zh" else
                        "🌏 **Cross-Border Portfolio Notice**: Mixed MYR (`.KL`) and USD tickers detected. Timezones are stripped and trading calendars are aligned via `.ffill().dropna()`."
                    )

                if st.button("🚀 Run SLSQP, Risk Parity (ERC) & Monte Carlo Optimization" if lang_key == "en" else "🚀 运行 SLSQP 最大夏普 + 桥水风险平价 (ERC) + 蒙特卡洛优化"):
                    with st.spinner("Solving SLSQP Tangency, Bridgewater Risk Parity (ERC) & Tail Risk..." if lang_key == "en" else "正在求解 SLSQP 切点组合、桥水风险平价 (ERC) 权重与尾部风险..."):
                        try:
                            data = fetch_portfolio_history(tuple(tickers_list))
                            valid_cols = [c for c in tickers_list if c in data.columns and data[c].notna().sum() > 20]
                            data = data[valid_cols].ffill().dropna()
                            if data.empty or len(valid_cols) < 2:
                                st.warning("⚠️ Please enter at least 2 valid tickers with overlapping trading history.")
                            else:
                                returns = data.pct_change().dropna()
                                num_portfolios = 3000
                                n_assets = len(valid_cols)
                                mean_returns = returns.mean().values * 252.0
                                cov_matrix = returns.cov().values * 252.0

                                rng = np.random.default_rng(42)
                                weights_mat = rng.dirichlet(np.ones(n_assets), size=num_portfolios)

                                p_rets = weights_mat @ mean_returns
                                p_vols = np.sqrt(np.einsum('ij,jk,ik->i', weights_mat, cov_matrix, weights_mat))
                                sharpes = (p_rets - engine.rf) / np.maximum(p_vols, 1e-6)

                                init_w = np.ones(n_assets) / n_assets
                                bounds = tuple((0.0, 1.0) for _ in range(n_assets))
                                constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0},)

                                def neg_sharpe(w):
                                    ret = float(np.dot(w, mean_returns))
                                    vol = float(np.sqrt(np.dot(w.T, np.dot(cov_matrix, w))))
                                    return -(ret - engine.rf) / max(vol, 1e-6)

                                def port_vol(w):
                                    return float(np.sqrt(np.dot(w.T, np.dot(cov_matrix, w))))

                                # 🌟 V13.0 优化点 B：求解桥水“黑色曼巴”风险平价模型 (Risk Parity / Equal Risk Contribution, ERC)
                                def erc_obj(w):
                                    w_arr = np.asarray(w, dtype=float)
                                    vol = max(float(np.sqrt(np.dot(w_arr.T, np.dot(cov_matrix, w_arr)))), 1e-8)
                                    mrc = np.dot(cov_matrix, w_arr) / vol
                                    rc = w_arr * mrc
                                    target_rc = vol / float(n_assets)
                                    return float(np.sum((rc - target_rc) ** 2)) * 1000.0

                                res_sharpe = sco.minimize(neg_sharpe, init_w, method='SLSQP', bounds=bounds, constraints=constraints)
                                res_gmv = sco.minimize(port_vol, init_w, method='SLSQP', bounds=bounds, constraints=constraints)
                                erc_bounds = tuple((0.01, 1.0) for _ in range(n_assets))
                                res_erc = sco.minimize(erc_obj, init_w, method='SLSQP', bounds=erc_bounds, constraints=constraints)

                                if res_sharpe.success:
                                    opt_weights = res_sharpe.x
                                    opt_ret = float(np.dot(opt_weights, mean_returns))
                                    opt_vol = port_vol(opt_weights)
                                    opt_sr = (opt_ret - engine.rf) / max(opt_vol, 1e-6)
                                else:
                                    max_sharpe_idx = int(np.argmax(sharpes))
                                    opt_weights = weights_mat[max_sharpe_idx]
                                    opt_ret = float(p_rets[max_sharpe_idx])
                                    opt_vol = float(p_vols[max_sharpe_idx])
                                    opt_sr = float(sharpes[max_sharpe_idx])

                                gmv_w = res_gmv.x if res_gmv.success else weights_mat[int(np.argmin(p_vols))]
                                gmv_ret = float(np.dot(gmv_w, mean_returns))
                                gmv_vol = port_vol(gmv_w)

                                # 逆波动率加权作为 ERC 求解器的稳健解析后备
                                inv_vol_raw = 1.0 / np.maximum(np.sqrt(np.diag(cov_matrix)), 1e-6)
                                inv_vol_w = inv_vol_raw / np.sum(inv_vol_raw)
                                erc_w = (res_erc.x / np.sum(res_erc.x)) if (res_erc.success and np.sum(res_erc.x) > 0) else inv_vol_w
                                erc_ret = float(np.dot(erc_w, mean_returns))
                                erc_vol = port_vol(erc_w)
                                erc_sr = (erc_ret - engine.rf) / max(erc_vol, 1e-6)

                                # 📐 计算最优切点组合的每日序列、历史最大回撤 (MDD)、95% VaR 与 95% CVaR
                                port_daily_rets = returns.values @ opt_weights
                                cum_wealth = np.cumprod(1.0 + port_daily_rets)
                                peak_wealth = np.maximum.accumulate(cum_wealth)
                                port_mdd = float(np.min((cum_wealth - peak_wealth) / np.maximum(peak_wealth, 1e-9))) * 100.0
                                port_var_95 = float(np.percentile(port_daily_rets, 5)) * 100.0
                                tail_losses = port_daily_rets[port_daily_rets <= np.percentile(port_daily_rets, 5)]
                                port_cvar_95 = float(np.mean(tail_losses)) * 100.0 if len(tail_losses) > 0 else port_var_95

                                opt1, opt2, opt3, opt4 = st.columns(4)
                                opt1.metric("Max Sharpe Return", f"{opt_ret*100:.2f}%", f"Vol: {opt_vol*100:.2f}%", delta_color="off")
                                opt2.metric("SLSQP Max Sharpe Ratio", f"{opt_sr:.2f}")
                                opt3.metric("Risk Parity (ERC) Return", f"{erc_ret*100:.2f}%", f"ERC Vol: {erc_vol*100:.2f}%", delta_color="off")
                                opt4.metric("Risk Parity (ERC) Sharpe", f"{erc_sr:.2f}", "Equal Risk Contrib.", delta_color="off")

                                tr1, tr2, tr3 = st.columns(3)
                                tr1.metric("1Y Max Drawdown (MDD)", f"{port_mdd:.2f}%", "Peak-to-Trough" if lang_key == "en" else "最大历史回撤", delta_color="off")
                                tr2.metric("95% Daily VaR (在险价值)", f"{port_var_95:.2f}%", "95% Confidence Daily Floor", delta_color="off")
                                tr3.metric("95% Daily CVaR (期望尾部亏损)", f"{port_cvar_95:.2f}%", "Expected Shortfall (Black Swan)", delta_color="off")

                                weight_df = pd.DataFrame({
                                    "Asset": valid_cols,
                                    "Max Sharpe Weight (%)": [f"{w*100:.1f}%" for w in opt_weights],
                                    "Min Variance (GMV) Weight (%)": [f"{w*100:.1f}%" for w in gmv_w],
                                    "Bridgewater Risk Parity (ERC %)": [f"{w*100:.1f}%" for w in erc_w]
                                })
                                st.table(weight_df.set_index('Asset').T)

                                fig_ef = px.scatter(
                                    x=p_vols, y=p_rets, color=sharpes,
                                    labels={'x': 'Volatility (Annualized Risk)', 'y': 'Expected Annual Return', 'color': 'Sharpe Ratio'},
                                    title="Markowitz Efficient Frontier, Capital Market Line & Bridgewater Risk Parity (ERC)"
                                )
                                fig_ef.add_trace(go.Scatter(
                                    x=[opt_vol], y=[opt_ret],
                                    mode='markers', marker=dict(color='#facc15', size=16, symbol='star'),
                                    name='SLSQP Max Sharpe (Tangency)'
                                ))
                                fig_ef.add_trace(go.Scatter(
                                    x=[gmv_vol], y=[gmv_ret],
                                    mode='markers', marker=dict(color='#10b981', size=13, symbol='diamond'),
                                    name='Global Min Variance (GMV)'
                                ))
                                fig_ef.add_trace(go.Scatter(
                                    x=[erc_vol], y=[erc_ret],
                                    mode='markers', marker=dict(color='#c084fc', size=15, symbol='hexagram'),
                                    name='Bridgewater Risk Parity (ERC)'
                                ))
                                cml_x = np.linspace(0.0, float(np.max(p_vols)) * 1.05, 100)
                                cml_y = engine.rf + opt_sr * cml_x
                                fig_ef.add_trace(go.Scatter(
                                    x=cml_x, y=cml_y, mode='lines',
                                    line=dict(color='#38bdf8', width=2, dash='dash'),
                                    name=f'Capital Market Line (Rf={engine.rf*100:.2f}%)'
                                ))
                                fig_ef.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#94a3b8'))
                                st.plotly_chart(fig_ef, use_container_width=True)
                        except Exception as e:
                            st.error(f"Error fetching basket data: {e}")

                # 🌟 V13.0 降维打击模块 3：多资产宏观与地缘政治黑天鹅压力测试引擎 (Macro Stress Test)
                st.markdown("---")
                st.markdown(
                    "##### 🌪️ 宏观与地缘政治黑天鹅压力测试引擎 (Multi-Asset Macroeconomic & Geopolitical Stress Test)"
                    if lang_key == "zh" else
                    "##### 🌪️ Multi-Asset Macroeconomic & Geopolitical Stress Testing Engine"
                )
                st.caption(
                    "模拟美联储意外加息 (+50bps)、中东地缘危机原油暴涨 (+30%)、大盘流动性闪崩 (-15%) 与 VIX 恐慌飙升 (+50%) 下的组合净值冲击与压力 VaR 倍增效应。"
                    if lang_key == "zh" else
                    "Simulates portfolio drawdown and Stressed 95% VaR expansion under 4 extreme macroeconomic and geopolitical shock scenarios."
                )
                stress_notional = st.number_input(
                    "压力测试组合本金规模 (Portfolio Notional for Stress Test)" if lang_key == "zh" else "Portfolio Notional Value",
                    value=100000.0, step=25000.0, key=f"stress_notional_{engine.ticker}"
                )
                stress_df = engine.run_macro_stress_test(portfolio_val=stress_notional, port_beta=engine.beta)
                disp_col = "Scenario_ZH" if lang_key == "zh" else "Scenario_EN"
                show_stress = stress_df[[disp_col, "Macro Trigger", "Stressed Drawdown (%)", "Portfolio P&L Impact", "Post-Shock Equity", "Stressed Daily 95% VaR"]].rename(columns={disp_col: "Stress Scenario"})
                st.dataframe(show_stress, use_container_width=True)

            # ==========================================
            # TAB 7: 期权链与 B-S 沙盘 (含 Mid-Price 过滤、Brentq IV 反解器、8大策略沙盘、PoP 胜率与动态 Delta 对冲模拟器)
            # ==========================================
            with tab7:
                st.markdown("#### 📉 Options Chain, Brentq IV Solver, 8-Strategy Sandbox & Dynamic Delta-Hedging Simulator (V13.0)")
                if engine.is_malaysia:
                    st.warning("⚠️ 马股（Bursa Malaysia）期权数据在 Yahoo Finance 上极度稀疏。建议切换至美股代码（如 NVDA, AAPL, TSLA）体验完整期权链！" if lang_key == "zh" else "⚠️ Bursa Malaysia options data is sparse on Yahoo Finance. Switch to US tickers (e.g., NVDA, AAPL) for live option chains.")

                try:
                    exp_dates = fetch_option_expirations(engine.ticker)
                    if exp_dates:
                        selected_expiry = st.selectbox("📅 选择期权到期日 (Select Expiration Date)" if lang_key == "zh" else "📅 Select Expiration Date", options=exp_dates)
                        calls, puts = fetch_option_chain_df(engine.ticker, selected_expiry)

                        exp_dt = datetime.datetime.strptime(selected_expiry, "%Y-%m-%d")
                        T_days = max((exp_dt - datetime.datetime.now()).days, 1)
                        T_years = max(T_days / 365.0, 1.0 / 365.0)
                        r = engine.rf
                        S = engine.price
                        div_rate_opt = float(engine.info.get('dividendRate') or engine.info.get('trailingAnnualDividendRate') or 0.0)
                        q_yield = (div_rate_opt / S) if S > 0 else 0.0

                        opt_tab1, opt_tab2, opt_tab3 = st.tabs([
                            "📈 隐含波动率微笑 (Volatility Smile)" if lang_key == "zh" else "📈 Volatility Smile / Skew",
                            "🛡️ 实时平值期权链 (Mid-Price & Brentq IV 反解)" if lang_key == "zh" else "🛡️ Live ATM Option Chain (Mid-Price & Brentq IV)",
                            "🧮 B-S 沙盘、8 大策略与动态 Delta 对冲 (Gamma Scalping)" if lang_key == "zh" else "🧮 BS Sandbox, 8-Strategy & Dynamic Delta-Hedging"
                        ])

                        with opt_tab1:
                            fig_smile = go.Figure()
                            if not calls.empty and 'impliedVolatility' in calls.columns:
                                valid_calls = calls[(calls['impliedVolatility'] > 0.01) & (calls['impliedVolatility'] < 3.0)]
                                fig_smile.add_trace(go.Scatter(x=valid_calls['strike'], y=valid_calls['impliedVolatility']*100, mode='markers+lines', name='Calls IV (%)', marker=dict(color='#38bdf8', size=6)))
                            if not puts.empty and 'impliedVolatility' in puts.columns:
                                valid_puts = puts[(puts['impliedVolatility'] > 0.01) & (puts['impliedVolatility'] < 3.0)]
                                fig_smile.add_trace(go.Scatter(x=valid_puts['strike'], y=valid_puts['impliedVolatility']*100, mode='markers+lines', name='Puts IV (%)', marker=dict(color='#ef4444', size=6)))
                            fig_smile.add_vline(x=S, line_dash="dash", line_color="yellow", annotation_text=f"Spot: ${S:.2f}")
                            fig_smile.update_layout(xaxis_title="Strike Price ($) ➡️", yaxis_title="Implied Volatility (%) ⬇️", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#94a3b8'), height=380)
                            st.plotly_chart(fig_smile, use_container_width=True)

                        with opt_tab2:
                            st.caption(
                                "💡 **量化级僵尸价格过滤与 Brentq IV 反解**：优先采用实时买卖盘中间价 `Mid = (Bid + Ask)/2`；当非交易时段 Yahoo 返回 `IV <= 1.5%` 或深度实值无解时，自动调用零崩溃加固版 `scipy.optimize.brentq` 反推真实隐含波动率！"
                                if lang_key == "zh" else
                                "💡 **Stale Price Filter & Brentq IV Solver**: Prioritizes `Mid = (Bid + Ask)/2` and backs out true Black-Scholes IV via exception-safe `scipy.optimize.brentq`."
                            )
                            opt_type_sel = st.radio(
                                "选择期权类型 (Option Type)" if lang_key == "zh" else "Select Option Type",
                                options=["Calls (看涨期权)", "Puts (看跌期权)"],
                                horizontal=True
                            )
                            is_call_view = opt_type_sel.startswith("Calls")
                            active_df = calls if is_call_view else puts
                            if not active_df.empty:
                                near_idx = (active_df['strike'] - S).abs().argsort()[:15]
                                sample_opts = active_df.iloc[near_idx].sort_values('strike').copy()
                                bs_results = []
                                for _, row in sample_opts.iterrows():
                                    K = float(row['strike'])
                                    bid_v = float(row.get('bid') or 0.0) if pd.notna(row.get('bid')) else 0.0
                                    ask_v = float(row.get('ask') or 0.0) if pd.notna(row.get('ask')) else 0.0
                                    last_v = float(row.get('lastPrice') or 0.0) if pd.notna(row.get('lastPrice')) else 0.0
                                    mid_v = 0.5 * (bid_v + ask_v) if (bid_v > 0 and ask_v > 0) else last_v
                                    vol_v = int(row.get('volume') or 0) if pd.notna(row.get('volume')) else 0
                                    oi_v = int(row.get('openInterest') or 0) if pd.notna(row.get('openInterest')) else 0

                                    raw_iv = float(row.get('impliedVolatility') or 0.0) if pd.notna(row.get('impliedVolatility')) else 0.0
                                    if raw_iv > 0.015:
                                        iv = raw_iv
                                        iv_src = "Exchange"
                                    else:
                                        iv, iv_src = engine.solve_implied_volatility(mid_v, S, K, T_years, r, q=q_yield, is_call=is_call_view, fallback_iv=0.35)

                                    greeks = engine.black_scholes_pricing(S, K, T_years, r, iv, q=q_yield)
                                    bs_results.append({
                                        "Strike": K,
                                        "Moneyness": "ATM" if abs(K - S) / S < 0.02 else ("ITM" if (K < S if is_call_view else K > S) else "OTM"),
                                        "Mid Price": round(mid_v, 2),
                                        "Bid / Ask": f"{bid_v:.2f} / {ask_v:.2f}",
                                        "Last": round(last_v, 2),
                                        "BS Model Fair": round(greeks['Call' if is_call_view else 'Put'], 2),
                                        "IV (%)": round(iv * 100, 1),
                                        "IV Source": iv_src,
                                        "Volume": vol_v,
                                        "Open Int": oi_v,
                                        "Delta": round(greeks['Delta_C' if is_call_view else 'Delta_P'], 3),
                                        "Gamma": round(greeks['Gamma'], 4),
                                        "Theta (Daily)": round(greeks['Theta_C' if is_call_view else 'Theta_P'], 3),
                                        "Vega": round(greeks['Vega'], 3)
                                    })
                                st.dataframe(pd.DataFrame(bs_results), use_container_width=True)

                        with opt_tab3:
                            with st.expander("📖 【新手必读 / 希腊字母百科】Delta, Gamma, Theta, Vega 与 Gamma Scalping 实战含义 (点击展开)" if lang_key == "zh" else "📖 [Beginner's Guide] Option Greeks & Gamma Scalping Explained (Click to Expand)", expanded=False):
                                st.markdown(
                                    r"""
                                    * **Delta ($\Delta$)**：正股每涨 \$1，期权价格涨多少。做市商通过反向买卖 $-\Delta \times 100$ 股正股实现 **Delta-Neutral ($\Delta_{\text{net}} = 0$)**。
                                    * **Gamma ($\Gamma$) 与 Gamma Scalping**：正股每变动 \$1，Delta 变动多少。持有正 Gamma（如买入跨式 Straddle）的机构在股价大涨时高抛正股、大跌时低吸正股，把波动率转化为真金白银，这叫 **Gamma Scalping**！
                                    * **Theta ($\Theta$)**：每天流逝的时间价值。Gamma Scalping 的核心博弈就是让每日高抛低吸赚取的 Gamma 收益大于每日流逝的 Theta 成本。
                                    * **Vega ($\mathcal{V}$)**：隐含波动率 (IV) 每变动 1%，期权价格变动多少。
                                    """
                                    if lang_key == "zh" else
                                    r"""
                                    * **Delta ($\Delta$)**: Option price change per \$1 move in spot price. Market makers trade $-\Delta \times 100$ shares to stay **Delta-Neutral ($\Delta_{\text{net}} = 0$)**.
                                    * **Gamma ($\Gamma$) & Gamma Scalping**: Rate of change of Delta. Long-Gamma traders buy low and sell high as spot oscillates to harvest realized volatility against daily **Theta ($\Theta$)** decay.
                                    """
                                )
                            op_col1, op_col2, op_col3 = st.columns(3)
                            strike_pct = op_col1.slider("行权价设定 (% 相对现价)" if lang_key == "zh" else "Strike Price Setting (%)", 80, 120, 100, 1) / 100.0
                            custom_K = op_col2.number_input("行权价 (Strike K)" if lang_key == "zh" else "Strike (K)", value=float(engine.price * strike_pct), format="%.2f")
                            custom_T_days = op_col3.number_input("剩余到期天数 (Days to Maturity)" if lang_key == "zh" else "Days to Maturity", value=30, min_value=1, max_value=730)

                            op_col4, op_col5, op_col6 = st.columns(3)
                            custom_vol = op_col4.slider("波动率 (Volatility σ %)" if lang_key == "zh" else "Volatility (IV σ %)", 10.0, 150.0, 35.0, 1.0) / 100.0
                            custom_r_rate = op_col5.slider("无风险利率 (Risk-Free Rate r %)" if lang_key == "zh" else "Risk-Free Rate (r %)", 1.0, 10.0, float(engine.rf * 100), 0.1) / 100.0
                            custom_div_yield = op_col6.slider("股息率 (Dividend Yield q %)" if lang_key == "zh" else "Dividend Yield (q %)", 0.0, 10.0, 1.5, 0.1) / 100.0

                            custom_greeks = engine.black_scholes_pricing(engine.price, custom_K, custom_T_days / 365.0, custom_r_rate, custom_vol, custom_div_yield)
                            res_c1, res_c2, res_c3, res_c4 = st.columns(4)
                            res_c1.metric("European Call (看涨公道价)", f"{engine.currency} {custom_greeks['Call']:.4f}", f"Delta: {custom_greeks['Delta_C']:+.3f}", delta_color="off")
                            res_c2.metric("European Put (看跌公道价)", f"{engine.currency} {custom_greeks['Put']:.4f}", f"Delta: {custom_greeks['Delta_P']:+.3f}", delta_color="off")
                            res_c3.metric("Gamma / Vega (每1% IV)", f"{custom_greeks['Gamma']:.4f}", f"Vega: {custom_greeks['Vega']:.3f}", delta_color="off")
                            res_c4.metric("Daily Theta (每日时间损耗)", f"Call: {custom_greeks['Theta_C']:.3f}", f"Put: {custom_greeks['Theta_P']:.3f}", delta_color="off")

                            st.markdown("---")
                            st.markdown("##### 🎯 8 大机构期权策略交互式沙盘 (含精确盈亏平衡点 Breakevens & 几何布朗运动到期胜率 PoP %)")
                            sim_strat_map = {
                                "Cash-Secured Put (现金担保卖看跌 - 巴菲特折价接货)": "cash_secured_put",
                                "Bull Call Spread (牛市看涨垂直价差 - 防 IV Crush)": "bull_call_spread",
                                "Covered Call (备兑看涨期权 - 持股收租增强)": "covered_call",
                                "Collar (零成本领口保护 - 锁死下行风险)": "collar",
                                "Iron Condor (铁鹰跨式套利 - 震荡市收割 Theta)": "iron_condor",
                                "Bear Put Spread (熊市看跌垂直价差 - 防御做空)": "bear_put_spread",
                                "Protective Put (保护性看跌期权 - 现货保险单)": "protective_put",
                                "Long Straddle (买入跨式双买 - 押注超级变盘)": "straddle"
                            }
                            sel_sim_label = st.selectbox("选择要模拟的期权策略结构 (Select Option Strategy)", options=list(sim_strat_map.keys()))
                            sel_sim_key = sim_strat_map[sel_sim_label]
                            fig_sim, sim_mp, sim_ml, sim_stats = draw_option_payoff_diagram(
                                engine, sel_sim_key, custom_T_days / 365.0, custom_vol, lang_key, return_stats=True
                            )
                            be_list = sim_stats.get("breakevens", [])
                            be_str = " / ".join([f"{engine.currency}{b:.2f}" for b in be_list]) if be_list else "N/A"
                            sc1, sc2, sc3, sc4 = st.columns(4)
                            sc1.metric("🎯 策略到期盈利概率 (PoP %)", f"{sim_stats.get('pop_pct', 0.0):.1f}%", "GBM Lognormal Exact", delta_color="off")
                            sc2.metric("⚖️ 精确盈亏平衡点 (Breakevens)", be_str)
                            sc3.metric("🚀 单张最大潜在盈利 (100股)", f"{engine.currency} {sim_mp:,.0f}")
                            sc4.metric("🛡️ 单张最大潜在亏损 (100股)", f"{engine.currency} {sim_ml:,.0f}")
                            st.plotly_chart(fig_sim, use_container_width=True)

                            # 🌟 V13.0 降维打击模块 2：做市商动态 Delta 对冲与 Gamma Scalping 模拟器
                            st.markdown("---")
                            st.markdown(
                                "##### ⚡ 做市商动态 Delta-Neutral 对冲与 Gamma Scalping 模拟器 (Dynamic Delta-Hedging Desk)"
                                if lang_key == "zh" else
                                "##### ⚡ Institutional Dynamic Delta-Hedging & Gamma Scalping Simulator"
                            )
                            dh_contracts = st.slider(
                                "模拟持有期权合约张数 (Contracts Held, 1张=100股)" if lang_key == "zh" else "Option Contracts Held (x100 Multiplier)",
                                1, 50, 10, 1, key=f"dh_contracts_{engine.ticker}"
                            )
                            dh_res = engine.simulate_dynamic_delta_hedging(
                                K=custom_K, T_days=int(min(custom_T_days, 60)), sigma=custom_vol, contracts=dh_contracts
                            )
                            dh1, dh2, dh3, dh4 = st.columns(4)
                            dh1.metric(
                                f"Long {dh_contracts}x Call 初始对冲指令",
                                f"{dh_res['call_hedge_shares']:+d} 股正股",
                                "Target Δ_net = 0", delta_color="off"
                            )
                            dh2.metric(
                                f"Long {dh_contracts}x Straddle 初始对冲",
                                f"{dh_res['straddle_hedge_shares']:+d} 股正股",
                                f"1%股价波动调仓: ±{dh_res['gamma_1pct_rebalance']:.1f}股", delta_color="off"
                            )
                            dh3.metric(
                                "30D 累计 Gamma 高抛低吸收益",
                                f"{engine.currency} {dh_res['final_gamma_pnl']:+,.2f}",
                                f"Theta 损耗: {engine.currency} {dh_res['final_theta_pnl']:+,.2f}", delta_color="off"
                            )
                            dh4.metric(
                                "30D Delta-Neutral 净套利盈亏",
                                f"{engine.currency} {dh_res['final_net_pnl']:+,.2f}",
                                "Gamma P&L + Theta Decay", delta_color="off"
                            )
                            st.dataframe(dh_res["df"], use_container_width=True, height=250)
                    else:
                        st.info("ℹ️ 当前标的暂无交易所公开期权链，您可以直接前往 **Tab [8] TradingAgents 投委会与期权作战室** 使用合成 B-S 期权策略引擎！" if lang_key == "zh" else "ℹ️ No exchange-listed option chain found; visit Tab [8] for synthetic B-S option strategy modeling!")
                except Exception as e:
                    st.error(f"Option chain error: {e}")


            # ==================================================================
            # 🌟 TAB 8: TradingAgents 多智能体投委会辩论与期权协同作战室 (V13.0 宗师满血版)
            # ==================================================================
            with tab8:
                st.markdown(
                    "### 🤖 TradingAgents Multi-Agent Investment Committee & Options Desk (V13.0 Grandmaster Edition)"
                    if lang_key == "en" else
                    "### 🤖 TradingAgents 多智能体投委会辩论与期权作战室 (V13.0 量化宗师终极版)"
                )
                st.caption(
                    "完美复刻 TauricResearch/TradingAgents 五阶段工作流，搭载 GARCH(1,1) 动态条件异方差波动率、Beneish M-Score 财务造假侦测雷达、Beta 中性多空配对交易 (Pairs Trading)、半凯利公式 (Half-Kelly) 仓位管理与 Google Gemini 2.5 双向闭环裁决系统。"
                    if lang_key == "zh" else
                    "Mirrors the 5-stage TauricResearch/TradingAgents workflow with GARCH(1,1) Dynamic Volatility, Beneish M-Score Forensics Radar, Market-Neutral Long-Short Pairs Trading, Half-Kelly Sizing, and Google Gemini 2.5 Bidirectional Verdict Override."
                )

                with st.container(border=True):
                    st.markdown("**💼 账户持仓上下文设定 (Portfolio Context - 决定交易员与期权策略是【建仓】、【收租】还是【对冲保护】)**" if lang_key == "zh" else "**💼 Portfolio Context (Guides Trader & Options Desk Sizing/Hedging)**")
                    pc1, pc2, pc3 = st.columns(3)
                    user_cash = pc1.number_input("可用现金 (Free Cash)" if lang_key == "zh" else "Free Cash Available", value=100000.0, step=10000.0)
                    user_shares = pc2.number_input("当前持有正股股数 (填 ≥100 股将激活备兑/领型对冲)" if lang_key == "zh" else "Current Shares Held (≥100 unlocks Covered Call / Collar)", value=0, min_value=0, step=100)
                    debate_rounds = pc3.slider("多空与风控辩论深度 (Debate Rounds)" if lang_key == "zh" else "Debate Rounds", 1, 3, 2)

                pipe = engine.run_trading_agents_pipeline(user_cash, user_shares, lang_key)
                tech = pipe["tech"]
                opt_info = pipe["opt_info"]
                beneish = pipe.get("beneish") or engine.compute_beneish_m_score()
                pair_info = pipe.get("pair_info") or {}

                # 财报日 IV Crush 横幅预警
                if opt_info.get("earnings_alert"):
                    st.warning(
                        f"⚡ **【财报日跨期波动率坍塌预警 (Earnings IV Crush Alert)】**：检测到 `{engine.ticker}` 将于 **{opt_info['earnings_date']}**（约 **{opt_info['days_to_earnings']} 天后**）发布财报，落在当前主力期权周期 (`{opt_info['expiry']}`) 内！"
                        f"平值跨式期权隐含财报波幅为 **±{opt_info['implied_move_pct']:.1f}%**。系统已自动规避裸买单腿期权与窄幅裸卖策略，优先采用价差（Spread）锁定风险！"
                    )

                # 🌟 V13.0 降维打击模块 1：Beneish M-Score 财务造假与盈余操纵侦测雷达横幅
                b_badge = beneish.get("badge_zh") if lang_key == "zh" else beneish.get("badge_en")
                if beneish.get("status") == "HIGH_RISK":
                    st.error(b_badge)
                elif beneish.get("status") == "GRAY_ZONE":
                    st.warning(b_badge)
                else:
                    st.success(b_badge)

                with st.expander("🔍 【Beneish M-Score 华尔街做空机构八因子财务侦测矩阵】查看详细拆解 (点击展开)" if lang_key == "zh" else "🔍 [Beneish M-Score 8-Factor Financial Forensics Matrix] (Click to Expand)", expanded=False):
                    b_comp = beneish.get("components", {})
                    bc1, bc2, bc3, bc4 = st.columns(4)
                    bc1.metric("Beneish M-Score", f"{beneish.get('m_score', -2.5):.2f}", "Threshold: -1.78", delta_color="off")
                    bc2.metric("Accruals Ratio (TATA)", f"{beneish.get('accruals_pct', 0.0):+.2f}%", "(Net Inc - OCF) / Assets", delta_color="off")
                    bc3.metric("DSRI (应收膨胀指数)", f"{b_comp.get('DSRI', 1.0):.2f}x", f"GMI (毛利恶化): {b_comp.get('GMI', 1.0):.2f}x", delta_color="off")
                    bc4.metric("SGI (营收扩张指数)", f"{b_comp.get('SGI', 1.0):.2f}x", f"LVGI (杠杆异动): {b_comp.get('LVGI', 1.0):.2f}x", delta_color="off")

                # --------------------------------------------------------------
                # STAGE 1: 四大分析师并行调研报告 (Parallel Analyst Team)
                # --------------------------------------------------------------
                st.markdown("#### 🔍 第一阶段：四大专业分析师并行调研 (Stage 1: Parallel Analyst Team)" if lang_key == "zh" else "#### 🔍 Stage 1: Parallel Analyst Team Reports")
                a_col1, a_col2, a_col3, a_col4 = st.columns(4)

                with a_col1:
                    with st.container(border=True):
                        st.markdown("<span class='agent-badge' style='background:rgba(56,189,248,0.2);color:#38bdf8;'>📈 MARKET ANALYST</span>", unsafe_allow_html=True)
                        st.markdown(f"**趋势判定:** `{tech['trend']}`")
                        st.markdown(
                            f"- **MA20 / MA50:** `{tech['ma20']:.2f}` / `{tech['ma50']:.2f}`\n"
                            f"- **RSI (14):** `{tech['rsi']:.1f}` ({'超买区' if tech['rsi']>70 else ('超卖区' if tech['rsi']<30 else '中性区')})\n"
                            f"- **GARCH(1,1) 动态波动率:** `{tech.get('garch_vol', tech['hv30'])*100:.1f}%` (HV30 `{tech['hv30']*100:.1f}%`)\n"
                            f"- **支撑 / 阻力位:** `{tech['support']:.2f}` / `{tech['resistance']:.2f}`\n"
                            f"- **1Y 最大回撤 (MDD):** `{tech.get('mdd_pct', 0.0):.1f}%`\n"
                            f"- **95% 日 VaR / CVaR:** `{tech.get('var_95_pct', 0.0):.2f}%` / `{tech.get('cvar_95_pct', 0.0):.2f}%`"
                        )

                with a_col2:
                    with st.container(border=True):
                        st.markdown("<span class='agent-badge' style='background:rgba(16,185,129,0.2);color:#10b981;'>📊 FUNDAMENTALS ANALYST</span>", unsafe_allow_html=True)
                        st.markdown(f"**主推模型:** `{engine.model_name[:18]}`")
                        st.markdown(
                            f"- **内在公允价:** `{engine.currency} {engine.fair_val:.2f}`\n"
                            f"- **安全边际 (MoS):** `{pipe['mos_pct']:+.1f}%`\n"
                            f"- **Beneish M-Score:** `{beneish.get('m_score', -2.5):.2f}` ({beneish.get('status', 'CLEAN')})\n"
                            f"- **三表真实 NWC DCF:** `{engine.currency} {(engine.val_3stmt_dcf or engine.fair_val):.2f}`\n"
                            f"- **同业 P/E 隐含股价:** `{engine.currency} {(engine.val_pe or engine.fair_val):.2f}`\n"
                            f"- **现金转换周期 (CCC):** `{engine.hist_dso + engine.hist_dio - engine.hist_dpo} 天`"
                        )

                with a_col3:
                    with st.container(border=True):
                        st.markdown("<span class='agent-badge' style='background:rgba(245,158,11,0.2);color:#f59e0b;'>📰 NEWS & SENTIMENT</span>", unsafe_allow_html=True)
                        st.markdown(f"**隐含增长率:** `{pipe['implied_g_pct']:.1f}% / 年`")
                        st.markdown(
                            f"- **华尔街目标均值:** `{engine.currency} {pipe['target_mean']:.2f}` ({pipe['ws_upside']:+.1f}%)\n"
                            f"- **年化 Jensen's α:** `{engine.alpha_annual*100:+.1f}% / 年`\n"
                            f"- **下一季财报日:** `{opt_info.get('earnings_date', 'N/A')}`\n"
                            f"- **最新头条监控:**\n" +
                            ("\n".join([f"  - *{ h[:48] }...*" for h in pipe["news"][:2]]) if pipe["news"] else "  - *暂无突发黑天鹅新闻*")
                        )

                with a_col4:
                    with st.container(border=True):
                        st.markdown("<span class='agent-badge' style='background:rgba(168,85,247,0.2);color:#c084fc;'>🎯 OPTIONS & VOL ANALYST</span>", unsafe_allow_html=True)
                        st.markdown(f"**主力合约:** `{opt_info['expiry']}`")
                        st.markdown(
                            f"- **平值隐含波动率 (IV):** `{opt_info['atm_iv']*100:.1f}%`\n"
                            f"- **GARCH(1,1) 预测波动率:** `{opt_info.get('garch_vol', tech['hv30'])*100:.1f}%` (`{tech.get('vol_regime', 'NORMAL')}`)\n"
                            f"- **IV / GARCH 溢价比:** `{opt_info['iv_hv_ratio']:.2f}x` ({'期权偏贵-宜卖方/价差' if opt_info['iv_hv_ratio']>=1.15 else '期权便宜-宜买方'})\n"
                            f"- **Put-Call 偏度 (Skew):** `{opt_info['skew']:+.1f}%`\n"
                            f"- **隐含预期波幅 (Straddle):** `±{opt_info.get('implied_move_pct', 0.0):.1f}%`"
                        )

                st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

                # --------------------------------------------------------------
                # STAGE 2: 多空研究员结构化辩论与研究总监裁决 (Bull vs Bear Debate)
                # --------------------------------------------------------------
                st.markdown("#### ⚔️ 第二阶段：多空研究员针锋相对辩论 & 研究总监裁决 (Stage 2: Bull vs. Bear Debate)" if lang_key == "zh" else "#### ⚔️ Stage 2: Bull vs. Bear Researcher Debate & Research Director")
                d_col1, d_col2 = st.columns(2)

                with d_col1:
                    bull_r1 = (
                        f"**[第一轮立论 - 估值与成长驱动]** 标的 `{engine.ticker}` 当前自由现金流造血能力强劲（FCF 达 `{engine.cf/1e9:.2f}B`）。"
                        f"在两阶段衰减模型下内在价值为 `{engine.currency} {engine.fair_val:.2f}`，三表动态 DCF 为 `{engine.currency} {(engine.val_3stmt_dcf or engine.fair_val):.2f}`，"
                        f"华尔街机构目标均值看向 `{engine.currency} {pipe['target_mean']:.2f}`（潜在空间 `{pipe['ws_upside']:+.1f}%`）。20日关键支撑位稳固在 `{tech['support']:.2f}`。"
                    )
                    bull_r2 = (
                        f"**[第二轮反驳空方 - 期权与现金流护城河]** 空方过度夸大了宏观折现率 (WACC `{engine.wacc*100:.2f}%`) 的压力！"
                        f"即便短期股价横盘，我们也可以利用当前 `{opt_info['atm_iv']*100:.1f}%` 的隐含波动率（对比 GARCH 动态波动率 `{tech.get('garch_vol', tech['hv30'])*100:.1f}%`），通过期权策略收割权利金或构建低成本垂直价差，持仓胜率极高。"
                    )
                    st.markdown(
                        f"<div class='debate-card-bull'>"
                        f"<div style='color:#10b981;font-weight:800;font-size:15px;margin-bottom:6px;'>🐂 看多研究员 (Bull Researcher)</div>"
                        f"<p style='font-size:13.5px;line-height:1.6;margin-bottom:8px;'>{bull_r1}</p>"
                        f"{f'<p style=\"font-size:13.5px;line-height:1.6;margin-bottom:0;\">{bull_r2}</p>' if debate_rounds >= 2 else ''}"
                        f"</div>",
                        unsafe_allow_html=True
                    )

                with d_col2:
                    bear_r1 = (
                        f"**[第一轮立论 - 估值透支与财务质量审视]** 当前市价 `{engine.currency} {engine.price:.2f}` 对比模型公允价 `{engine.fair_val:.2f}` 的安全边际为 `{pipe['mos_pct']:+.1f}%`，"
                        f"Beneish M-Score 财务质量得分为 `{beneish.get('m_score', -2.5):.2f}`（应计比率 `{beneish.get('accruals_pct', 0.0):+.2f}%`）。"
                        f"测谎仪显示市场当前定价隐含了未来 `{engine.horizon}` 年每年 `{pipe['implied_g_pct']:.1f}%` 的增长预期，一旦增速放缓将面临剧烈的估值杀跌。"
                    )
                    bear_r2 = (
                        f"**[第二轮反驳多方 - 尾部风险与回撤压力]** 历史回测显示该标的过去 1 年最大回撤达 `{tech.get('mdd_pct', 0.0):.1f}%`，95% 极端日 CVaR 尾部亏损为 `{tech.get('cvar_95_pct', 0.0):.2f}%`。"
                        f"技术指标 RSI 目前处于 `{tech['rsi']:.1f}`，上方 `{tech['resistance']:.2f}` 阻力重重，盲目单边重仓正股极易在波动中受损！"
                    )
                    st.markdown(
                        f"<div class='debate-card-bear'>"
                        f"<div style='color:#ef4444;font-weight:800;font-size:15px;margin-bottom:6px;'>🐻 看空研究员 (Bear Researcher)</div>"
                        f"<p style='font-size:13.5px;line-height:1.6;margin-bottom:8px;'>{bear_r1}</p>"
                        f"{f'<p style=\"font-size:13.5px;line-height:1.6;margin-bottom:0;\">{bear_r2}</p>' if debate_rounds >= 2 else ''}"
                        f"</div>",
                        unsafe_allow_html=True
                    )

                with st.container(border=True):
                    st.markdown(
                        f"**⚖️ 研究总监裁决 (Research Manager Synthesis - `ResearchPlan`)**  |  "
                        f"**初步投研评级: `{pipe['final_rating'].upper()}` (综合量化得分: `{pipe['total_score']:+.1f}`，含 Beneish 财务修正 `{beneish.get('penalty', 0.0):+.0f}` 分)**"
                    )
                    st.write(
                        f"综合多空双方 {debate_rounds} 轮辩论：基本面估值偏离度为 `{pipe['mos_pct']:+.1f}%`，技术面处于 `{tech['trend']}` 格局。"
                        f"研究部决定采用 **【半凯利公式 (Half-Kelly) 仓位控制 + 期权波动率套利/保护 + Beta 中性多空配对】** 的复合战略指令。"
                    )

                st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

                # --------------------------------------------------------------
                # STAGE 3: 交易员现货、期权与多空配对协同作战方案 (Trader, Options & Pairs Desk)
                # --------------------------------------------------------------
                st.markdown("#### 💼 第三阶段：交易员【半凯利正股 + 期权 + 多空配对】三维作战指令单 (Stage 3: Equity, Options & Pairs Desk)" if lang_key == "zh" else "#### 💼 Stage 3: Half-Kelly Equity, Options & Long-Short Pairs Execution Desk")
                t_col1, t_col2 = st.columns([1.15, 1.35])

                with t_col1:
                    with st.container(border=True):
                        st.markdown("<span class='agent-badge' style='background:rgba(56,189,248,0.2);color:#38bdf8;'>💵 SPOT EQUITY ORDER (半凯利公式仓位提案)</span>", unsafe_allow_html=True)
                        st.markdown(f"##### 执行方向: `{pipe['trader_action']}`  |  Half-Kelly 建议仓位: `{pipe['alloc_pct']:.1f}%`")
                        suggested_shares = int((user_cash * (pipe['alloc_pct'] / 100.0)) // engine.price) if engine.price > 0 else 0
                        st.markdown(
                            f"- **参考建仓/挂单价 (Entry):** `{engine.currency} {pipe['entry_price']:.2f}`\n"
                            f"- **ATR 硬性止损位 (Stop-Loss):** `{engine.currency} {pipe['stop_loss']:.2f}` (2x ATR 支撑防线)\n"
                            f"- **第一止盈目标位 (Take-Profit):** `{engine.currency} {pipe['take_profit']:.2f}`\n"
                            f"- **凯利数学推导 ($0.5 f^*$):** 综合胜率 $p={pipe.get('win_prob_p', 0.5)*100:.1f}\\%$, 赔率 $b={pipe.get('odds_b', 1.5):.2f}:1$ $\\rightarrow$ 全凯利 `{pipe.get('full_kelly_pct', 0.0):.1f}%` $\\rightarrow$ **半凯利 `{pipe.get('half_kelly_pct', 0.0):.1f}%`**\n"
                            f"- **按可用现金折算股数:** 约 `{suggested_shares:,}` 股 (现有持仓 `{user_shares}` 股)"
                        )

                with t_col2:
                    with st.container(border=True):
                        st.markdown("<span class='agent-badge' style='background:rgba(16,185,129,0.25);color:#10b981;'>🎯 OPTIONS TACTICAL ORDER (衍生品期权作战指令)</span>", unsafe_allow_html=True)
                        st.markdown(f"##### 推荐策略: {pipe['opt_strategy_name']}")
                        st.markdown(f"- **具体合约操作:** {pipe['opt_action_detail']}")
                        st.info(f"💡 **期权交易员逻辑 (Options Desk Rationale):** {pipe['opt_rationale']}")

                # 🌟 V13.0 极致优化 C：对冲基金多空配对交易 (Market-Neutral Long-Short Equity Pairs Trading)
                if pair_info:
                    with st.container(border=True):
                        st.markdown("<span class='agent-badge' style='background:rgba(192,132,252,0.22);color:#c084fc;'>⚖️ STAT-ARB LONG-SHORT PAIRS DESK (Beta 中性多空配对统计套利指令)</span>", unsafe_allow_html=True)
                        st.markdown(f"##### 配对结构: {pair_info.get('spread_desc', '')}")
                        st.markdown(
                            f"- **多头腿名义本金 (Long Leg Notional):** `{engine.currency} {pair_info.get('long_notional', 0):,.0f}` (`{pair_info.get('long_tk')}`)  |  "
                            f"**空头腿 Beta 对冲本金 (Short Leg Notional):** `{engine.currency} {pair_info.get('short_notional', 0):,.0f}` (`{pair_info.get('short_tk')}`)\n"
                            f"- **统计套利逻辑:** {pair_info.get('rationale', '')}"
                        )

                with st.container(border=True):
                    st.markdown(f"**📊 交易台推荐期权策略双曲线盈亏仿真与 GBM 到期胜率 ({pipe['opt_strategy_name']})**")
                    fig_ta_payoff, ta_max_p, ta_max_l, ta_opt_stats = draw_option_payoff_diagram(
                        engine, pipe["opt_strat_key"], opt_info["T_years"], opt_info["atm_iv"], lang_key, pipe["opt_legs_meta"], return_stats=True
                    )
                    ta_be_list = ta_opt_stats.get("breakevens", [])
                    ta_be_str = " / ".join([f"{engine.currency}{b:.2f}" for b in ta_be_list]) if ta_be_list else "N/A"
                    pm_c1, pm_c2, pm_c3, pm_c4 = st.columns(4)
                    pm_c1.metric("🎯 策略到期盈利胜率 (PoP %)", f"{ta_opt_stats.get('pop_pct', 0.0):.1f}%", "GBM Risk-Neutral PDF", delta_color="off")
                    pm_c2.metric("⚖️ 精确盈亏平衡点 (Breakevens)", ta_be_str)
                    pm_c3.metric("🚀 单张最大潜在盈利 (100股)", f"{engine.currency} {ta_max_p:,.0f}")
                    pm_c4.metric("🛡️ 单张最大潜在亏损 (100股)", f"{engine.currency} {ta_max_l:,.0f}")
                    st.plotly_chart(fig_ta_payoff, use_container_width=True)

                st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

                # --------------------------------------------------------------
                # STAGE 4 & 5: 风控委员会三方博弈 & 投资组合经理 (PM) 终审拍板
                # --------------------------------------------------------------
                st.markdown("#### 🛡️ 第四 & 第五阶段：风控三方博弈与基金经理终审拍板 (Stage 4 & 5: Risk Committee & PM Decision)" if lang_key == "zh" else "#### 🛡️ Stage 4 & 5: Risk Committee Debate & Portfolio Manager Final Decision")
                r_col1, r_col2, r_col3 = st.columns(3)

                with r_col1:
                    with st.container(border=True):
                        st.markdown("<span class='agent-badge' style='background:rgba(239,68,68,0.2);color:#f87171;'>🔥 AGGRESSIVE RISK DEBATOR</span>", unsafe_allow_html=True)
                        st.write(
                            f"**激进派风控意见：** 全凯利公式给出的理论上限仓位为 `{pipe.get('full_kelly_pct', 0.0):.1f}%`。建议利用期权非线性凸性（Gamma），"
                            f"将部分正股预算置换为 `{opt_info['expiry']}` 到期的看涨价差或卖 Put（当前策略到期胜率 PoP 达 `{ta_opt_stats.get('pop_pct', 0.0):.1f}%`），放大资本效率。"
                        )

                with r_col2:
                    with st.container(border=True):
                        st.markdown("<span class='agent-badge' style='background:rgba(59,130,246,0.2);color:#60a5fa;'>🛡️ CONSERVATIVE RISK DEBATOR</span>", unsafe_allow_html=True)
                        st.write(
                            f"**保守派风控意见：** 标的过去 1 年最大回撤为 `{tech.get('mdd_pct', 0.0):.1f}%`，95% 日 CVaR 极端亏损为 `{tech.get('cvar_95_pct', 0.0):.2f}%`。"
                            f"严禁使用全凯利满仓！必须砍半执行 **Half-Kelly (`{pipe['alloc_pct']:.1f}%`)**，或采用 **多空配对 (`Long {pair_info.get('long_tk')} / Short {pair_info.get('short_tk')}`)** 剥离大盘 Beta。"
                        )

                with r_col3:
                    with st.container(border=True):
                        st.markdown("<span class='agent-badge' style='background:rgba(16,185,129,0.2);color:#34d399;'>⚖️ NEUTRAL RISK DEBATOR</span>", unsafe_allow_html=True)
                        st.write(
                            f"**中立派风控意见：** 折中激进派与保守派诉求，最佳方案是 **【Half-Kelly 现货底仓 (`{pipe['alloc_pct']:.1f}%`) + {pipe['opt_strategy_name'].split('(')[0]}】** 组合。"
                            f"既保留了基本面价值回归的收益，又将盈亏平衡点锁定在 `{ta_be_str}`。"
                        )

                st.markdown(
                    f"""
                    <div class="debate-card-pm">
                        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;">
                            <div style="color:#38bdf8;font-weight:800;font-size:18px;">👑 投资组合经理终审决议 (Portfolio Manager Final Decision - V13.0)</div>
                            <div style="background:linear-gradient(135deg,#10b981,#059669);color:#fff;padding:5px 16px;border-radius:999px;font-weight:800;font-size:15px;">
                                QUANT RATING: {pipe['final_rating'].upper()}
                            </div>
                        </div>
                        <hr style="border-color:rgba(255,255,255,0.1);margin:12px 0;">
                        <p style="font-size:14px;line-height:1.7;margin-bottom:8px;">
                            <b>1. 终审定调：</b> 综合四大分析师硬核数据、Beneish M-Score 财务侦测 (<b>{beneish.get('m_score', -2.5):.2f}</b>)、多空辩论及三方风控意见，批准对 <b>{engine.name} ({engine.ticker})</b> 赋予 <b>【{pipe['final_rating']}】</b> 机构评级。<br>
                            <b>2. 现货执行批示 (Half-Kelly)：</b> 建议目标仓位配比 <b>{pipe['alloc_pct']:.1f}%</b>，参考入场位 <b>{engine.currency} {pipe['entry_price']:.2f}</b>，铁律止损位 <b>{engine.currency} {pipe['stop_loss']:.2f}</b>，目标止盈位 <b>{engine.currency} {pipe['take_profit']:.2f}</b>。<br>
                            <b>3. 期权与配对协同批示：</b> 同步执行 <b>【{pipe['opt_strategy_name']}】</b>（{pipe['opt_action_detail']}），策略到期胜率 (PoP) 为 <b>{ta_opt_stats.get('pop_pct', 0.0):.1f}%</b>，盈亏平衡点 <b>{ta_be_str}</b>；或执行 <b>Beta 中性配对 (Long {pair_info.get('long_tk')} / Short {pair_info.get('short_tk')})</b>。
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)

                # --------------------------------------------------------------
                # 记忆账本归档与导出按钮
                # --------------------------------------------------------------
                mem_c1, mem_c2 = st.columns([1, 1])
                with mem_c1:
                    if st.button("📌 归档本次投委会决议至记忆账本 (Save to Memory Log)", use_container_width=True):
                        save_decision_to_ledger(engine, pipe)
                        st.success(f"✅ 已将 {engine.ticker} ({pipe['final_rating']}) 归档至本地记忆账本！后续 Gemini 辩论将自动读取此记录进行历史反思。")

                ledger_entries = load_memory_ledger()
                if ledger_entries:
                    with st.expander("📜 历史投委会决策记忆账本与实时交割盈亏 (TradingAgents Memory & Settlement Ledger)", expanded=False):
                        rows = []
                        for item in ledger_entries[:15]:
                            rec_p = float(item.get("recorded_price") or 0.0)
                            live_p = engine.price if item.get("ticker") == engine.ticker else rec_p
                            ret_pct = ((live_p - rec_p) / rec_p * 100.0) if rec_p > 0 else 0.0
                            rows.append({
                                "Date": item.get("date"),
                                "Ticker": item.get("ticker"),
                                "Rating": item.get("rating"),
                                "Action": item.get("trader_action"),
                                "Entry Price": f"{item.get('currency', '')} {rec_p:.2f}",
                                "Model Fair Val": f"{item.get('currency', '')} {item.get('fair_value', 0):.2f}",
                                "Option Strategy": item.get("option_strategy"),
                                "Realized Return (vs Spot)": f"{ret_pct:+.2f}%" if item.get("ticker") == engine.ticker else "Switch ticker to settle"
                            })
                        st.dataframe(pd.DataFrame(rows), use_container_width=True)

                st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

                # --------------------------------------------------------------
                # 🌟 STAGE 6: Google Gemini API 首席投委会双向闭环推演 (原生专属模块 - 云端会话安全隔离 + 官方 Gemini 2.5 模型)
                # --------------------------------------------------------------
                st.markdown(
                    "#### ✨ 第六阶段：Google Gemini 2.5 首席投委会双向闭环推演与期权实战书 (Powered by Official Gemini API)"
                    if lang_key == "zh" else
                    "#### ✨ Stage 6: Google Gemini 2.5 Bidirectional Closed-Loop Investment Committee"
                )
                with st.container(border=True):
                    cloud_shared = is_cloud_shared_environment()
                    st.caption(
                        "💡 **专属原生 Gemini 2.5 双向闭环引擎（已通过安全审计）**：自动将上方算出的 **100% 真实 DCF/三表估值、同业可比隐含价、MDD/VaR/CVaR 尾部风险、半凯利仓位、财报 IV Crush 雷达、以及最新 8 条实时财经新闻** 注入 Google Gemini。API Key 默认采用 `st.session_state` 浏览器会话内存级隔离，彻底杜绝公网跨用户泄露！"
                        if lang_key == "zh" else
                        "💡 **Native Gemini 2.5 Closed-Loop Engine (Security Audited)**: Injects 100% of your DCF/3-Statement metrics, Peer Comps, MDD/VaR/CVaR, Half-Kelly sizing, and live headlines into Google Gemini with session-isolated API key storage."
                    )
                    saved_gem_key = load_saved_gemini_key()
                    g_col1, g_col2, g_col3, g_col4 = st.columns([1.5, 1.05, 0.8, 0.75])
                    gemini_key_in = g_col1.text_input(
                        "🔑 Google Gemini API Key (会话隔离保护)" if lang_key == "zh" else "🔑 Google Gemini API Key (Session Isolated)",
                        value=saved_gem_key,
                        type="password",
                        placeholder="AIzaSy..."
                    )
                    # 🚨 安全与可用性修复 #2：全部采用 Google 官方真实存在的旗舰与高速模型 ID，彻底消除 404 NOT_FOUND
                    gemini_model_in = g_col2.selectbox(
                        "🤖 选择官方 Gemini 模型 (Official Model)" if lang_key == "zh" else "🤖 Select Official Gemini Model",
                        options=[
                            "gemini-2.5-flash",
                            "gemini-2.5-pro",
                            "gemini-2.5-flash-lite",
                            "gemini-2.0-flash"
                        ],
                        index=0
                    )
                    remember_key = g_col3.checkbox(
                        "💾 本机磁盘记住 Key" if lang_key == "zh" else "💾 Save to Local Disk",
                        value=(not cloud_shared),
                        disabled=cloud_shared,
                        help="公网云端环境已自动禁用服务器磁盘写入，仅保存在您当前浏览器的私有 Session 会话中，关掉网页即销毁。" if cloud_shared else "仅在您个人单机电脑运行且勾选时，才会写入本机 ~/.tradingagents/gemini_config.json"
                    )
                    auto_debate = g_col4.checkbox(
                        "⚡ 自动与模型辩论" if lang_key == "zh" else "⚡ Auto-Debate",
                        value=bool(saved_gem_key)
                    )

                    run_gem_now = st.button("✨ 立即让【量化模型】与【Google Gemini 2.5】展开深度辩论 & 双向修正期权策略", use_container_width=True)
                    report_cache_key = f"gemini_report_{engine.ticker}_{gemini_model_in}_{user_shares}"

                    if run_gem_now or (auto_debate and gemini_key_in.strip() and report_cache_key not in st.session_state):
                        if not gemini_key_in.strip():
                            st.warning("⚠️ 请先在上方输入框填入您的 Google Gemini API Key（以 `AIza` 开头），或配置在环境变量 `GEMINI_API_KEY` 中。")
                        else:
                            save_gemini_key_local(gemini_key_in, allow_disk=remember_key)
                            with st.spinner(f"正在让您的量化数学引擎与 Google 官方 {gemini_model_in} 进行多轮交锋与双向闭环期权推演..."):
                                try:
                                    gem_report = invoke_gemini_committee(
                                        gemini_key_in, gemini_model_in, engine, pipe, user_cash, user_shares, lang_key
                                    )
                                    st.session_state[report_cache_key] = gem_report
                                except Exception as gem_exc:
                                    st.error(f"Gemini API 调用失败: {gem_exc}")

                    if report_cache_key in st.session_state:
                        clean_gem_md, gem_verdict = parse_gemini_verdict(st.session_state[report_cache_key], pipe)
                        st.markdown("---")

                        is_overridden = (
                            str(gem_verdict["gemini_rating"]).lower() != pipe["final_rating"].lower()
                            or str(gem_verdict["gemini_opt_strat_key"]).lower() != pipe["opt_strat_key"].lower()
                        )
                        badge_bg = "linear-gradient(135deg,#f59e0b,#d97706)" if is_overridden else "linear-gradient(135deg,#10b981,#059669)"
                        status_txt = "⚡ GEMINI 已修正量化初判 (OVERRIDDEN)" if is_overridden else "✅ GEMINI 确认量化初判 (CONFIRMED)"

                        st.markdown(
                            f"""
                            <div style="background:linear-gradient(135deg,rgba(15,23,42,0.95),rgba(30,41,59,0.9));border:1.5px solid #38bdf8;border-radius:12px;padding:18px;margin-bottom:14px;">
                                <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;margin-bottom:10px;">
                                    <div style="color:#38bdf8;font-weight:800;font-size:16px;">
                                        🔄 【双向闭环裁决中心】本地量化模型初判 ↔ Google Gemini ({gemini_model_in}) 终判对比
                                    </div>
                                    <span style="background:{badge_bg};color:#fff;padding:4px 12px;border-radius:999px;font-size:12px;font-weight:800;">
                                        {status_txt}
                                    </span>
                                </div>
                                <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;font-size:13.5px;color:#e2e8f0;">
                                    <div style="background:rgba(255,255,255,0.04);padding:10px 12px;border-radius:8px;">
                                        <span style="color:#94a3b8;">📊 量化模型初判评级 (Half-Kelly)：</span><br>
                                        <b>{pipe['final_rating'].upper()} ({pipe['trader_action']} | 仓位 {pipe['alloc_pct']:.1f}%)</b>
                                    </div>
                                    <div style="background:rgba(56,189,248,0.1);padding:10px 12px;border-radius:8px;border:1px solid rgba(56,189,248,0.3);">
                                        <span style="color:#38bdf8;">✨ Gemini 辩论终判评级：</span><br>
                                        <b>{str(gem_verdict['gemini_rating']).upper()} ({gem_verdict['gemini_action']} | 建议仓位 {gem_verdict['gemini_alloc_pct']}%)</b>
                                    </div>
                                    <div style="background:rgba(16,185,129,0.1);padding:10px 12px;border-radius:8px;border:1px solid rgba(16,185,129,0.3);">
                                        <span style="color:#10b981;">🎯 Gemini 钦定期权结构：</span><br>
                                        <b>{str(gem_verdict['gemini_opt_strat_key']).upper().replace('_', ' ')}</b>
                                    </div>
                                </div>
                                <div style="margin-top:10px;font-size:13px;color:#cbd5e1;border-top:1px solid rgba(255,255,255,0.08);padding-top:8px;">
                                    💬 <b>投委会主席裁决摘要：</b> {gem_verdict['override_summary']}
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                        valid_strat_keys = {"cash_secured_put", "bull_call_spread", "covered_call", "iron_condor", "collar", "bear_put_spread", "protective_put", "straddle"}
                        gem_strat_k = str(gem_verdict.get("gemini_opt_strat_key") or "").strip().lower()
                        if gem_strat_k in valid_strat_keys and gem_strat_k != pipe["opt_strat_key"]:
                            st.markdown(f"**📈 Gemini 辩论修正后的期权策略盈亏仿真 (`{gem_strat_k.upper()}`)**")
                            fig_gem_payoff, gem_mp, gem_ml, gem_opt_stats = draw_option_payoff_diagram(
                                engine, gem_strat_k, opt_info["T_years"], opt_info["atm_iv"], lang_key, pipe["opt_legs_meta"], return_stats=True
                            )
                            g_be_list = gem_opt_stats.get("breakevens", [])
                            g_be_str = " / ".join([f"{engine.currency}{b:.2f}" for b in g_be_list]) if g_be_list else "N/A"
                            gc1, gc2, gc3, gc4 = st.columns(4)
                            gc1.metric("🎯 修正策略到期胜率 (PoP %)", f"{gem_opt_stats.get('pop_pct', 0.0):.1f}%")
                            gc2.metric("⚖️ 修正策略盈亏平衡点", g_be_str)
                            gc3.metric("🚀 单张最大潜在盈利", f"{engine.currency} {gem_mp:,.0f}")
                            gc4.metric("🛡️ 单张最大潜在亏损", f"{engine.currency} {gem_ml:,.0f}")
                            st.plotly_chart(fig_gem_payoff, use_container_width=True)

                        st.markdown(clean_gem_md)

                        export_md = (
                            f"# {engine.name} ({engine.ticker}) — V12.0 量化估值与 Google Gemini 多智能体期权作战书\n"
                            f"- **生成日期**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                            f"- **当前现价**: {engine.currency} {engine.price:.2f} | **内在公允价**: {engine.currency} {engine.fair_val:.2f} (MoS: {pipe['mos_pct']:+.1f}%)\n"
                            f"- **三表动态 DCF**: {engine.currency} {(engine.val_3stmt_dcf or 0):.2f} | **同业 P/E 隐含价**: {engine.currency} {(engine.val_pe or 0):.2f} | **WACC**: {engine.wacc*100:.2f}%\n"
                            f"- **尾部风险**: 1Y MDD `{tech.get('mdd_pct', 0.0):.1f}%` | 95% VaR `{tech.get('var_95_pct', 0.0):.2f}%` | 95% CVaR `{tech.get('cvar_95_pct', 0.0):.2f}%`\n"
                            f"- **量化初判**: {pipe['final_rating']} (Half-Kelly `{pipe['alloc_pct']:.1f}%` | {pipe['opt_strategy_name']} PoP `{ta_opt_stats.get('pop_pct', 0.0):.1f}%`) | **Gemini 终判**: {gem_verdict['gemini_rating']} ({gem_verdict['gemini_opt_strat_key']})\n\n"
                            f"---\n\n{clean_gem_md}\n"
                        )
                        st.download_button(
                            label="📥 一键下载完整【V12.0 量化估值 + Gemini 辩论 + 期权作战书】(.md)",
                            data=export_md.encode("utf-8"),
                            file_name=f"{engine.ticker}_V12_Quant_Gemini_Playbook_{datetime.datetime.now().strftime('%Y%m%d')}.md",
                            mime="text/markdown",
                            use_container_width=True
                        )


                # 保留给其他人的可选外部接口 (OpenAI / DeepSeek / OpenRouter)
                with st.expander("🔌 【其他人可选】接入其他第三方兼容接口 (OpenAI / DeepSeek / OpenRouter)", expanded=False):
                    st.caption("如果您或团队其他成员需要使用 OpenAI / DeepSeek 等其他模型接口，可在此处单独调用：")
                    llm_c1, llm_c2, llm_c3 = st.columns(3)
                    api_key_in = llm_c1.text_input("Other API Key", type="password", placeholder="sk-...")
                    base_url_in = llm_c2.text_input("API Base URL", value="https://api.openai.com/v1")
                    model_in = llm_c3.text_input("Model Name", value="gpt-4o-mini")
                    if st.button("🚀 使用第三方接口生成辩论"):
                        if not api_key_in.strip():
                            st.warning("⚠️ 请先输入有效的 API Key。")
                        else:
                            with st.spinner("第三方大模型正在推演..."):
                                try:
                                    llm_output = invoke_live_llm_committee(api_key_in, base_url_in, model_in, engine, pipe, user_cash, user_shares, lang_key)
                                    clean_other_md, _ = parse_gemini_verdict(llm_output, pipe)
                                    st.markdown(clean_other_md)
                                except Exception as exc:
                                    st.error(f"API 调用失败: {exc}")

    # [模块 12：免责声明]
    st.markdown("---")
    with st.container(border=True):
        st.markdown(f"### {T['disclaimer_title']}")
        st.markdown(T['disclaimer_1'])
        st.markdown(T['disclaimer_2'])
        st.markdown(T['disclaimer_3'])
        st.markdown("")
        st.markdown(
            "<div style='text-align: center; color: #94a3b8; font-size: 12px; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 10px;'>"
            "© 2026 Thomas. All rights reserved. | Developed for Academic & Quantitative Research."
            "</div>",
            unsafe_allow_html=True
        )


if __name__ == '__main__':
    main()
