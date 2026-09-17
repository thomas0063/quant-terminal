import datetime
import numpy as np
import pandas as pd
import requests
import yfinance as yf
import streamlit as st
import plotly.graph_objects as go

try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

# ==============================================================================
# 1. 页面基本配置
# ==============================================================================
st.set_page_config(
    page_title="StockVal Pro - 智能股票公道价估值器",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==============================================================================
# 2. StockVal Pro 经典天蓝极客设计系统 (Fintech Dark Glassmorphism + 冰蓝边框)
# ==============================================================================
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

/* 全局主背景与文字渲染 */
.stApp {
    background: radial-gradient(circle at 50% 0%, #131c31 0%, #0b0f19 60%, #060911 100%) !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    color: #f8fafc !important;
}

header[data-testid="stHeader"] {
    background: transparent !important;
}
.block-container {
    padding-top: 1.8rem !important;
    padding-bottom: 3.5rem !important;
    max-width: 1280px !important;
}

/* 🌟 核心：为所有便当盒卡片加上精致、清晰的冰蓝色高级边框与深蓝实底 */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: linear-gradient(135deg, rgba(19, 27, 46, 0.9) 0%, rgba(11, 15, 25, 0.95) 100%) !important;
    border: 1px solid rgba(56, 189, 248, 0.35) !important; /* 精致的天蓝色边界 */
    border-radius: 14px !important;
    padding: 20px 22px !important;
    box-shadow: 0 8px 24px -4px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.08) !important;
    transition: all 0.25s ease !important;
    margin-bottom: 14px !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border-color: #38bdf8 !important;
    box-shadow: 0 10px 30px -4px rgba(56, 189, 248, 0.25) !important;
    transform: translateY(-2px);
}

/* 现代科技感按钮 */
.stButton > button {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%) !important;
    color: #38bdf8 !important;
    border: 1px solid rgba(56, 189, 248, 0.3) !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    padding: 6px 14px !important;
    transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1) !important;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.25) !important;
}
.stButton > button:hover {
    border-color: #38bdf8 !important;
    background: rgba(56, 189, 248, 0.15) !important;
    color: #ffffff !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 18px -2px rgba(56, 189, 248, 0.4) !important;
}

/* 搜索与输入框 */
div[data-baseweb="input"] > div, div[data-baseweb="select"] > div {
    background-color: #131b2e !important;
    border: 1px solid rgba(56, 189, 248, 0.3) !important;
    border-radius: 8px !important;
    color: #ffffff !important;
    box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.2) !important;
}
div[data-baseweb="input"] input {
    color: #ffffff !important;
    font-family: 'JetBrains Mono', monospace !important;
}

