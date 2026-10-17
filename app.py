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
    page_title="Ultimate Quant & TradingAgents Terminal V11.0",
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
# 2. 高速数据缓存层 (@st.cache_data 彻底解决滑块与语言切换卡顿)
# ==============================================================================
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_ticker_bundle(ticker: str):
    """缓存标的公司的核心 Info 与三大财务报表 (1小时有效)"""
    t = yf.Ticker(ticker)
    info = t.info or {}
    if 'symbol' not in info and not info.get('regularMarketPrice') and not info.get('currentPrice') and not info.get('previousClose'):
        hist_check = t.history(period="5d")
        if hist_check.empty:
            raise ValueError(f"Data missing for {ticker}")
        info['symbol'] = ticker
        info['previousClose'] = float(hist_check['Close'].dropna().iloc[-1])

    fallback_price = 0.0
    if not (info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')):
        try:
            h = t.history(period="5d")
            if not h.empty:
                fallback_price = float(h['Close'].dropna().iloc[-1])
        except Exception:
            pass

    bs = t.balance_sheet
    fin = t.financials
    cfs = t.cashflow
    return info, bs, fin, cfs, fallback_price


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
    s_hist = yf.Ticker(ticker).history(period='3y', interval='1mo')
    m_hist = yf.Ticker(market_sym).history(period='3y', interval='1mo')
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
    """缓存 1 年日 K 线数据"""
    return yf.Ticker(ticker).history(period="1y", interval="1d")


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_peer_info(peer_ticker: str):
    """缓存同业可比公司 Info"""
    return yf.Ticker(peer_ticker).info or {}


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_portfolio_history(tickers_tuple: tuple):
    """缓存有效前沿资产池的收盘价序列"""
    data = yf.download(list(tickers_tuple), period="1y", interval="1d", progress=False)['Close']
    if isinstance(data, pd.Series):
        data = data.to_frame(name=tickers_tuple[0])
    return data


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_option_expirations(ticker: str):
    """缓存期权到期日列表"""
    return yf.Ticker(ticker).options


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_option_chain_df(ticker: str, expiry: str):
    """缓存指定到期日的 Calls 与 Puts 期权链"""
    chain = yf.Ticker(ticker).option_chain(expiry)
    return chain.calls, chain.puts


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_recent_news(ticker: str):
    """缓存标的近期新闻标题 (用于 TradingAgents 情绪与新闻分析师节点)"""
    try:
        raw_news = yf.Ticker(ticker).news or []
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


# ==============================================================================
# 3. 国际化多语言字典
# ==============================================================================
TEXTS = {
    "zh": {
        "title": "🌐 智能量化与多智能体金融终端 (V11.0 满血终极版)",
        "subtitle": "融合 线性衰减DCF、真实三表NWC、LBO、并行Comps、SLSQP有效前沿、双曲线B-S期权、财报IV预警 与 Gemini 双向闭环投委会",
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
        "title": "🌐 Universal Quant & Multi-Agent Terminal (Flagship V11.0)",
        "subtitle": "Integrating Fading DCF, True 3-Stmt NWC, LBO, Parallel Comps, SLSQP Frontier, Dual-Curve Options, Earnings IV Radar & Gemini Closed-Loop IC",
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
        "note_pe": "Based on EPS multiplied by benchmark P/E multiples.",
        
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
        "beta_desc": "📊 **Beta Scatter Plot Explanation:** Each dot represents past 3-year monthly return correlation. The red line slope represents the Beta relationship (Bursa benchmarks against FTSE Bursa KLCI `^KLSE`, US equities against S&P 500 `^GSPC`).\n* **$R^2$ Analysis**: Tight clustering indicates market-driven systemic risk; higher dispersion reflects strong independent trends.",
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
# 4. 核心硬核量化引擎 (集成真实NWC反推、动态Rf/有效税率、财报IV预警、双曲线期权与TradingAgents)
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

        # 🌟 优化点 3：从真实资产负债表与现金流量表反推历史 DSO / DIO / DPO / Capex%
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
        self.hardcore_ufcf_proj = []
        self.hardcore_ebitda_proj = []
        self.val_3stmt_dcf = None

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
            cov = np.cov(aligned.iloc[:, 0], aligned.iloc[:, 1])[0, 1]
            var = np.var(aligned.iloc[:, 1], ddof=1)
            if var == 0:
                return fallback, 'Zero Market Var'
            raw_beta = cov / var
            if not np.isfinite(raw_beta):
                return fallback, 'System Default'
            clipped_beta = float(np.clip(raw_beta, 0.2, 2.5))
            blume_beta = round((0.67 * clipped_beta) + (0.33 * 1.0), 2)
            tag = 'Blume Adjusted' if 0.2 <= raw_beta <= 2.5 else 'Blume (Clipped)'
            return blume_beta, tag
        except Exception:
            return fallback, 'System Default'

    def run_valuation(self, erp, terminal_g):
        self.beta, self.beta_type = self.compute_blume_beta()
        # 🌟 优化点 4：动态 10Y 国债收益率 Rf 与真实有效税率 Effective Tax Rate
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

        int_exp = abs(float(self.info.get('interestExpense') or get_fin_metric(self.fin, 'Interest Expense', 0.0)))
        kd = min((int_exp / self.debt) if self.debt > 0 else 0.05, 0.10)
        self.wacc = (w_e * self.ke) + (w_d * kd * (1 - self.tax))
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
        self.val_pe = None
        if eps > 0:
            bench_pe = 24.0 if self.sector in ['Technology', 'Communication Services'] else (11.5 if self.sector == 'Financial Services' else 16.0)
            self.val_pe = eps * bench_pe

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
        years = ['Year 0 (Current)', 'Year 1', 'Year 2', 'Year 3', 'Year 4', 'Year 5']

        rev_0 = self.revenue
        cogs_0 = self.cogs if self.cogs > 0 else rev_0 * 0.5
        ebitda_margin = self.ebitda / self.revenue if self.revenue > 0 else 0.2
        tax_rate = self.tax

        rev = [rev_0]
        cogs = [cogs_0]
        ebitda = [self.ebitda]
        da = [self.hist_da]
        capex = [rev_0 * capex_pct]

        ar = [(dso / 365.0) * rev_0]
        inv = [(dio / 365.0) * cogs_0]
        ap = [(dpo / 365.0) * cogs_0]
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

    def run_lbo_model(self, ltv_ratio, interest_rate, exit_multiple):
        purchase_price = self.ev
        debt_funding = purchase_price * ltv_ratio
        equity_funding = purchase_price - debt_funding

        debt_schedule = [debt_funding]

        for fcf in self.hardcore_ufcf_proj:
            interest = debt_schedule[-1] * interest_rate
            cash_sweep = max(0.0, fcf - interest)
            ending_debt = max(0.0, debt_schedule[-1] - cash_sweep)
            debt_schedule.append(ending_debt)

        y5_ebitda = self.hardcore_ebitda_proj[-1] if self.hardcore_ebitda_proj else self.ebitda * ((1.0 + self.g2) ** 5)
        exit_ev = y5_ebitda * exit_multiple
        exit_equity = max(0.0, exit_ev - debt_schedule[-1])

        moic = exit_equity / equity_funding if equity_funding > 0 else 0.0
        irr = (moic ** (1.0 / 5.0)) - 1.0 if moic > 0 else -1.0

        return {
            "Entry EV": purchase_price, "Debt": debt_funding, "Equity": equity_funding,
            "Y5 EBITDA": y5_ebitda, "Exit EV": exit_ev, "Exit Debt": debt_schedule[-1],
            "Exit Equity": exit_equity, "MOIC": moic, "IRR": irr, "Debt Schedule": debt_schedule
        }

    def run_comps_analysis(self):
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

        # 🌟 优化点 8：使用多线程并发抓取同业数据，大幅降低等待延迟
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
                ev_ebitda_str = f"{pev / pebitda:.2f}" if pebitda > 0 else "N/A (Bank/Fin)"
                return {
                    "Ticker": p,
                    "Name": str(pi.get('shortName') or p)[:16],
                    mcap_col: round(pmcap / 1e9, 2),
                    "EV/EBITDA": ev_ebitda_str,
                    "P/E": round(pe_ratio, 2) if pe_ratio > 0 else 0.0,
                    "Gross Margin %": round(gm, 1)
                }
            except Exception:
                return None

        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(_build_peer_row, peers))
        for r_item in results:
            if r_item is not None:
                comp_data.append(r_item)
        return pd.DataFrame(comp_data)

    def run_monte_carlo(self, sims=2000):
        if self.cf <= 0 or self.shares <= 0:
            return []
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
        return vals[vals > 0].tolist()

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

    # ==========================================================================
    # 🌟 核心融合：TradingAgents 五阶段多智能体投委会与期权作战引擎
    # ==========================================================================
    def compute_technical_signals(self):
        """对应 TradingAgents 的 Market Technical Analyst 工具集 (RSI, MACD, Bollinger, ATR, SMA)"""
        hist = fetch_candlestick_history(self.ticker)
        if hist.empty or len(hist) < 30:
            return {
                "rsi": 50.0, "macd": 0.0, "macd_signal": 0.0, "macd_hist": 0.0,
                "ma20": self.price, "ma50": self.price, "ma200": self.price,
                "atr": self.price * 0.025, "hv30": 0.30,
                "support": self.price * 0.93, "resistance": self.price * 1.08,
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
            "atr": atr, "hv30": hv30, "support": support, "resistance": resistance,
            "trend": trend
        }

    def compute_options_intelligence(self, hv30: float):
        """提取期权链 ATM IV、Put-Call Skew、真实行权价、财报日 IV Crush 预警与预期涨跌幅 (Implied Move)"""
        default_iv = max(hv30 * 1.1, 0.25)
        now = datetime.datetime.now()

        # 🌟 优化点 2：检测下一季财报日 (Earnings Date) 距离今天的天数
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
                    "hv30": hv30, "iv_hv_ratio": 1.1, "skew": 0.0, "expiry": "30D (Synthetic)",
                    "T_years": T_y, "days": 30, "strikes": [],
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

            calls, puts = fetch_option_chain_df(self.ticker, chosen_exp)
            atm_iv = default_iv
            if not calls.empty and 'impliedVolatility' in calls.columns:
                near_c = calls.iloc[(calls['strike'] - self.price).abs().argsort()[:3]]
                valid_c_iv = near_c['impliedVolatility'][near_c['impliedVolatility'] > 0.01]
                if not valid_c_iv.empty:
                    atm_iv = float(valid_c_iv.mean())

            otm_put_iv = atm_iv
            if not puts.empty and 'impliedVolatility' in puts.columns:
                otm_p = puts[(puts['strike'] >= self.price * 0.88) & (puts['strike'] <= self.price * 0.96)]
                valid_p_iv = otm_p['impliedVolatility'][otm_p['impliedVolatility'] > 0.01]
                if not valid_p_iv.empty:
                    otm_put_iv = float(valid_p_iv.mean())

            otm_call_iv = atm_iv
            if not calls.empty and 'impliedVolatility' in calls.columns:
                otm_c = calls[(calls['strike'] >= self.price * 1.04) & (calls['strike'] <= self.price * 1.12)]
                valid_oc_iv = otm_c['impliedVolatility'][otm_c['impliedVolatility'] > 0.01]
                if not valid_oc_iv.empty:
                    otm_call_iv = float(valid_oc_iv.mean())

            skew = (otm_put_iv - atm_iv) * 100.0
            iv_hv_ratio = atm_iv / max(hv30, 0.05)
            avail_strikes = sorted(list(set(calls['strike'].dropna().tolist()))) if not calls.empty and 'strike' in calls.columns else []
            T_y = max(chosen_days / 365.0, 7 / 365.0)
            bs_atm = self.black_scholes_pricing(self.price, self.price, T_y, self.rf, atm_iv)
            imp_move_pct = ((bs_atm["Call"] + bs_atm["Put"]) / max(self.price, 1.0)) * 100.0
            earnings_alert = bool(days_to_earnings is not None and 0 <= days_to_earnings <= chosen_days)

            return {
                "has_options": True,
                "atm_iv": atm_iv,
                "otm_put_iv": otm_put_iv,
                "otm_call_iv": otm_call_iv,
                "hv30": hv30,
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
                "hv30": hv30, "iv_hv_ratio": 1.1, "skew": 0.0, "expiry": "30D (Synthetic)",
                "T_years": T_y, "days": 30, "strikes": [],
                "earnings_date": earnings_date_str, "days_to_earnings": days_to_earnings,
                "earnings_alert": False, "implied_move_pct": 6.5
            }

    def run_trading_agents_pipeline(self, portfolio_cash: float = 100000.0, current_shares: int = 0, lang_key: str = "zh"):
        """
        复刻并升级 TradingAgents 全链路状态机：
        Stage 1 (4 Analysts) -> Stage 2 (Bull vs Bear Debate & Research Manager)
        -> Stage 3 (Equity & Options Trader Desk) -> Stage 4 (3-Way Risk Debate)
        -> Stage 5 (Portfolio Manager 5-Tier Verdict)
        """
        tech = self.compute_technical_signals()
        opt_info = self.compute_options_intelligence(tech["hv30"])
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

        val_score = float(np.clip(mos_pct * 1.2, -45, 45))
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

        S = self.price
        atr = tech["atr"]
        iv = opt_info["atm_iv"]
        put_iv = opt_info.get("otm_put_iv", iv)
        call_iv = opt_info.get("otm_call_iv", iv)
        T_y = opt_info["T_years"]
        q_y = div_yield / 100.0

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
            alloc_pct = 20.0 if final_rating == "Buy" else 12.0

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
                    f"当前期权隐含波动率 (IV={iv*100:.1f}%) 高于 30日历史波动率 (HV={tech['hv30']*100:.1f}%)，且无近期财报跳空地雷。"
                    f"通过**卖出 {k_95_put:.2f} 虚值 Put (Skew IV={put_iv*100:.1f}%)** 收取丰厚权利金；若回调则以 {breakeven:.2f} 折价接盘正股。"
                ) if lang_key == "zh" else (
                    f"Implied Volatility (IV={iv*100:.1f}%) trades at a premium to HV ({tech['hv30']*100:.1f}%). "
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
            alloc_pct = 10.0

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
            alloc_pct = 0.0

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

        return {
            "tech": tech,
            "opt_info": opt_info,
            "opt_legs_meta": opt_legs_meta,
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
# 6. 图表生成 (热力图 + K线 + Beta + 双曲线期权盈亏图 Expiration & T+0 B-S Curve)
# ==============================================================================
def draw_sensitivity_heatmap(engine):
    if engine.cf <= 0:
        return None, None
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
    return fig, heat_summary


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
    if engine.scatter_data is None or engine.scatter_data.empty:
        return None
    stock_ret = engine.scatter_data.iloc[:, 0]
    market_ret = engine.scatter_data.iloc[:, 1]
    corr = np.corrcoef(stock_ret, market_ret)[0, 1]
    r_squared = (corr ** 2) if not np.isnan(corr) else 0.0

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=market_ret, y=stock_ret, mode='markers',
        marker=dict(color='#38bdf8', size=7, opacity=0.8), name='Monthly Returns'
    ))
    x_range = np.linspace(market_ret.min(), market_ret.max(), 100)
    fig.add_trace(go.Scatter(
        x=x_range, y=engine.beta * x_range, mode='lines',
        line=dict(color='#ef4444', width=2), name='Blume Beta Line'
    ))
    fig.update_layout(
        title=dict(text=f"Beta Regression (Blume β = {engine.beta:.2f} | R² = {r_squared:.2f})", font=dict(color='#ffffff')),
        xaxis_title="Market Benchmark Monthly Return",
        yaxis_title="Stock Monthly Return",
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#94a3b8'),
        xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
        showlegend=False, height=330, margin=dict(l=0, r=0, t=35, b=0)
    )
    return fig


def draw_option_payoff_diagram(engine, strategy_key, T_years, iv, lang_key="zh", legs_meta: dict | None = None):
    """
    🌟 优化点 1：
    1) 与交易台真实对齐行权价 (snap_k)、股息率 q 及波动率偏度 (Skew IV) 100% 同步；
    2) 同时绘制【到期日盈亏实线 (Expiration Payoff)】与【半周期/盘中 B-S 动态理论盈亏虚线 (Mid-Term B-S Curve)】！
    """
    S = engine.price
    r = engine.rf
    s_grid = np.linspace(S * 0.70, S * 1.30, 250)
    meta = legs_meta or {}

    k_atm = meta.get("k_atm", round(S, 2))
    k_95_put = meta.get("k_95_put", round(S * 0.95, 2))
    k_98_put = meta.get("k_98_put", round(S * 0.98, 2))
    k_otm_put = meta.get("k_otm_put", round(S * 0.92, 2))
    k_far_put = meta.get("k_far_put", round(S * 0.85, 2))
    k_otm_call = meta.get("k_otm_call", round(S * 1.05, 2))
    k_108_call = meta.get("k_108_call", round(S * 1.08, 2))
    k_far_call = meta.get("k_far_call", round(S * 1.12, 2))

    atm_iv = meta.get("atm_iv", iv)
    put_iv = meta.get("put_iv", iv)
    call_iv = meta.get("call_iv", iv)
    q = meta.get("q_yield", 0.0)
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

    if strategy_key == "cash_secured_put":
        pnl = p_95 - np.maximum(k_95_put - s_grid, 0.0)
        pnl_mid = p_95 - engine.black_scholes_pricing(s_grid, k_95_put, T_mid, r, put_iv, q)["Put"]
        label = f"Cash-Secured Short Put (Sell Put @ {k_95_put:.2f}, Credit: +{p_95:.2f})"
    elif strategy_key == "bear_put_spread":
        net_debit_bp = max(0.05, p_98 - p_otm)
        pnl = np.maximum(k_98_put - s_grid, 0.0) - np.maximum(k_otm_put - s_grid, 0.0) - net_debit_bp
        pnl_mid = (
            engine.black_scholes_pricing(s_grid, k_98_put, T_mid, r, put_iv, q)["Put"]
            - engine.black_scholes_pricing(s_grid, k_otm_put, T_mid, r, put_iv, q)["Put"]
            - net_debit_bp
        )
        label = f"Bear Put Spread (Buy {k_98_put:.2f} Put / Sell {k_otm_put:.2f} Put)"
    elif strategy_key == "covered_call":
        pnl = (s_grid - S) + c_otm - np.maximum(s_grid - k_otm_call, 0.0)
        pnl_mid = (s_grid - S) + c_otm - engine.black_scholes_pricing(s_grid, k_otm_call, T_mid, r, call_iv, q)["Call"]
        label = f"Covered Call (Long Stock @ {S:.2f} + Short Call @ {k_otm_call:.2f})"
    elif strategy_key == "protective_put":
        pnl = (s_grid - S) - p_otm + np.maximum(k_otm_put - s_grid, 0.0)
        pnl_mid = (s_grid - S) - p_otm + engine.black_scholes_pricing(s_grid, k_otm_put, T_mid, r, put_iv, q)["Put"]
        label = f"Protective Put (Long Stock @ {S:.2f} + Long Put @ {k_otm_put:.2f})"
    elif strategy_key == "collar":
        pnl = (s_grid - S) - p_otm + np.maximum(k_otm_put - s_grid, 0.0) + c_otm - np.maximum(s_grid - k_otm_call, 0.0)
        pnl_mid = (
            (s_grid - S) - p_otm
            + engine.black_scholes_pricing(s_grid, k_otm_put, T_mid, r, put_iv, q)["Put"]
            + c_otm
            - engine.black_scholes_pricing(s_grid, k_otm_call, T_mid, r, call_iv, q)["Call"]
        )
        label = f"Collar (Long Put @ {k_otm_put:.2f} + Short Call @ {k_otm_call:.2f})"
    elif strategy_key == "bull_call_spread":
        net_debit = max(0.05, c_atm - c_108)
        pnl = np.maximum(s_grid - k_atm, 0.0) - np.maximum(s_grid - k_108_call, 0.0) - net_debit
        pnl_mid = (
            engine.black_scholes_pricing(s_grid, k_atm, T_mid, r, atm_iv, q)["Call"]
            - engine.black_scholes_pricing(s_grid, k_108_call, T_mid, r, call_iv, q)["Call"]
            - net_debit
        )
        label = f"Bull Call Spread (Buy {k_atm:.2f} Call / Sell {k_108_call:.2f} Call)"
    elif strategy_key == "iron_condor":
        net_credit = max(0.05, (c_108 - c_far) + (p_otm - p_far))
        call_spread_loss = np.maximum(s_grid - k_108_call, 0.0) - np.maximum(s_grid - k_far_call, 0.0)
        put_spread_loss = np.maximum(k_otm_put - s_grid, 0.0) - np.maximum(k_far_put - s_grid, 0.0)
        pnl = net_credit - call_spread_loss - put_spread_loss
        pnl_mid = net_credit - (
            engine.black_scholes_pricing(s_grid, k_108_call, T_mid, r, call_iv, q)["Call"]
            - engine.black_scholes_pricing(s_grid, k_far_call, T_mid, r, call_iv, q)["Call"]
        ) - (
            engine.black_scholes_pricing(s_grid, k_otm_put, T_mid, r, put_iv, q)["Put"]
            - engine.black_scholes_pricing(s_grid, k_far_put, T_mid, r, put_iv, q)["Put"]
        )
        label = f"Iron Condor (Profit Zone: {k_otm_put:.2f} ~ {k_108_call:.2f})"
    else:
        total_prem = c_atm + p_atm
        pnl = np.maximum(s_grid - k_atm, 0.0) + np.maximum(k_atm - s_grid, 0.0) - total_prem
        pnl_mid = (
            engine.black_scholes_pricing(s_grid, k_atm, T_mid, r, atm_iv, q)["Call"]
            + engine.black_scholes_pricing(s_grid, k_atm, T_mid, r, atm_iv, q)["Put"]
            - total_prem
        )
        label = f"Long Straddle (ATM Strike @ {k_atm:.2f}, Cost: {total_prem:.2f})"

    pnl_contract = pnl * 100.0
    pnl_mid_contract = pnl_mid * 100.0

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
    fig.add_hline(y=0, line_dash="dot", line_color="#94a3b8")
    fig.add_vline(x=S, line_dash="dash", line_color="#facc15", annotation_text=f"Spot: {engine.currency} {S:.2f}")

    fig.update_layout(
        title=dict(text=label, font=dict(color='#ffffff', size=14)),
        xaxis_title="Underlying Stock Price ➡️" if lang_key == "en" else "标的股票价格 ➡️",
        yaxis_title=f"Net P&L ({engine.currency} / 1 Contract)" if lang_key == "en" else f"净盈亏 ({engine.currency} / 每张合约100股)",
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#94a3b8'),
        xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=380, margin=dict(l=0, r=0, t=55, b=0)
    )
    return fig, float(np.max(pnl_contract)), float(np.min(pnl_contract))


# ==============================================================================
# 7. 原生 Google Gemini API 投委会深度推演与双向闭环修正引擎 (附其他接口可选扩展)
# ==============================================================================
# 💡 如果您不想在网页端手动输入，可直接将免费的 Google AI Studio Key (AIzaSy...) 填在下方引号内：
DEFAULT_GEMINI_API_KEY = ""
GEMINI_CONFIG_FILE = Path.home() / ".tradingagents" / "gemini_config.json"


def load_saved_gemini_key() -> str:
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
    if GEMINI_CONFIG_FILE.exists():
        try:
            data = json.loads(GEMINI_CONFIG_FILE.read_text(encoding="utf-8"))
            return str(data.get("gemini_api_key") or "").strip()
        except Exception:
            return ""
    return ""


def save_gemini_key_local(api_key: str):
    GEMINI_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    GEMINI_CONFIG_FILE.write_text(
        json.dumps({"gemini_api_key": api_key.strip()}, ensure_ascii=False, indent=2),
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

    # 🌟 优化点 6：提取该标的的历史记忆账本记录，注入 Prompt 让 Gemini 自我反思 (Episodic Memory Reflection)
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
- 两阶段衰减 DCF 公允价: {engine.currency} {(engine.val_dcf or 0):.2f} | 三表真实营运资本动态 DCF (DSO={engine.hist_dso}/DIO={engine.hist_dio}/DPO={engine.hist_dpo}): {engine.currency} {(engine.val_3stmt_dcf or 0):.2f} | P/E 倍数估值: {engine.currency} {(engine.val_pe or 0):.2f}
- WACC 折现门槛: {engine.wacc*100:.2f}% (Rf={engine.rf*100:.2f}%, {engine.tax_tag}) | Blume 修正 Beta: {engine.beta:.2f} | 测谎仪市场隐含年化增长率: {pipe['implied_g_pct']:.2f}%
- 华尔街投行平均目标价: {engine.currency} {pipe['target_mean']:.2f} (华尔街预期空间: {pipe['ws_upside']:+.1f}%) | 股息率: {pipe['div_yield']:.2f}%

[2. 技术面量价与波动率信号 (Technical & Momentum Signals)]
- 趋势结构判定: {pipe['tech']['trend']} | RSI(14): {pipe['tech']['rsi']:.1f} | MACD 柱状图: {pipe['tech']['macd_hist']:+.3f}
- 均线系统: MA20={pipe['tech']['ma20']:.2f}, MA50={pipe['tech']['ma50']:.2f}, MA200={pipe['tech']['ma200']:.2f}
- 14日真实波幅 (ATR): {engine.currency} {pipe['tech']['atr']:.2f} | 20日关键支撑位: {pipe['tech']['support']:.2f} | 20日关键阻力位: {pipe['tech']['resistance']:.2f}

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
   - 🐻 **看空研究员 (Bear Case)**：从 WACC 折现压力、估值溢价与财报/波动率尾部风险展开立论并反驳多头。
3. **💵 正股精准交易执行计划 (Spot Equity Execution Plan)**：结合账户可用现金 ({engine.currency} {user_cash:,.0f}) 与现有持仓 ({user_shares} 股)，给出分批建仓区间、2x ATR 硬止损价 ({engine.currency} {pipe['stop_loss']:.2f}) 及分批止盈目标位。
4. **🎯 期权（Options）实战组合策略手册 (Options Tactical Playbook)**：
   - **主推期权策略**：明确给出到期日 ({pipe['opt_info']['expiry']})、具体 Buy/Sell 哪一个真实行权价 (Strike)、预估权利金收支、盈亏平衡点以及财报 IV Crush 防护逻辑。
   - **动态移仓 (Roll) 应对手册**：说明若正股大涨突破阻力位、大跌触及支撑位或横盘损耗殆尽时，该如何动态向上/向下/向远期移仓 (Roll)。
5. **👑 基金经理终审裁决**：给出最终五档评级（Buy / Overweight / Hold / Underweight / Sell）与一句话行动纲领。

【重要机器可读闭环指令】：在报告的最末尾，请务必附带以下单行 XML 包裹的 JSON 块（用于反向同步更新系统主控台与期权盈亏图，合法 opt_strat_key 仅限：cash_secured_put, bull_call_spread, covered_call, iron_condor, collar, bear_put_spread, protective_put, straddle）：
<GEMINI_VERDICT_JSON>{{"gemini_rating": "Buy", "gemini_action": "BUY", "gemini_alloc_pct": 20, "gemini_opt_strat_key": "{pipe['opt_strat_key']}", "override_summary": "一句话说明Gemini维持或修正量化模型初判的核心原因"}}</GEMINI_VERDICT_JSON>
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
    原生调用 Google Gemini API：
    优先使用最新 google-genai SDK (client.interactions.create)，
    若本地环境尚未安装 google-genai 包，则自动无缝回退至 Gemini 官方 HTTPS REST 接口，确保零依赖报错！
    """
    clean_key = api_key.strip()
    system_prompt, user_context = build_committee_prompts(engine, pipe, user_cash, user_shares, lang_key)

    # 路径 A：优先使用官方 google-genai SDK (Interactions API)
    try:
        from google import genai
        client = genai.Client(api_key=clean_key)
        if hasattr(client, "interactions"):
            interaction = client.interactions.create(
                model=model_name.strip(),
                system_instruction=system_prompt,
                input=user_context,
            )
            if getattr(interaction, "output_text", None):
                return interaction.output_text
    except Exception:
        pass

    # 路径 B：零依赖 REST API 调用 (Interactions v1 优先，自动兼容 v1beta)
    headers_v1 = {
        "x-goog-api-key": clean_key,
        "Content-Type": "application/json",
    }
    payload_v1 = {
        "model": model_name.strip(),
        "system_instruction": system_prompt,
        "input": user_context,
    }
    try:
        resp_v1 = requests.post(
            "https://generativelanguage.googleapis.com/v1/interactions",
            headers=headers_v1,
            json=payload_v1,
            timeout=90,
        )
        if resp_v1.status_code == 200:
            data = resp_v1.json()
            text_chunks = []
            for step in data.get("steps", []):
                if step.get("type") == "model_output":
                    for part in step.get("content", []):
                        if part.get("type") == "text" and part.get("text"):
                            text_chunks.append(part["text"])
            if text_chunks:
                return "\n".join(text_chunks)
    except Exception:
        pass

    # 兼容备用端点 (适配不同区域 Key 路由)
    fallback_models = [model_name.strip(), "gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]
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

                    if engine.val_dcf and engine.val_dcf > 0:
                        st.markdown(f"### {T['heat_title']}")
                        with st.container(border=True):
                            st.markdown(T['heat_desc'], unsafe_allow_html=True)
                            fig_heat, heat_stats = draw_sensitivity_heatmap(engine)
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
                            st.markdown(f"**3-Year Beta Regression (β = {engine.beta:.2f})**")
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
            # TAB 2: 硬核财报排程 (自动带出公司真实历史 DSO/DIO/DPO/Capex%)
            # ==========================================
            with tab2:
                st.markdown("#### ⚙️ Hardcore 3-Statement Forecast (Real Balance Sheet NWC & Depreciation Engine)")
                tab2_desc = (
                    f"已自动从 `{engine.ticker}` 真实资产负债表与现金流量表反推历史基准参数："
                    f"**DSO={engine.hist_dso}天, DIO={engine.hist_dio}天, DPO={engine.hist_dpo}天, Capex={engine.hist_capex_pct:.1f}%**。"
                    if lang_key == "zh" else
                    f"Automatically initialized from `{engine.ticker}` balance sheet & cash flow statement: "
                    f"**DSO={engine.hist_dso}d, DIO={engine.hist_dio}d, DPO={engine.hist_dpo}d, Capex={engine.hist_capex_pct:.1f}%**."
                )
                st.caption(tab2_desc)

                exp_title_t2 = "📖 【新手必读 / 核心参数调整指南】营运资本与资本开支 (点击展开)" if lang_key == "zh" else "📖 [Beginner's Guide] Working Capital & Capex Drivers (Click to Expand)"

                guide_t2_zh = """
                * **DSO (应收账款天数 - Days Sales Outstanding)**：衡量公司卖出产品后，客户平均需要多少天把现金付清。调大代表客户拖欠加剧（现金流变差）。
                * **DIO (存货天数 - Days Inventory Outstanding)**：衡量货物从生产出来到卖掉平均在仓库躺几天。调大代表存货积压。
                * **DPO (应付账款天数 - Days Payable Outstanding)**：公司平均多少天付钱给上游供应商。调大代表公司对供应链占款能力强（短期自由现金流变好）。
                * **Capex % of Revenue (资本开支占营收比例)**：每年拿多少比例收入买厂房、服务器等固定资产。扩产期调高，维护期调低。
                """
                guide_t2_en = """
                * **DSO (Days Sales Outstanding)**: Days to collect cash from customers after a sale. Higher DSO ties up working capital and reduces FCF.
                * **DIO (Days Inventory Outstanding)**: Days inventory sits in storage before sale. Higher DIO signals inventory buildup.
                * **DPO (Days Payable Outstanding)**: Days taken to pay suppliers. Higher DPO preserves short-term cash flow.
                * **Capex % of Revenue**: Percentage of revenue spent on PP&E/servers. Increase for heavy expansion phases.
                """

                with st.expander(exp_title_t2, expanded=False):
                    st.markdown(guide_t2_zh if lang_key == "zh" else guide_t2_en)

                with st.container(border=True):
                    st.markdown("**🔧 Operating Assumptions (Auto-Calibrated from Financial Statements)**")
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
                        "真实供应链现金周期 (CCC = DSO+DIO-DPO)" if lang_key == "zh" else "Cash Conversion Cycle (CCC)",
                        f"{dso + dio - dpo} Days",
                        "Negative = Supplier Funded" if (dso + dio - dpo) < 0 else "Working Capital Tied Up",
                        delta_color="off"
                    )

                styled_df = df_is.copy()
                for col in styled_df.columns:
                    styled_df[col] = styled_df[col].apply(lambda x: f"{x:,.0f}" if isinstance(x, (int, float)) else x)

                st.dataframe(styled_df, use_container_width=True, height=320)

            # ==========================================
            # TAB 3: LBO (与 Tab 2 EBITDA/UFCF 100% 闭环)
            # ==========================================
            with tab3:
                st.markdown("#### 🏛️ Dynamic LBO Model & Cash Sweep Schedule")
                tab3_desc = "此 LBO 沙盘已与 Tab 2 中的硬核无杠杆现金流 (UFCF) 及第 5 年预测 EBITDA 完美联动。" if lang_key == "zh" else "This LBO is 100% linked to the Hardcore UFCF and Year-5 EBITDA generated in Tab 2."
                st.caption(tab3_desc)

                col_l1, col_l2, col_l3 = st.columns(3)
                ltv = col_l1.slider("Debt Leverage (LTV %)", 30, 80, 60, 5) / 100.0
                int_rate = col_l2.slider("Debt Interest Rate (%)", 5.0, 15.0, 8.0, 0.5) / 100.0
                default_mult = float(np.clip(engine.ev / engine.ebitda if engine.ebitda > 0 else 10.0, 5.0, 25.0))
                exit_mult = col_l3.slider("Exit EV/EBITDA Multiple", 5.0, 25.0, round(default_mult * 2) / 2, 0.5)

                lbo_res = engine.run_lbo_model(ltv, int_rate, exit_mult)

                c_res1, c_res2, c_res3 = st.columns(3)
                c_res1.metric("Sponsor IRR (5-Year)", f"{lbo_res['IRR']*100:.1f}%")
                c_res2.metric("MOIC (Cash-on-Cash)", f"{lbo_res['MOIC']:.2f}x")
                c_res3.metric("Total Debt Paid Down", f"{engine.currency} {(lbo_res['Debt'] - lbo_res['Exit Debt'])/1e9:.2f}B")

                st.markdown("**Sources & Uses (Entry)**")
                su_df = pd.DataFrame({
                    "Sources": ["Sponsor Equity", "Senior Debt", "Total Sources (Entry EV)"],
                    "Amount": [f"{lbo_res['Equity']:,.0f}", f"{lbo_res['Debt']:,.0f}", f"{lbo_res['Entry EV']:,.0f}"],
                    "%": [f"{(1-ltv)*100:.1f}%", f"{ltv*100:.1f}%", "100.0%"]
                })
                st.table(su_df)

                st.markdown("**Debt Schedule & Cash Sweep**")
                debt_df = pd.DataFrame({
                    "Year": ["0 (Entry)", "1", "2", "3", "4", "5"],
                    "Ending Debt Balance": [f"{x:,.0f}" for x in lbo_res['Debt Schedule']]
                })
                st.table(debt_df.set_index('Year').T)

            # ==========================================
            # TAB 4, 5, 6 (并行 Comps + SLSQP 精确马科维茨前沿与资本市场线 CML)
            # ==========================================
            with tab4:
                comp_title = "#### 🏢 相对估值矩阵 (多线程并发同业可比公司)" if lang_key == "zh" else "#### 🏢 Comparable Company Analysis (Parallel Peer Valuation Matrix)"
                st.markdown(comp_title)
                st.dataframe(engine.run_comps_analysis(), use_container_width=True)

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
                st.markdown("#### 📈 Markowitz Efficient Frontier & SLSQP Analytical Optimization (with Capital Market Line)")
                basket_input = st.text_input(
                    "Asset Basket Tickers (Comma-separated)",
                    value="NVDA, AAPL, MSFT, GOOGL, AMZN" if not engine.is_malaysia else "1155.KL, 1023.KL, 1295.KL, 5819.KL"
                )
                tickers_list = [t.strip().upper() for t in basket_input.split(",") if t.strip()]

                if st.button("🚀 Run SLSQP & Monte Carlo Portfolio Optimization" if lang_key == "en" else "🚀 运行 SLSQP 精确解析解 + 蒙特卡洛组合优化"):
                    with st.spinner("Solving exact SLSQP tangency portfolio & simulating cloud..." if lang_key == "en" else "正在通过 SLSQP 二次规划求解全局最大夏普切点组合与资本市场线..."):
                        try:
                            data = fetch_portfolio_history(tuple(tickers_list))
                            valid_cols = [c for c in tickers_list if c in data.columns and data[c].notna().sum() > 20]
                            data = data[valid_cols].dropna()
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

                                # 🌟 优化点 7：使用 scipy.optimize.minimize (SLSQP) 求解精确全局最大夏普组合与最小方差组合
                                init_w = np.ones(n_assets) / n_assets
                                bounds = tuple((0.0, 1.0) for _ in range(n_assets))
                                constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0},)

                                def neg_sharpe(w):
                                    ret = float(np.dot(w, mean_returns))
                                    vol = float(np.sqrt(np.dot(w.T, np.dot(cov_matrix, w))))
                                    return -(ret - engine.rf) / max(vol, 1e-6)

                                def port_vol(w):
                                    return float(np.sqrt(np.dot(w.T, np.dot(cov_matrix, w))))

                                res_sharpe = sco.minimize(neg_sharpe, init_w, method='SLSQP', bounds=bounds, constraints=constraints)
                                res_gmv = sco.minimize(port_vol, init_w, method='SLSQP', bounds=bounds, constraints=constraints)

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

                                opt1, opt2, opt3 = st.columns(3)
                                opt1.metric("Exact Tangency Return", f"{opt_ret*100:.2f}%")
                                opt2.metric("Exact Tangency Volatility", f"{opt_vol*100:.2f}%")
                                opt3.metric("SLSQP Max Sharpe Ratio", f"{opt_sr:.2f}")

                                weight_df = pd.DataFrame({
                                    "Asset": valid_cols,
                                    "Max Sharpe Weight (%)": [f"{w*100:.1f}%" for w in opt_weights],
                                    "Min Variance (GMV) Weight (%)": [f"{w*100:.1f}%" for w in gmv_w]
                                })
                                st.table(weight_df.set_index('Asset').T)

                                fig_ef = px.scatter(
                                    x=p_vols, y=p_rets, color=sharpes,
                                    labels={'x': 'Volatility (Annualized Risk)', 'y': 'Expected Annual Return', 'color': 'Sharpe Ratio'},
                                    title="Markowitz Efficient Frontier & Capital Market Line (SLSQP Exact Solution)"
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

            # ==========================================
            # TAB 7: 期权链与 B-S 沙盘
            # ==========================================
            with tab7:
                st.markdown("#### 📉 Options Chain, Volatility Smile & BS Interactive Sandbox")
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
                            "🛡️ 实时平值期权链与希腊字母矩阵" if lang_key == "zh" else "🛡️ Live ATM Option Chain & Greeks",
                            "🧮 独立 B-S 仿真沙盘 (Interactive Sandbox)" if lang_key == "zh" else "🧮 BS Interactive Sandbox"
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
                                    raw_iv = float(row.get('impliedVolatility') or 0.0)
                                    iv = raw_iv if raw_iv > 0.01 else 0.35
                                    greeks = engine.black_scholes_pricing(S, K, T_years, r, iv, q=q_yield)
                                    bs_results.append({
                                        "Strike": K,
                                        "Moneyness": "ATM" if abs(K - S) / S < 0.02 else ("ITM" if (K < S if is_call_view else K > S) else "OTM"),
                                        "Market Last": row['lastPrice'],
                                        "BS Fair Price": round(greeks['Call' if is_call_view else 'Put'], 2),
                                        "IV (%)": round(iv * 100, 1),
                                        "Delta": round(greeks['Delta_C' if is_call_view else 'Delta_P'], 3),
                                        "Gamma": round(greeks['Gamma'], 4),
                                        "Theta (Daily)": round(greeks['Theta_C' if is_call_view else 'Theta_P'], 3),
                                        "Vega": round(greeks['Vega'], 3)
                                    })
                                st.dataframe(pd.DataFrame(bs_results), use_container_width=True)

                        with opt_tab3:
                            op_col1, op_col2, op_col3 = st.columns(3)
                            strike_pct = op_col1.slider("行权价设定 (% 相对现价)" if lang_key == "zh" else "Strike Price Setting (%)", 80, 120, 100, 1) / 100.0
                            custom_K = op_col2.number_input("行权价 (Strike K)" if lang_key == "zh" else "Strike (K)", value=float(engine.price * strike_pct), format="%.2f")
                            custom_T_days = op_col3.number_input("剩余到期天数 (Days to Maturity)" if lang_key == "zh" else "Days to Maturity", value=30, min_value=1, max_value=730)

                            op_col4, op_col5, op_col6 = st.columns(3)
                            custom_vol = op_col4.slider("波动率 (Volatility σ %)" if lang_key == "zh" else "Volatility (IV σ %)", 10.0, 150.0, 35.0, 1.0) / 100.0
                            custom_r_rate = op_col5.slider("无风险利率 (Risk-Free Rate r %)" if lang_key == "zh" else "Risk-Free Rate (r %)", 1.0, 10.0, float(engine.rf * 100), 0.1) / 100.0
                            custom_div_yield = op_col6.slider("股息率 (Dividend Yield q %)" if lang_key == "zh" else "Dividend Yield (q %)", 0.0, 10.0, 1.5, 0.1) / 100.0

                            custom_greeks = engine.black_scholes_pricing(engine.price, custom_K, custom_T_days / 365.0, custom_r_rate, custom_vol, custom_div_yield)
                            res_c1, res_c2 = st.columns(2)
                            res_c1.metric("European Call (看涨公道价)" if lang_key == "zh" else "European Call Premium", f"{engine.currency} {custom_greeks['Call']:.4f}")
                            res_c2.metric("European Put (看跌公道价)" if lang_key == "zh" else "European Put Premium", f"{engine.currency} {custom_greeks['Put']:.4f}")
                    else:
                        st.info("ℹ️ 当前标的暂无交易所公开期权链，您可以直接前往 **Tab [8] TradingAgents 投委会与期权作战室** 使用合成 B-S 期权策略引擎！" if lang_key == "zh" else "ℹ️ No exchange-listed option chain found; visit Tab [8] for synthetic B-S option strategy modeling!")
                except Exception as e:
                    st.error(f"Option chain error: {e}")

            # ==================================================================
            # 🌟 TAB 8: TradingAgents 多智能体投委会辩论与期权协同作战室 (V11.0 满血融合)
            # ==================================================================
            with tab8:
                st.markdown(
                    "### 🤖 TradingAgents Multi-Agent Investment Committee & Options Desk (V11.0)"
                    if lang_key == "en" else
                    "### 🤖 TradingAgents 多智能体投委会辩论与期权作战室 (V11.0 双向闭环满血版)"
                )
                st.caption(
                    "完美复刻 TauricResearch/TradingAgents 五阶段投委会工作流，内置财报日 IV Crush 雷达、双曲线期权盈亏仿真与 Google Gemini 双向闭环裁决系统。"
                    if lang_key == "zh" else
                    "Mirrors the 5-stage TauricResearch/TradingAgents workflow with Earnings IV Crush Radar, Dual-Curve Payoff Simulation, and Google Gemini Bidirectional Verdict Override."
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

                # 财报日 IV Crush 横幅预警
                if opt_info.get("earnings_alert"):
                    st.warning(
                        f"⚡ **【财报日跨期波动率坍塌预警 (Earnings IV Crush Alert)】**：检测到 `{engine.ticker}` 将于 **{opt_info['earnings_date']}**（约 **{opt_info['days_to_earnings']} 天后**）发布财报，落在当前主力期权周期 (`{opt_info['expiry']}`) 内！"
                        f"平值跨式期权隐含财报波幅为 **±{opt_info['implied_move_pct']:.1f}%**。系统已自动规避裸买单腿期权与窄幅裸卖策略，优先采用价差（Spread）锁定风险！"
                    )

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
                            f"- **MACD Hist:** `{tech['macd_hist']:+.3f}`\n"
                            f"- **14D ATR 波动:** `{engine.currency} {tech['atr']:.2f}`\n"
                            f"- **支撑 / 阻力位:** `{tech['support']:.2f}` / `{tech['resistance']:.2f}`"
                        )

                with a_col2:
                    with st.container(border=True):
                        st.markdown("<span class='agent-badge' style='background:rgba(16,185,129,0.2);color:#10b981;'>📊 FUNDAMENTALS ANALYST</span>", unsafe_allow_html=True)
                        st.markdown(f"**主推模型:** `{engine.model_name[:18]}`")
                        st.markdown(
                            f"- **内在公允价:** `{engine.currency} {engine.fair_val:.2f}`\n"
                            f"- **安全边际 (MoS):** `{pipe['mos_pct']:+.1f}%`\n"
                            f"- **WACC 折现门槛:** `{engine.wacc*100:.2f}%`\n"
                            f"- **三表真实 NWC DCF:** `{engine.currency} {(engine.val_3stmt_dcf or engine.fair_val):.2f}`\n"
                            f"- **现金转换周期 (CCC):** `{engine.hist_dso + engine.hist_dio - engine.hist_dpo} 天`"
                        )

                with a_col3:
                    with st.container(border=True):
                        st.markdown("<span class='agent-badge' style='background:rgba(245,158,11,0.2);color:#f59e0b;'>📰 NEWS & SENTIMENT</span>", unsafe_allow_html=True)
                        st.markdown(f"**隐含增长率:** `{pipe['implied_g_pct']:.1f}% / 年`")
                        st.markdown(
                            f"- **华尔街目标均值:** `{engine.currency} {pipe['target_mean']:.2f}` ({pipe['ws_upside']:+.1f}%)\n"
                            f"- **下一季财报日:** `{opt_info.get('earnings_date', 'N/A')}`\n"
                            f"- **最新头条监控:**\n" +
                            ("\n".join([f"  - *{ h[:48] }...*" for h in pipe["news"][:2]]) if pipe["news"] else "  - *暂无突发黑天鹅新闻*")
                        )

                with a_col4:
                    with st.container(border=True):
                        st.markdown("<span class='agent-badge' style='background:rgba(168,85,247,0.2);color:#c084fc;'>🎯 OPTIONS & VOL ANALYST</span>", unsafe_allow_html=True)
                        st.markdown(f"**主力合约:** `{opt_info['expiry']}`")
                        st.markdown(
                            f"- **平值隐含波动率 (IV):** `{opt_info['atm_iv']*100:.1f}%` (HV `{tech['hv30']*100:.1f}%`)\n"
                            f"- **IV / HV 溢价倍数:** `{opt_info['iv_hv_ratio']:.2f}x` ({'期权偏贵-宜卖方/价差' if opt_info['iv_hv_ratio']>=1.15 else '期权便宜-宜买方'})\n"
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
                        f"即便短期股价横盘，我们也可以利用当前 `{opt_info['atm_iv']*100:.1f}%` 的隐含波动率，通过期权策略收割权利金或构建低成本垂直价差，持仓胜率极高。"
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
                        f"**[第一轮立论 - 估值透支与均值回归风险]** 当前市价 `{engine.currency} {engine.price:.2f}` 对比模型公允价 `{engine.fair_val:.2f}` 的安全边际为 `{pipe['mos_pct']:+.1f}%`。"
                        f"测谎仪显示市场当前定价隐含了未来 `{engine.horizon}` 年每年 `{pipe['implied_g_pct']:.1f}%` 的增长预期！"
                        f"一旦下季度财报增速略微放缓或营运资本 DSO ({engine.hist_dso}天) 拉长，将面临剧烈的戴维斯双杀。"
                    )
                    bear_r2 = (
                        f"**[第二轮反驳多方 - 技术与波动率尾部风险]** 技术指标 RSI 目前处于 `{tech['rsi']:.1f}`，且期权市场 Put-Call 偏度为 `{opt_info['skew']:+.1f}%`，"
                        f"期权跨式隐含波动幅度达 `±{opt_info.get('implied_move_pct', 0.0):.1f}%`。上方 `{tech['resistance']:.2f}` 阻力重重，盲目裸多正股极易在波动中受损！"
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
                        f"**初步投研评级: `{pipe['final_rating'].upper()}` (综合量化得分: `{pipe['total_score']:+.1f}`)**"
                    )
                    st.write(
                        f"综合多空双方 {debate_rounds} 轮辩论：基本面估值偏离度为 `{pipe['mos_pct']:+.1f}%`，技术面处于 `{tech['trend']}` 格局。"
                        f"研究部决定不采取简单的‘全仓梭哈’或‘盲目看空’，而是向交易台下达 **【正股关键点位挂单 + 期权波动率套利/保护】** 的复合战略指令。"
                    )

                st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

                # --------------------------------------------------------------
                # STAGE 3: 交易员现货与期权协同作战方案 (Trader & Options Desk)
                # --------------------------------------------------------------
                st.markdown("#### 💼 第三阶段：交易员【正股 + 期权】协同作战指令单 (Stage 3: Equity & Options Trader Desk)" if lang_key == "zh" else "#### 💼 Stage 3: Equity & Options Trader Execution Desk")
                t_col1, t_col2 = st.columns([1.1, 1.4])

                with t_col1:
                    with st.container(border=True):
                        st.markdown("<span class='agent-badge' style='background:rgba(56,189,248,0.2);color:#38bdf8;'>💵 SPOT EQUITY ORDER (正股交易提案)</span>", unsafe_allow_html=True)
                        st.markdown(f"##### 执行方向: `{pipe['trader_action']}`  |  建议仓位: `{pipe['alloc_pct']:.0f}%`")
                        suggested_shares = int((user_cash * (pipe['alloc_pct'] / 100.0)) // engine.price) if engine.price > 0 else 0
                        st.markdown(
                            f"- **参考建仓/挂单价 (Entry):** `{engine.currency} {pipe['entry_price']:.2f}`\n"
                            f"- **ATR 硬性止损位 (Stop-Loss):** `{engine.currency} {pipe['stop_loss']:.2f}` (基于 2x ATR 与 20日支撑位)\n"
                            f"- **第一止盈目标位 (Take-Profit):** `{engine.currency} {pipe['take_profit']:.2f}`\n"
                            f"- **按可用现金折算股数:** 约 `{suggested_shares:,}` 股 (现有持仓 `{user_shares}` 股)"
                        )

                with t_col2:
                    with st.container(border=True):
                        st.markdown("<span class='agent-badge' style='background:rgba(16,185,129,0.25);color:#10b981;'>🎯 OPTIONS TACTICAL ORDER (衍生品期权作战指令)</span>", unsafe_allow_html=True)
                        st.markdown(f"##### 推荐策略: {pipe['opt_strategy_name']}")
                        st.markdown(f"- **具体合约操作:** {pipe['opt_action_detail']}")
                        st.info(f"💡 **期权交易员逻辑 (Options Desk Rationale):** {pipe['opt_rationale']}")

                with st.container(border=True):
                    st.markdown(f"**📊 交易台推荐期权策略双曲线盈亏仿真 ({pipe['opt_strategy_name']})**")
                    fig_ta_payoff, ta_max_p, ta_max_l = draw_option_payoff_diagram(
                        engine, pipe["opt_strat_key"], opt_info["T_years"], opt_info["atm_iv"], lang_key, pipe["opt_legs_meta"]
                    )
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
                            f"**激进派风控意见：** 若只用轻仓正股，资金效率太低。建议利用期权非线性凸性（Gamma），"
                            f"将部分正股预算置换为 `{opt_info['expiry']}` 到期的看涨价差或卖 Put，以小博大放大名义敞口回报率。"
                        )

                with r_col2:
                    with st.container(border=True):
                        st.markdown("<span class='agent-badge' style='background:rgba(59,130,246,0.2);color:#60a5fa;'>🛡️ CONSERVATIVE RISK DEBATOR</span>", unsafe_allow_html=True)
                        st.write(
                            f"**保守派风控意见：** 标的单日 ATR 波动为 `{engine.currency} {tech['atr']:.2f}`，Beta 为 `{engine.beta:.2f}`。"
                            f"必须严格执行 `{engine.currency} {pipe['stop_loss']:.2f}` 的止损纪律！期权端严禁裸卖空 Call（Naked Short Call），必须采用价差或备兑锁死尾部风险。"
                        )

                with r_col3:
                    with st.container(border=True):
                        st.markdown("<span class='agent-badge' style='background:rgba(16,185,129,0.2);color:#34d399;'>⚖️ NEUTRAL RISK DEBATOR</span>", unsafe_allow_html=True)
                        st.write(
                            f"**中立派风控意见：** 折中激进派与保守派诉求，最佳方案是 **【现货底仓 + {pipe['opt_strategy_name'].split('(')[0]}】** 组合。"
                            f"既保留了基本面价值回归的收益，又通过期权封住了最大回撤并赚取波动率溢价。"
                        )

                st.markdown(
                    f"""
                    <div class="debate-card-pm">
                        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;">
                            <div style="color:#38bdf8;font-weight:800;font-size:18px;">👑 投资组合经理终审决议 (Portfolio Manager Final Decision)</div>
                            <div style="background:linear-gradient(135deg,#10b981,#059669);color:#fff;padding:5px 16px;border-radius:999px;font-weight:800;font-size:15px;">
                                QUANT RATING: {pipe['final_rating'].upper()}
                            </div>
                        </div>
                        <hr style="border-color:rgba(255,255,255,0.1);margin:12px 0;">
                        <p style="font-size:14px;line-height:1.7;margin-bottom:8px;">
                            <b>1. 终审定调：</b> 综合四大分析师硬核数据、多空辩论及三方风控意见，批准对 <b>{engine.name} ({engine.ticker})</b> 赋予 <b>【{pipe['final_rating']}】</b> 机构评级。<br>
                            <b>2. 现货执行批示：</b> 建议目标仓位配比 <b>{pipe['alloc_pct']:.0f}%</b>，参考入场位 <b>{engine.currency} {pipe['entry_price']:.2f}</b>，铁律止损位 <b>{engine.currency} {pipe['stop_loss']:.2f}</b>，目标止盈位 <b>{engine.currency} {pipe['take_profit']:.2f}</b>。<br>
                            <b>3. 期权协同批示：</b> 同步执行 <b>【{pipe['opt_strategy_name']}】</b>（{pipe['opt_action_detail']}），利用期权隐含波动率 (IV={opt_info['atm_iv']*100:.1f}%) 实现风险收益比最优化。
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
                # 🌟 STAGE 6: Google Gemini API 首席投委会双向闭环推演 (原生专属模块)
                # --------------------------------------------------------------
                st.markdown(
                    "#### ✨ 第六阶段：Google Gemini AI 首席投委会双向闭环推演与期权实战书 (Powered by Gemini API)"
                    if lang_key == "zh" else
                    "#### ✨ Stage 6: Google Gemini AI Bidirectional Closed-Loop Investment Committee"
                )
                with st.container(border=True):
                    st.caption(
                        "💡 **专属原生 Gemini 双向闭环引擎**：自动将上方算出的 **100% 真实 DCF/三表估值、财报 IV Crush 雷达、历史记忆账本盈亏、以及最新 8 条实时财经新闻** 注入 Google Gemini。Gemini 辩论后不仅输出深度研报，还会自动生成 **【双向闭环修正裁决卡】** 与修正后的期权盈亏图！"
                        if lang_key == "zh" else
                        "💡 **Native Gemini Closed-Loop Engine**: Injects 100% of your DCF/3-Statement metrics, Earnings IV radar, Episodic Memory ledger, and live headlines into Google Gemini, returning both a deep report and a bidirectional strategy override."
                    )
                    saved_gem_key = load_saved_gemini_key()
                    g_col1, g_col2, g_col3, g_col4 = st.columns([1.5, 1.0, 0.75, 0.85])
                    gemini_key_in = g_col1.text_input(
                        "🔑 Google Gemini API Key (填一次自动保存)" if lang_key == "zh" else "🔑 Google Gemini API Key",
                        value=saved_gem_key,
                        type="password",
                        placeholder="AIzaSy..."
                    )
                    gemini_model_in = g_col2.selectbox(
                        "🤖 选择 Gemini 模型 (Model)" if lang_key == "zh" else "🤖 Select Gemini Model",
                        options=[
                            "gemini-3.8-flash",
                            "gemini-4-argon",
                            "gemini-3.5-flash-lite",
                            "gemini-3.1-flash-lite"
                        ],
                        index=0
                    )
                    remember_key = g_col3.checkbox(
                        "💾 本机记住 Key" if lang_key == "zh" else "💾 Remember Key",
                        value=True
                    )
                    auto_debate = g_col4.checkbox(
                        "⚡ 自动与模型辩论" if lang_key == "zh" else "⚡ Auto-Debate",
                        value=bool(saved_gem_key)
                    )

                    run_gem_now = st.button("✨ 立即让【量化模型】与【Google Gemini】展开深度辩论 & 双向修正期权策略", use_container_width=True)
                    report_cache_key = f"gemini_report_{engine.ticker}_{gemini_model_in}_{user_shares}"

                    if run_gem_now or (auto_debate and gemini_key_in.strip() and report_cache_key not in st.session_state):
                        if not gemini_key_in.strip():
                            st.warning("⚠️ 请先在上方输入框填入您的 Google Gemini API Key（以 `AIza` 开头），或填写在代码 `DEFAULT_GEMINI_API_KEY` 中。")
                        else:
                            if remember_key:
                                save_gemini_key_local(gemini_key_in)
                            with st.spinner(f"正在让您的量化数学引擎与 Google {gemini_model_in} 进行多轮交锋与双向闭环期权推演..."):
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

                        # 🌟 优化点 5：渲染【量化模型初判 vs Gemini 辩论终判】双向闭环对比卡
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
                                        <span style="color:#94a3b8;">📊 量化模型初判评级：</span><br>
                                        <b>{pipe['final_rating'].upper()} ({pipe['trader_action']} | 仓位 {pipe['alloc_pct']:.0f}%)</b>
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

                        # 若 Gemini 调整了期权策略结构，则自动渲染 Gemini 钦定期权策略的盈亏图
                        valid_strat_keys = {"cash_secured_put", "bull_call_spread", "covered_call", "iron_condor", "collar", "bear_put_spread", "protective_put", "straddle"}
                        gem_strat_k = str(gem_verdict.get("gemini_opt_strat_key") or "").strip().lower()
                        if gem_strat_k in valid_strat_keys and gem_strat_k != pipe["opt_strat_key"]:
                            st.markdown(f"**📈 Gemini 辩论修正后的期权策略盈亏仿真 (`{gem_strat_k.upper()}`)**")
                            fig_gem_payoff, _, _ = draw_option_payoff_diagram(
                                engine, gem_strat_k, opt_info["T_years"], opt_info["atm_iv"], lang_key, pipe["opt_legs_meta"]
                            )
                            st.plotly_chart(fig_gem_payoff, use_container_width=True)

                        st.markdown(clean_gem_md)

                        # 🌟 优化点 9：一键导出完整 Markdown 投研与期权作战书
                        export_md = (
                            f"# {engine.name} ({engine.ticker}) — 量化估值与 Google Gemini 多智能体期权作战书\n"
                            f"- **生成日期**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                            f"- **当前现价**: {engine.currency} {engine.price:.2f} | **内在公允价**: {engine.currency} {engine.fair_val:.2f} (MoS: {pipe['mos_pct']:+.1f}%)\n"
                            f"- **三表动态 DCF**: {engine.currency} {(engine.val_3stmt_dcf or 0):.2f} | **WACC**: {engine.wacc*100:.2f}%\n"
                            f"- **量化初判**: {pipe['final_rating']} ({pipe['opt_strategy_name']}) | **Gemini 终判**: {gem_verdict['gemini_rating']} ({gem_verdict['gemini_opt_strat_key']})\n\n"
                            f"---\n\n{clean_gem_md}\n"
                        )
                        st.download_button(
                            label="📥 一键下载完整【量化估值 + Gemini 辩论 + 期权作战书】(.md)",
                            data=export_md.encode("utf-8"),
                            file_name=f"{engine.ticker}_Quant_Gemini_Playbook_{datetime.datetime.now().strftime('%Y%m%d')}.md",
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