/* 标题美化 */
h1, h2, h3, h4, h5 { font-family: 'Inter', sans-serif !important; font-weight: 700 !important; color: #ffffff !important; }
h3 { color: #38bdf8 !important; margin-top: 10px !important; margin-bottom: 15px !important; }

/* 数字等宽 */
.mono-num { font-family: 'JetBrains Mono', monospace !important; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ==============================================================================
# 3. 国际化多语言字典 (I18N: 中文 / English)
# ==============================================================================
TEXTS = {
    "zh": {
        "title": "StockVal Pro",
        "badge_engine": "AI 内在价值测算引擎 v2.5",
        "subtitle": "多维度股票公允价值测算平台 | 深度支持马来西亚股市 (Bursa) 与美股 (US Equities)",
        "market_label": "📌 步骤 1：挑选热门股票或自选代码",
        "market_my": "🇲🇾 马来西亚股市 (Bursa)",
        "market_us": "🇺🇸 美国股市 (US Equities)",
        "market_custom": "🔍 手动输入代码 (Custom Ticker)",
        "choose_stock": "从热门股票池中快速挑选：",
        "custom_label": "输入股票代码：",
        "custom_help": "马股请加 .KL (如: 1155.KL)；美股直接输入代码 (如: AAPL, NVDA)",
        "custom_placeholder": "例如: 1155.KL 或 AAPL",
        "quick_tag": "🔥 热门标的秒选：",
        "btn_analyze": "开始测算",
        
        "param_header": "⚙️ 步骤 2：估值核心参数设定 (建议保持默认)",
        "param_terminal_g": "长期永续通胀增长率 (Terminal Growth Rate)",
        "param_terminal_g_help": "指公司成熟稳定后，永久跟随国家经济与通胀的微小增长率。保持 2.5% 即可！",
        "param_erp": "股市风险溢价要求 (Equity Risk Premium)",
        "param_erp_help": "投资股票相比于国债所期望的额外回报补偿。通常为 5.5%。",
        
        "result_header": "📊 步骤 3：三大估值模型横向对比与综合结论",
        "curr_price": "当前市场价格",
        "fair_price_rec": "系统推荐公道价",
        "verdict_title": "综合投资诊断",
        "verdict_under": "🟢 明显低估 (划算 / 打折中)",
        "verdict_over": "🔴 明显高估 (偏贵 / 溢价中)",
        "verdict_fair": "⚖️ 估值合理 (价格适中)",
        "upside_prefix": "较当前市价有潜在上涨空间",
        "downside_prefix": "较公道价溢价",
        
        "model_dcf_name": "两阶段现金流贴现 (DCF)",
        "model_ddm_name": "股息分红贴现 (DDM)",
        "model_pe_name": "市盈率倍数估值 (P/E)",
        "badge_recommended": "⭐ 主要推荐",
        "badge_reference": "📌 参考指标",
        "no_data": "暂无有效数据",
        "no_data_dcf": "现金流为负或数据不足",
        "no_data_ddm": "该公司不派发股息",
        "no_data_pe": "公司目前处于净亏损",
        
        "glossary_header": "📖 小白通俗金融词典：这些数据代表什么？",
        "card_beta_title": "波动敏感度 (Beta)",
        "card_beta_desc": "衡量这只股票相对于大盘是更活泼还是更稳健。<br>• <b>Beta > 1</b>：涨跌比大盘更猛<br>• <b>Beta < 1</b>：抗跌防守属性强",
        "card_growth_title": "预期增长率 (Growth)",
        "card_growth_desc": "未来 5 年公司自由现金流预计每年递增的比例。增长越快，公道身价越高。",
        "card_wacc_title": "投资及格线回报率 (WACC)",
        "card_wacc_desc": "你买入这家公司所要求的最低年化回报门槛。风险越高要求越高。",
        "card_fair_title": "内在公允价值 (Fair Value)",
        "card_fair_desc": "剥离市场短期情绪，根据公司真实资产、欠债与造血能力算出的出厂公道价。",

        "chart_header": "📈 步骤 4：多周期蜡烛走势图与量化特征图",
        "timeframe_label": "切换 K 线蜡烛图周期：",
        "chart_history_title": "交互式 K 线蜡烛走势图 (Candlestick)",
        "chart_legend": "🟢 绿色表示收盘上涨 (阳线) | 🔴 红色表示收盘下跌 (阴线)",
        "chart_beta_title": "Beta 收益率特征线散点分布图",
        "chart_beta_exp": "红线斜率即为真实 Beta（马股对标 MSCI Malaysia ETF，美股对标 S&P 500）。",
        
        "ws_header": "🏛️ 华尔街专业投行分析师共识 (Wall Street View)",
        "ws_mean": "投行平均目标价",
        "ws_range": "目标价区间",
        "ws_rating": "投行综合评级",
        "ws_match": "✅ 你的模型计算与华尔街机构分析师共识高度吻合！",
        
        "disclaimer_title": "⚠️ 重要法律与风险免责声明",
        "disclaimer_content": (
            "1. <b>非投资建议</b>：本平台呈现的所有估值结果、公道价格、诊断与图表分析，仅供学术研究、个人学习交流与教学参考，不构成任何买卖要约或财务建议。<br>"
            "2. <b>市场风险</b>：股票市场波动剧烈，历史数据和数学量化模型无法预知未来突发事件。<br>"
            "3. <b>自主决策</b>：任何投资决策均应由投资者在独立调查或咨询持牌财务顾问的基础上自行做出。"
        )
    },
    "en": {
        "title": "StockVal Pro",
        "badge_engine": "AI Intrinsic Engine v2.5",
        "subtitle": "Beginner-Friendly Multi-Model Valuation Platform | Supports Bursa Malaysia & US Equities",
        "market_label": "📌 Step 1: Select Popular Stock or Custom Ticker",
        "market_my": "🇲🇾 Bursa Malaysia",
        "market_us": "🇺🇸 US Equities",
        "market_custom": "🔍 Custom Ticker",
        "choose_stock": "Quick pick from popular pools:",
        "custom_label": "Enter Stock Ticker Symbol:",
        "custom_help": "For Malaysian stocks add .KL (e.g., 1155.KL); for US stocks enter ticker (e.g., AAPL, NVDA)",
        "custom_placeholder": "e.g., 1155.KL or AAPL",
        "quick_tag": "🔥 Quick Suggestions:",
        "btn_analyze": "Analyze",
        
        "param_header": "⚙️ Step 2: Core Valuation Assumptions (Defaults Recommended)",
        "param_terminal_g": "Perpetual / Terminal Growth Rate (g)",
        "param_terminal_g_help": "The long-term perpetual growth rate once company matures. 2.5% is standard.",
        "param_erp": "Equity Risk Premium (ERP)",
        "param_erp_help": "The extra return expected for taking stock risk. Typically 5.5%.",
        
        "result_header": "📊 Step 3: Multi-Model Valuation Matrix & Final Verdict",
        "curr_price": "Current Market Price",
        "fair_price_rec": "System Recommended Fair Value",
        "verdict_title": "Diagnostic Summary",
        "verdict_under": "🟢 UNDERVALUED (On Sale)",
        "verdict_over": "🔴 OVERVALUED (Expensive)",
        "verdict_fair": "⚖️ FAIRLY VALUED",
        "upside_prefix": "Potential upside: ",
        "downside_prefix": "Trading at a premium: ",
        
        "model_dcf_name": "Two-Stage DCF Model",
        "model_ddm_name": "Dividend Discount Model (DDM)",
        "model_pe_name": "P/E Multiples Valuation",
        "badge_recommended": "⭐ Recommended",
        "badge_reference": "📌 Reference",
        "no_data": "No Valid Data",
        "no_data_dcf": "Negative or Missing Cash Flows",
        "no_data_ddm": "Company pays no dividend",
        "no_data_pe": "Company in net loss",
        
        "glossary_header": "📖 Beginner's Financial Glossary: What do these numbers mean?",
        "card_beta_title": "Volatility Sensitivity (Beta)",
        "card_beta_desc": "Measures stock swing compared to benchmark.<br>• <b>Beta > 1</b>: High elasticity<br>• <b>Beta < 1</b>: Defensive",
        "card_growth_title": "Expected Growth Rate",
        "card_growth_desc": "Forecasted annual growth rate in cash generation over next 5 years.",
        "card_wacc_title": "Hurdle Discount Rate (WACC)",
        "card_wacc_desc": "Minimum annual hurdle return required by investors.",
        "card_fair_title": "Intrinsic Fair Value",
        "card_fair_desc": "Authentic 'factory price' per share stripping away hype.",

        "chart_header": "📈 Step 4: Multi-Timeframe Candlestick & Regression Analysis",
        "timeframe_label": "Select Candlestick Timeframe:",
        "chart_history_title": "Interactive Stock Candlestick Chart",
        "chart_legend": "🟢 Green: Bullish | 🔴 Red: Bearish",
        "chart_beta_title": "Beta Characteristic Line & Scatter Plot",
        "chart_beta_exp": "Slope of the red line is Beta.",
        
        "ws_header": "🏛️ Wall Street Analyst Consensus (US Equities)",
        "ws_mean": "Analyst Consensus Target Price",
        "ws_range": "Analyst High / Low Range",
        "ws_rating": "Overall Consensus Rating",
        "ws_match": "✅ Your valuation closely aligns with Wall Street institutional targets!",
        
        "disclaimer_title": "⚠️ Important Legal & Risk Disclaimer",
        "disclaimer_content": (
            "1. <b>Educational Purposes Only</b>: All valuation models are for academic research only.<br>"
            "2. <b>Market Risk</b>: Equity investments involve substantial capital risk.<br>"
            "3. <b>Independent Decision</b>: Investors must exercise their own independent judgement."
        )
    }
}

# ==============================================================================
# 4. 品牌顶栏与语言切换区
# ==============================================================================
col_logo, col_lang = st.columns([4.2, 1.2])
with col_lang:
    selected_lang = st.selectbox("🌐 Language / 语言", options=["中文", "English"], index=0)
    lang_key = "zh" if selected_lang == "中文" else "en"
    T = TEXTS[lang_key]

with col_logo:
    st.markdown(
        f"""
        <div style="display: flex; align-items: center; gap: 12px; margin-top: 4px;">
            <div style="background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%); width: 44px; height: 44px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 22px; box-shadow: 0 4px 12px rgba(2, 132, 199, 0.4);">
                💎
            </div>
            <div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 24px; font-weight: 800; letter-spacing: -0.5px; color: #ffffff;">{T['title']}</span>
                    <span style="background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 20px; text-transform: uppercase;">{T['badge_engine']}</span>
                </div>
                <div style="color: #94a3b8; font-size: 13px; font-weight: 400; margin-top: 2px;">{T['subtitle']}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

# ==============================================================================
# 5. 股票选择器与搜索
# ==============================================================================
st.markdown(f"#### {T['market_label']}")

MY_STOCKS = [
    ("1155.KL", "Maybank (马来亚银行 - 金融分红王)"),
    ("1295.KL", "Public Bank (大众银行 - 稳健金融巨头)"),
    ("5347.KL", "Tenaga Nasional (国家能源 - 公用事业基建)"),
    ("0166.KL", "Inari Amertron (益纳利 - 科技半导体芯片)"),
    ("5211.KL", "Sunway (双威集团 - 综合地产医疗)"),
    ("7113.KL", "Top Glove (顶级手套 - 医疗制造)"),
    ("5296.KL", "MR D.I.Y. (大型家装零售连锁)"),
    ("5183.KL", "PetChem (国油石化 - 能源化工龙头)")
]

US_STOCKS = [
    ("AAPL", "Apple Inc. (苹果公司 - 消费电子与生态)"),
    ("NVDA", "NVIDIA Corporation (英伟达 - 全球 AI 算力芯片)"),
    ("TSLA", "Tesla Inc. (特斯拉 - 电动车与机器人)"),
    ("MSFT", "Microsoft (微软 - 企业软件与云计算)"),
    ("GOOGL", "Alphabet Inc. (谷歌 - 全球搜索与云原生)"),
    ("AMZN", "Amazon.com (亚马逊 - 全球电商与 AWS)"),
    ("META", "Meta Platforms (Meta - 社交网络与大模型)"),
    ("JPM", "JPMorgan Chase (摩根大通 - 华尔街银行巨头)")
]

my_opts = [f"{t} | {name}" for t, name in MY_STOCKS]
us_opts = [f"{t} | {name}" for t, name in US_STOCKS]

if "active_ticker" not in st.session_state:
    st.session_state["active_ticker"] = "NVDA"
if "active_market" not in st.session_state:
    st.session_state["active_market"] = "US"
if "radio_market_key" not in st.session_state:
    st.session_state["radio_market_key"] = "US"

def select_stock_quick(ticker, market):
    st.session_state["active_ticker"] = ticker
    st.session_state["active_market"] = market
    st.session_state["radio_market_key"] = market
    if market == "US":
        for opt in us_opts:
            if opt.startswith(ticker):
                st.session_state["us_dropdown_widget"] = opt
                break
    elif market == "MY":
        for opt in my_opts:
            if opt.startswith(ticker):
                st.session_state["my_dropdown_widget"] = opt
                break

st.write(T["quick_tag"])
q_cols = st.columns(6)
q_cols[0].button("🇺🇸 NVDA", use_container_width=True, on_click=select_stock_quick, args=("NVDA", "US"))
q_cols[1].button("🇺🇸 AAPL", use_container_width=True, on_click=select_stock_quick, args=("AAPL", "US"))
q_cols[2].button("🇺🇸 TSLA", use_container_width=True, on_click=select_stock_quick, args=("TSLA", "US"))
q_cols[3].button("🇲🇾 1155.KL", use_container_width=True, on_click=select_stock_quick, args=("1155.KL", "MY"))
q_cols[4].button("🇲🇾 0166.KL", use_container_width=True, on_click=select_stock_quick, args=("0166.KL", "MY"))
q_cols[5].button("🇲🇾 5347.KL", use_container_width=True, on_click=select_stock_quick, args=("5347.KL", "MY"))

st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

market_labels = {
    "MY": T["market_my"],
    "US": T["market_us"],
    "CUSTOM": T["market_custom"]
}

def on_market_radio_change():
    chosen_market = st.session_state["radio_market_key"]
    st.session_state["active_market"] = chosen_market
    if chosen_market == "MY" and not st.session_state["active_ticker"].endswith(".KL"):
        st.session_state["active_ticker"] = "1155.KL"
        st.session_state["my_dropdown_widget"] = my_opts[0]
    elif chosen_market == "US" and st.session_state["active_ticker"].endswith(".KL"):
        st.session_state["active_ticker"] = "NVDA"
        st.session_state["us_dropdown_widget"] = us_opts[0]

st.radio(
    "市场类别：",
    options=["US", "MY", "CUSTOM"],
    format_func=lambda k: market_labels[k],
    horizontal=True,
    label_visibility="collapsed",
    key="radio_market_key",
    on_change=on_market_radio_change
)

current_market = st.session_state.get("active_market", "US")

if current_market == "MY":
    def on_my_dropdown_change():
        chosen_str = st.session_state["my_dropdown_widget"]
        st.session_state["active_ticker"] = chosen_str.split(" | ")[0].strip()

    my_keys = [t for t, _ in MY_STOCKS]
    default_my_idx = my_keys.index(st.session_state["active_ticker"]) if st.session_state["active_ticker"] in my_keys else 0
    if "my_dropdown_widget" not in st.session_state or not any(st.session_state["my_dropdown_widget"].startswith(t) for t in my_keys):
        st.session_state["my_dropdown_widget"] = my_opts[default_my_idx]

    sel_my = st.selectbox(T["choose_stock"], options=my_opts, key="my_dropdown_widget", on_change=on_my_dropdown_change)
    st.session_state["active_ticker"] = sel_my.split(" | ")[0].strip()

elif current_market == "US":
    def on_us_dropdown_change():
        chosen_str = st.session_state["us_dropdown_widget"]
        st.session_state["active_ticker"] = chosen_str.split(" | ")[0].strip()

    us_keys = [t for t, _ in US_STOCKS]
    default_us_idx = us_keys.index(st.session_state["active_ticker"]) if st.session_state["active_ticker"] in us_keys else 0
    if "us_dropdown_widget" not in st.session_state or not any(st.session_state["us_dropdown_widget"].startswith(t) for t in us_keys):
        st.session_state["us_dropdown_widget"] = us_opts[default_us_idx]

    sel_us = st.selectbox(T["choose_stock"], options=us_opts, key="us_dropdown_widget", on_change=on_us_dropdown_change)
    st.session_state["active_ticker"] = sel_us.split(" | ")[0].strip()

else:
    def on_custom_submit():
        val = st.session_state["custom_input_field"].strip().upper()
        if val:
            st.session_state["active_ticker"] = val

    custom_code_col, custom_btn_col = st.columns([4.2, 1.2])
    with custom_code_col:
        st.text_input(
            T["custom_label"],
            value=st.session_state["active_ticker"],
            placeholder=T["custom_placeholder"],
            help=T["custom_help"],
            key="custom_input_field",
            on_change=on_custom_submit
        )
    with custom_btn_col:
        st.write("")
        st.write("")
        if st.button(T["btn_analyze"] + " 🔎", use_container_width=True):
            on_custom_submit()
            st.rerun()

current_ticker = st.session_state["active_ticker"]
is_my = current_ticker.endswith(".KL")

# ==============================================================================
# 6. 核心参数调节 (Glassmorphic Drawer)
# ==============================================================================
with st.expander(f"{T['param_header']}", expanded=False):
    param_col1, param_col2 = st.columns(2)
    with param_col1:
        custom_terminal_g = st.slider(T["param_terminal_g"], 1.0, 3.5, 2.5, 0.1, help=T["param_terminal_g_help"]) / 100.0
    with param_col2:
        custom_erp = st.slider(T["param_erp"], 4.0, 7.0, 5.5, 0.1, help=T["param_erp_help"]) / 100.0

# ==============================================================================
# 7. 后台金融量化引擎
# ==============================================================================
def safe_extract_item(df, item_name, default=0.0):
    if df is None or df.empty: return default
    try:
        for idx in df.index:
            if str(idx).strip().lower() == str(item_name).strip().lower():
                row = df.loc[idx]
                val = row.iloc[0] if hasattr(row, 'iloc') and len(row) > 0 else (list(row)[0] if hasattr(row, '__iter__') and len(row) > 0 else row)
                if pd.notna(val): return float(val)
    except Exception: pass
    return default

def fetch_risk_free_rate(is_my):
    if is_my: return 0.0385, "BNM MGS 10Y (~3.85%)"
    try:
        tnx = yf.Ticker("^TNX").history(period="5d")
        if not tnx.empty and 'Close' in tnx:
            rf = float(tnx['Close'].dropna().iloc[-1]) / 100.0
            return rf, f"US Treasury 10Y ({rf*100:.2f}%)"
    except Exception: pass
    return 0.042, "US Treasury 10Y (4.20%)"

def run_dynamic_beta_regression(ticker, is_my):
    benchmark_symbol = "EWM" if is_my else "SPY"
    try:
        df = yf.download([ticker, benchmark_symbol], period="3y", interval="1wk", auto_adjust=True, progress=False)
        if df.empty: return 1.0, None, 0.0
        df_close = df['Close'] if 'Close' in df else df
        if isinstance(df_close.columns, pd.MultiIndex): df_close.columns = df_close.columns.get_level_values(0)
        df_close.columns = [str(c).strip().upper() for c in df_close.columns]
        if ticker.upper() not in df_close.columns or benchmark_symbol.upper() not in df_close.columns: return 1.0, None, 0.0
        
        returns = df_close[[ticker.upper(), benchmark_symbol.upper()]].pct_change().dropna()
        if len(returns) < 20: return 1.0, None, 0.0
        y, x = returns.iloc[:, 0].values * 100.0, returns.iloc[:, 1].values * 100.0
        beta, alpha = np.polyfit(x, y, 1)
        r2 = float(np.corrcoef(x, y)[0, 1] ** 2)

        fig, ax = plt.subplots(figsize=(5.5, 3.8), dpi=120)
        fig.patch.set_facecolor('#131b2e'); ax.set_facecolor('#131b2e')
        ax.scatter(x, y, alpha=0.6, color="#38bdf8", edgecolors="none", s=28)
        x_line = np.linspace(x.min(), x.max(), 100)
        ax.plot(x_line, beta * x_line + alpha, color="#38bdf8", linewidth=2.2, label=f"Beta = {beta:.2f}")
        ax.tick_params(colors='#94a3b8', labelsize=8)
        for spine in ax.spines.values(): spine.set_color('#334155')
        ax.set_title(f"Beta Regression (Beta = {beta:.2f} | R² = {r2:.2f})", fontsize=10.5, fontweight="bold", color="#ffffff")
        ax.grid(True, linestyle=":", alpha=0.25, color="#64748b")
        plt.tight_layout()
        return float(min(max(beta, 0.40), 2.20)), fig, r2
    except Exception: return 1.0, None, 0.0

if current_ticker:
    with st.spinner("Calculating intrinsic valuation..."):
        try:
            stock = yf.Ticker(current_ticker)
            info = stock.info or {}
            company_name = info.get('longName') or info.get('shortName') or current_ticker
            sector = info.get('sector', 'Unknown')
            industry = info.get('industry', 'Unknown')
            currency = info.get('currency', 'MYR' if is_my else 'USD')

            price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose') or 0.0
            shares = info.get('sharesOutstanding', 1) or 1

            rf, _ = fetch_risk_free_rate(is_my)
            beta, beta_fig, _ = run_dynamic_beta_regression(current_ticker, is_my)
            ke = rf + (beta * custom_erp)

            bs, fin, cfs = stock.balance_sheet, stock.financials, stock.cashflow
            total_debt = safe_extract_item(bs, 'Total Debt', float(info.get('totalDebt', 0.0) or 0.0))
            cash = safe_extract_item(bs, 'Cash And Cash Equivalents', float(info.get('totalCash', 0.0) or 0.0))
            interest_exp = abs(safe_extract_item(fin, 'Interest Expense', 0.0))
            tax, pretax = safe_extract_item(fin, 'Tax Provision', 0.0), safe_extract_item(fin, 'Pretax Income', 0.0)
            tax_rate = min(max(tax / pretax, 0.10), 0.35) if (pretax > 0 and tax > 0) else (0.24 if is_my else 0.21)

            kd = (interest_exp / total_debt) if total_debt > 0 else 0.0
            market_cap = price * shares
            total_capital = market_cap + total_debt
            wacc = (market_cap / total_capital * ke) + (total_debt / total_capital * kd * (1.0 - tax_rate)) if total_capital > 0 else ke
            wacc = max(wacc, custom_terminal_g + 0.02)

            # DCF
            fcf = float(info.get('freeCashflow', 0.0) or 0.0)
            if fcf <= 0.0: fcf = safe_extract_item(cfs, 'Free Cash Flow', 0.0)
            growth_dcf = 0.08 if not is_my else 0.05
            
            pv_stage1 = sum([ (fcf * ((1.0 + growth_dcf) ** yr)) / ((1.0 + wacc) ** yr) for yr in range(1, 6) ])
            fcf_yr5 = fcf * ((1.0 + growth_dcf) ** 5)
            pv_tv = ((fcf_yr5 * (1.0 + custom_terminal_g)) / (wacc - custom_terminal_g)) / ((1.0 + wacc) ** 5)
            val_dcf = (pv_stage1 + pv_tv - total_debt + cash) / shares if shares > 0 else None

            # DDM
            dps = float(info.get('dividendRate') or info.get('trailingAnnualDividendRate') or 0.0)
            val_ddm = (dps * (1.0 + custom_terminal_g)) / (ke - custom_terminal_g) if (dps > 0 and ke > custom_terminal_g) else None

            # P/E
            eps = float(info.get('trailingEps') or info.get('forwardEps') or 0.0)
            if eps <= 0.0 and safe_extract_item(fin, 'Net Income', 0.0) > 0:
                eps = safe_extract_item(fin, 'Net Income', 0.0) / shares
            bench_pe = 22.0 if sector in ['Technology', 'Communication Services'] else (11.5 if sector == 'Financial Services' else 16.0)
            val_pe = eps * bench_pe if eps > 0 else None

            if sector in ['Financial Services', 'Utilities', 'Real Estate'] and val_ddm:
                primary_val, primary_model_name = val_ddm, T["model_ddm_name"]
            elif val_dcf:
                primary_val, primary_model_name = val_dcf, T["model_dcf_name"]
            elif val_pe:
                primary_val, primary_model_name = val_pe, T["model_pe_name"]
            else:
                primary_val, primary_model_name = None, "N/A"

            # 身份卡片容器
            with st.container(border=True):
                st.markdown(
                    f"""
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
                        <div>
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <span style="font-size: 22px; font-weight: 800; color: #ffffff;">{company_name}</span>
                                <span style="font-family: 'JetBrains Mono', monospace; background: #0284c7; color: #ffffff; font-size: 12px; font-weight: 700; padding: 2px 8px; border-radius: 6px;">{current_ticker}</span>
                            </div>
                            <div style="color: #94a3b8; font-size: 13px; margin-top: 6px;">
                                板块：<span style="color: #cbd5e1;">{sector}</span> • <span style="color: #cbd5e1;">{industry}</span> | 货币：<span style="color: #38bdf8; font-weight: 600;">{currency}</span>
                            </div>
                        </div>
                        <div style="text-align: right;">
                            <div style="color: #94a3b8; font-size: 12px; text-transform: uppercase;">{T['curr_price']}</div>
                            <div style="font-family: 'JetBrains Mono', monospace; font-size: 28px; font-weight: 800; color: #ffffff;">{currency} {price:.2f}</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            # 综合诊断卡片
            if primary_val and primary_val > 0 and price > 0:
                diff_pct = (primary_val - price) / price * 100.0
                is_undervalued = primary_val > price
                verdict_text = T['verdict_under'] if is_undervalued else T['verdict_over']
                diff_label = f"{T['upside_prefix']} +{diff_pct:.1f}%" if is_undervalued else f"{T['downside_prefix']} {abs(diff_pct):.1f}%"
                card_border = "#22c55e" if is_undervalued else "#f43f5e"
            else:
                verdict_text, diff_label, card_border = T['no_data'], "暂无足够数据", "#334155"

            with st.container(border=True):
                st.markdown(
                    f"""
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px;">
                        <div>
                            <div style="color: #94a3b8; font-size: 13px; font-weight: 600; text-transform: uppercase;">{T['verdict_title']}</div>
                            <div style="font-size: 26px; font-weight: 800; color: #ffffff; margin: 4px 0 6px 0;">{verdict_text}</div>
                            <div style="display: inline-flex; background: rgba(56, 189, 248, 0.15); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 20px; padding: 4px 12px; font-size: 13.5px; font-weight: 700; color: #38bdf8;">
                                {diff_label}
                            </div>
                        </div>
                        <div style="background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 12px; padding: 14px 22px; text-align: right;">
                            <div style="color: #94a3b8; font-size: 12px;">{T['fair_price_rec']}</div>
                            <div style="font-family: 'JetBrains Mono', monospace; font-size: 28px; font-weight: 800; color: #38bdf8; margin: 2px 0;">
                                {currency} {primary_val:.2f} if primary_val else 'N/A'
                            </div>
                            <div style="color: #cbd5e1; font-size: 11.5px;">基准模型：{primary_model_name}</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            # 三大模型矩阵便当盒
            m1, m2, m3 = st.columns(3)
            with m1:
                with st.container(border=True):
                    st.markdown(f"**{T['model_dcf_name']}**")
                    st.markdown(f"<div style='font-family: JetBrains Mono; font-size: 24px; font-weight: 800; color: #ffffff; margin: 10px 0;'>{currency} {val_dcf:.2f}</div>" if val_dcf else "<div style='color:#94a3b8;'>N/A</div>", unsafe_allow_html=True)
                    st.caption("基于 5 年自由现金流与 WACC 贴现")
            with m2:
                with st.container(border=True):
                    st.markdown(f"**{T['model_ddm_name']}**")
                    st.markdown(f"<div style='font-family: JetBrains Mono; font-size: 24px; font-weight: 800; color: #ffffff; margin: 10px 0;'>{currency} {val_ddm:.2f}</div>" if val_ddm else "<div style='color:#94a3b8;'>N/A (无稳定分红)</div>", unsafe_allow_html=True)
                    st.caption("基于长期股息分红增长贴现")
            with m3:
                with st.container(border=True):
                    st.markdown(f"**{T['model_pe_name']}**")
                    st.markdown(f"<div style='font-family: JetBrains Mono; font-size: 24px; font-weight: 800; color: #ffffff; margin: 10px 0;'>{currency} {val_pe:.2f}</div>" if val_pe else "<div style='color:#94a3b8;'>N/A</div>", unsafe_allow_html=True)
                    st.caption("基于每股收益 EPS 乘以行业市盈率")

            # 词典卡片
            st.markdown(f"#### {T['glossary_header']}")
            g1, g2, g3, g4 = st.columns(4)
            with g1:
                with st.container(border=True):
                    st.markdown(f"**{T['card_beta_title']}**")
                    st.markdown(f"<div style='font-family: JetBrains Mono; font-size: 22px; font-weight: 800; color: #38bdf8;'>{beta:.2f}</div>", unsafe_allow_html=True)
                    st.caption(T['card_beta_desc'], unsafe_allow_html=True)
            with g2:
                with st.container(border=True):
                    st.markdown(f"**{T['card_growth_title']}**")
                    st.markdown(f"<div style='font-family: JetBrains Mono; font-size: 22px; font-weight: 800; color: #38bdf8;'>{growth_dcf*100:.1f}%</div>", unsafe_allow_html=True)
                    st.caption(T['card_growth_desc'])
            with g3:
                with st.container(border=True):
                    st.markdown(f"**{T['card_wacc_title']}**")
                    st.markdown(f"<div style='font-family: JetBrains Mono; font-size: 22px; font-weight: 800; color: #38bdf8;'>{wacc*100:.1f}%</div>", unsafe_allow_html=True)
                    st.caption(T['card_wacc_desc'])
            with g4:
                with st.container(border=True):
                    st.markdown(f"**{T['card_fair_title']}**")
                    st.markdown(f"<div style='font-family: JetBrains Mono; font-size: 22px; font-weight: 800; color: #38bdf8;'>{currency} {primary_val:.2f}</div>" if primary_val else "N/A", unsafe_allow_html=True)
                    st.caption(T['card_fair_desc'])

            # 图表区
            st.markdown(f"#### {T['chart_header']}")
            ch1, ch2 = st.columns([1.35, 1])
            with ch1:
                with st.container(border=True):
                    st.markdown(f"##### 📈 {T['chart_history_title']}")
                    timeframe = st.radio(T["timeframe_label"], ["1D", "1M", "1Y", "5Y", "MAX"], index=2, horizontal=True)
                    tf_map = {"1D": ("1d", "5m"), "1M": ("1mo", "1d"), "1Y": ("1y", "1wk"), "5Y": ("5y", "1mo"), "MAX": ("max", "3mo")}
                    p_val, i_val = tf_map[timeframe]
                    hist_data = yf.download(current_ticker, period=p_val, interval=i_val, progress=False)
                    if isinstance(hist_data.columns, pd.MultiIndex): hist_data.columns = hist_data.columns.get_level_values(0)
                    if not hist_data.empty and HAS_PLOTLY:
                        fig_k = go.Figure(data=[go.Candlestick(
                            x=hist_data.index, open=hist_data['Open'], high=hist_data['High'], low=hist_data['Low'], close=hist_data['Close'],
                            increasing_line_color='#22c55e', decreasing_line_color='#ef4444'
                        )])
                        fig_k.update_layout(xaxis_rangeslider_visible=False, height=350, margin=dict(l=10, r=10, t=10, b=10), template="plotly_dark", paper_bgcolor="#0b0f19", plot_bgcolor="#0b0f19")
                        st.plotly_chart(fig_k, use_container_width=True)
            with ch2:
                with st.container(border=True):
                    st.markdown(f"##### 🎯 {T['chart_beta_title']}")
                    if beta_fig: st.pyplot(beta_fig)

            # 免责声明
            with st.container(border=True):
                st.markdown(f"**{T['disclaimer_title']}**")
                st.markdown(f"<div style='color: #cbd5e1; font-size: 12px; line-height: 1.5;'>{T['disclaimer_content']}</div>", unsafe_allow_html=True)

        except Exception as e:
            st.error(f"测算遇到异常: {e}")
