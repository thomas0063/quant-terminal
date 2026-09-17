import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime

try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

# ==============================================================================
# 1. 页面基本配置 (UI-UX-Pro-Max)
# ==============================================================================
st.set_page_config(
    page_title="StockVal Pro - 智能股票公道价估值器",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==============================================================================
# 2. UI-UX-Pro-Max 设计系统：全局 CSS 深度定制注入
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

/* 隐藏 Streamlit 默认顶部白边与装饰线 */
header[data-testid="stHeader"] { background: transparent !important; }
.block-container { padding-top: 1.8rem !important; padding-bottom: 3.5rem !important; max-width: 1280px !important; }

/* 现代按钮体系 */
.stButton > button {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%) !important;
    color: #f1f5f9 !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1) !important;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.25) !important;
}
.stButton > button:hover {
    border-color: #38bdf8 !important;
    color: #ffffff !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 18px -2px rgba(56, 189, 248, 0.3) !important;
}

/* 搜索与输入框 */
div[data-baseweb="input"] > div, div[data-baseweb="select"] > div {
    background-color: #131b2e !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    border-radius: 8px !important;
    color: #ffffff !important;
}
div[data-baseweb="input"] input {
    color: #ffffff !important;
    font-family: 'JetBrains Mono', monospace !important;
}

/* 单选框 (Segmented Controls) */
div[role="radiogroup"] {
    background: #0f172a !important;
    padding: 6px 12px !important;
    border-radius: 10px !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    gap: 16px !important;
}
div[role="radiogroup"] label { color: #cbd5e1 !important; font-size: 13.5px !important; font-weight: 500 !important; }

/* 参数折叠抽屉 */
.streamlit-expanderHeader {
    background-color: #131b2e !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 10px !important;
    color: #f8fafc !important;
    font-weight: 600 !important;
}
.streamlit-expanderContent {
    background-color: rgba(19, 27, 46, 0.6) !important;
    border: 1px solid rgba(255, 255, 255, 0.06) !important;
    border-top: none !important;
    border-bottom-left-radius: 10px !important;
    border-bottom-right-radius: 10px !important;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ==============================================================================
# 3. 国际化多语言字典
# ==============================================================================
TEXTS = {
    "zh": {
        "title": "StockVal Pro",
        "badge_engine": "AI 内在价值测算引擎 v2.5",
        "subtitle": "小白也能看懂的多维度股票公允价值测算平台 | 深度支持马来西亚股市 (Bursa) 与美股 (US Equities)",
        "market_label": "📌 步骤 1：挑选热门股票或自选代码",
        "market_my": "🇲🇾 马来西亚股市 (Bursa)",
        "market_us": "🇺🇸 美国股市 (US Equities)",
        "market_custom": "🔍 手动输入代码",
        "choose_stock": "从热门股票池中快速挑选：",
        "custom_label": "输入股票代码：",
        "custom_help": "马股请加 .KL (如: 1155.KL)；美股直接输入代码 (如: AAPL, NVDA)",
        "custom_placeholder": "例如: 1155.KL 或 AAPL",
        "quick_tag": "🔥 热门标的秒选：",
        "btn_analyze": "开始测算",
        "param_header": "⚙️ 步骤 2：估值核心参数设定 (小白建议保持默认)",
        "param_terminal_g": "长期永续增长率 (Terminal Growth)",
        "param_terminal_g_help": "指公司成熟稳定后的永久增长率，建议保持 2.5%。",
        "param_erp": "股市风险溢价要求 (ERP)",
        "param_erp_help": "投资股票相比于国债所期望的额外回报补偿。通常为 5.5%。",
        "result_header": "📊 步骤 3：三大估值模型横向对比与综合结论",
        "curr_price": "当前市场价格",
        "fair_price_rec": "系统最推荐公道价",
        "verdict_title": "综合投资诊断",
        "verdict_under": "🟢 明显低估 (划算 / 打折中)",
        "verdict_over": "🔴 明显高估 (偏贵 / 溢价中)",
        "verdict_fair": "⚖️ 估值合理 (价格适中)",
        "upside_prefix": "较当前市价有",
        "downside_prefix": "较公道价溢价",
        "model_dcf_name": "两阶段现金流贴现 (DCF)",
        "model_ddm_name": "股息分红贴现 (DDM)",
        "model_pe_name": "市盈率倍数估值 (P/E)",
        "badge_recommended": "⭐ 主要推荐",
        "badge_reference": "📌 参考指标",
        "no_data": "暂无数据",
        "no_data_dcf": "现金流为负或数据不足",
        "no_data_ddm": "该公司不派发股息",
        "no_data_pe": "公司目前处于净亏损",
        "glossary_header": "📖 小白通俗金融词典",
        "card_beta_title": "波动敏感度 (Beta)",
        "card_beta_desc": "衡量相对于大盘是活泼还是稳健。>1 高弹性，<1 抗跌。",
        "card_growth_title": "预期增长率 (Growth)",
        "card_growth_desc": "未来现金流预计每年递增比例。增长越快，当前身价越高。",
        "card_wacc_title": "及格线回报率 (WACC)",
        "card_wacc_desc": "买入该公司的最低年化回报门槛。风险越高，要求越高。",
        "card_fair_title": "内在公允价值 (Fair Value)",
        "card_fair_desc": "剥离市场短期情绪，根据真实资产造血能力算出的出厂价。",
        "chart_header": "📈 步骤 4：多周期走势图与量化特征图",
        "timeframe_label": "切换 K 线周期：",
        "chart_history_title": "交互式 K 线走势图",
        "chart_legend": "🟢 绿色上涨 (阳线) | 🔴 红色下跌 (阴线)",
        "chart_beta_title": "Beta 特征线散点分布图",
        "chart_beta_exp": "每个点代表一周收益。红线斜率即真实 Beta。",
        "ws_header": "🏛️ 华尔街专业投行分析师共识 (Wall Street Consensus)",
        "ws_mean": "投行平均目标价",
        "ws_range": "目标价预测区间",
        "ws_rating": "投行综合评级",
        "ws_match": "✅ 你的模型计算与华尔街机构分析师共识高度吻合！",
        "disclaimer_title": "⚠️ 重要法律与风险免责声明",
        "disclaimer_content": "本平台结果仅供学术研究，不构成财务建议。股市有风险，投资需谨慎。"
    },
    "en": {
        "title": "StockVal Pro",
        "badge_engine": "AI Intrinsic Engine v2.5",
        "subtitle": "Beginner-Friendly Multi-Model Valuation Platform | Bursa & US Equities",
        "market_label": "📌 Step 1: Select Stock",
        "market_my": "🇲🇾 Bursa Malaysia",
        "market_us": "🇺🇸 US Equities",
        "market_custom": "🔍 Custom Ticker",
        "choose_stock": "Quick pick:",
        "custom_label": "Enter Stock Ticker:",
        "custom_help": "Malaysia: add .KL (e.g. 1155.KL). US: just ticker (e.g. AAPL)",
        "custom_placeholder": "e.g., 1155.KL or AAPL",
        "quick_tag": "🔥 Quick Suggestions:",
        "btn_analyze": "Analyze",
        "param_header": "⚙️ Step 2: Core Valuation Assumptions",
        "param_terminal_g": "Terminal Growth (g)",
        "param_terminal_g_help": "Long-term growth rate, standard is 2.5%.",
        "param_erp": "Equity Risk Premium (ERP)",
        "param_erp_help": "Extra return expected for stock risk. Typically 5.5%.",
        "result_header": "📊 Step 3: Valuation Matrix & Verdict",
        "curr_price": "Current Price",
        "fair_price_rec": "System Recommended Fair Value",
        "verdict_title": "Diagnostic Summary",
        "verdict_under": "🟢 UNDERVALUED",
        "verdict_over": "🔴 OVERVALUED",
        "verdict_fair": "⚖️ FAIRLY VALUED",
        "upside_prefix": "Potential upside: ",
        "downside_prefix": "Premium of: ",
        "model_dcf_name": "Two-Stage DCF",
        "model_ddm_name": "Dividend Discount (DDM)",
        "model_pe_name": "P/E Multiples",
        "badge_recommended": "⭐ Recommended",
        "badge_reference": "📌 Reference",
        "no_data": "N/A",
        "no_data_dcf": "Negative/Missing Cash Flows",
        "no_data_ddm": "No dividend",
        "no_data_pe": "Company in net loss",
        "glossary_header": "📖 Beginner's Glossary",
        "card_beta_title": "Beta",
        "card_beta_desc": "Volatility vs market. >1 high elasticity, <1 defensive.",
        "card_growth_title": "Growth",
        "card_growth_desc": "Forecasted cash flow growth. Higher growth = higher value.",
        "card_wacc_title": "WACC",
        "card_wacc_desc": "Minimum hurdle return required by investors.",
        "card_fair_title": "Fair Value",
        "card_fair_desc": "Authentic price based on business assets, stripping hype.",
        "chart_header": "📈 Step 4: Candlestick & Regression",
        "timeframe_label": "Timeframe:",
        "chart_history_title": "Interactive Chart",
        "chart_legend": "🟢 Bullish | 🔴 Bearish",
        "chart_beta_title": "Beta Scatter Plot",
        "chart_beta_exp": "Slope of red line is Beta.",
        "ws_header": "🏛️ Wall Street Consensus (US)",
        "ws_mean": "Avg Target Price",
        "ws_range": "Target Range",
        "ws_rating": "Consensus Rating",
        "ws_match": "✅ Your DCF aligns closely with Wall Street targets!",
        "disclaimer_title": "⚠️ Disclaimer",
        "disclaimer_content": "For educational purposes only. Not financial advice."
    }
}

# ==============================================================================
# 4. 后台金融量化引擎与辅助函数
# ==============================================================================
def safe_extract_item(df, item_name, default=0.0):
    if df is None or df.empty: return default
    try:
        for idx in df.index:
            if str(idx).strip().lower() == str(item_name).strip().lower():
                row = df.loc[idx]
                val = row.iloc[0] if hasattr(row, 'iloc') else list(row)[0] if hasattr(row, '__iter__') else row
                if pd.notna(val): return float(val)
    except: pass
    return default

@st.cache_data(ttl=3600)
def fetch_risk_free_rate(is_my):
    if is_my: return 0.0385, "BNM Benchmark (MGS 10Y: ~3.85%)"
    try:
        tnx = yf.Ticker("^TNX").history(period="5d")
        if not tnx.empty and 'Close' in tnx: return float(tnx['Close'].dropna().iloc[-1]) / 100.0, "US Treasury 10Y"
    except: pass
    return 0.042, "US Treasury 10Y Benchmark (4.20%)"

@st.cache_data(ttl=86400)
def run_dynamic_beta_regression(ticker, is_my):
    b_sym, b_label = ("EWM", "MSCI Malaysia") if is_my else ("SPY", "S&P 500")
    try:
        df = yf.download([ticker, b_sym], period="3y", interval="1wk", auto_adjust=True, progress=False)['Close']
        df.columns = [str(c).strip().upper() for c in df.columns]
        if ticker.upper() not in df.columns or b_sym not in df.columns: raise ValueError()
        
        returns = df[[ticker.upper(), b_sym]].pct_change().dropna() * 100
        y, x = returns[ticker.upper()].values, returns[b_sym].values
        beta, alpha = np.polyfit(x, y, 1)
        r2 = float(np.corrcoef(x, y)[0, 1] ** 2)

        fig, ax = plt.subplots(figsize=(5.5, 3.8), dpi=120)
        fig.patch.set_facecolor('#131b2e')
        ax.set_facecolor('#131b2e')
        ax.scatter(x, y, alpha=0.6, color="#38bdf8", edgecolors="none", s=28)
        x_line = np.linspace(x.min(), x.max(), 100)
        ax.plot(x_line, beta * x_line + alpha, color="#f43f5e", linewidth=2.2)
        ax.axhline(0, color="#475569", linestyle="--", linewidth=0.8, alpha=0.6)
        ax.axvline(0, color="#475569", linestyle="--", linewidth=0.8, alpha=0.6)
        ax.tick_params(colors='#94a3b8', labelsize=8)
        for spine in ax.spines.values(): spine.set_color('#334155')
        ax.set_xlabel(f"Benchmark: {b_label} (%)", fontsize=9, color="#94a3b8")
        ax.set_ylabel(f"Stock: {ticker} (%)", fontsize=9, color="#94a3b8")
        ax.set_title(f"Beta Regression (Beta = {beta:.2f} | R² = {r2:.2f})", fontsize=10.5, fontweight="bold", color="#ffffff")
        ax.grid(True, linestyle=":", alpha=0.25, color="#64748b")
        plt.tight_layout()
        return min(max(beta, 0.40), 2.20), fig, r2
    except:
        return 1.0, None, 0.0

# ==============================================================================
# 5. 主程序与 UI 构建
# ==============================================================================
def main():
    col_logo, col_lang = st.columns([4.2, 1.2])
    with col_lang:
        lang_key = "zh" if st.selectbox("🌐", ["中文", "English"], index=0, label_visibility="collapsed") == "中文" else "en"
        T = TEXTS[lang_key]

    with col_logo:
        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 12px; margin-top: 4px;">
            <div style="background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%); width: 44px; height: 44px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 22px; box-shadow: 0 4px 12px rgba(2, 132, 199, 0.4);">💎</div>
            <div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 24px; font-weight: 800; color: #ffffff;">{T['title']}</span>
                    <span style="background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 20px;">{T['badge_engine']}</span>
                </div>
                <div style="color: #94a3b8; font-size: 13px; margin-top: 2px;">{T['subtitle']}</div>
            </div>
        </div><div style='height: 12px;'></div>
        """, unsafe_allow_html=True)

    MY_STOCKS = [("1155.KL", "Maybank"), ("1295.KL", "Public Bank"), ("5347.KL", "Tenaga Nasional"), ("0166.KL", "Inari"), ("5296.KL", "MR D.I.Y.")]
    US_STOCKS = [("AAPL", "Apple"), ("NVDA", "NVIDIA"), ("TSLA", "Tesla"), ("MSFT", "Microsoft"), ("META", "Meta")]

    if "active_ticker" not in st.session_state:
        st.session_state.update({"active_ticker": "1155.KL", "active_market": "MY", "radio_market_key": "MY"})

    def select_stock_quick(ticker, market):
        st.session_state.update({"active_ticker": ticker, "active_market": market, "radio_market_key": market})
        key = "us_dropdown_widget" if market == "US" else "my_dropdown_widget"
        opts = [f"{t} | {n}" for t, n in (US_STOCKS if market == "US" else MY_STOCKS)]
        st.session_state[key] = next((o for o in opts if o.startswith(ticker)), opts[0])

    st.write(T["quick_tag"])
    q_cols = st.columns(6)
    q_cols[0].button("🇲🇾 1155.KL", on_click=select_stock_quick, args=("1155.KL", "MY"), use_container_width=True)
    q_cols[1].button("🇲🇾 0166.KL", on_click=select_stock_quick, args=("0166.KL", "MY"), use_container_width=True)
    q_cols[2].button("🇲🇾 5347.KL", on_click=select_stock_quick, args=("5347.KL", "MY"), use_container_width=True)
    q_cols[3].button("🇺🇸 AAPL", on_click=select_stock_quick, args=("AAPL", "US"), use_container_width=True)
    q_cols[4].button("🇺🇸 NVDA", on_click=select_stock_quick, args=("NVDA", "US"), use_container_width=True)
    q_cols[5].button("🇺🇸 TSLA", on_click=select_stock_quick, args=("TSLA", "US"), use_container_width=True)

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    def on_market_change():
        mkt = st.session_state["radio_market_key"]
        st.session_state["active_market"] = mkt
        if mkt == "MY" and not st.session_state["active_ticker"].endswith(".KL"):
            st.session_state["active_ticker"] = "1155.KL"
        elif mkt == "US" and st.session_state["active_ticker"].endswith(".KL"):
            st.session_state["active_ticker"] = "AAPL"

    st.radio("Market:", ["MY", "US", "CUSTOM"], format_func=lambda k: {"MY": T["market_my"], "US": T["market_us"], "CUSTOM": T["market_custom"]}[k], horizontal=True, label_visibility="collapsed", key="radio_market_key", on_change=on_market_change)

    current_market = st.session_state["active_market"]
    if current_market in ["MY", "US"]:
        opts = [f"{t} | {n}" for t, n in (MY_STOCKS if current_market == "MY" else US_STOCKS)]
        dd_key = f"{current_market.lower()}_dropdown_widget"
        if dd_key not in st.session_state: st.session_state[dd_key] = opts[0]
        sel = st.selectbox(T["choose_stock"], opts, key=dd_key, on_change=lambda: st.session_state.update({"active_ticker": st.session_state[dd_key].split(" | ")[0]}))
        st.session_state["active_ticker"] = sel.split(" | ")[0]
    else:
        c1, c2 = st.columns([4.2, 1.2])
        st.session_state["active_ticker"] = c1.text_input(T["custom_label"], value=st.session_state["active_ticker"], placeholder=T["custom_placeholder"]).upper()
        c2.write(""); c2.write(""); c2.button(T["btn_analyze"] + " 🔎", use_container_width=True)

    current_ticker = st.session_state["active_ticker"]
    is_my = current_ticker.endswith(".KL")

    with st.expander(T['param_header'], expanded=False):
        p1, p2 = st.columns(2)
        custom_g2 = p1.slider(T["param_terminal_g"], 1.0, 3.5, 2.5, 0.1, help=T["param_terminal_g_help"]) / 100.0
        custom_erp = p2.slider(T["param_erp"], 4.0, 7.0, 5.5, 0.1, help=T["param_erp_help"]) / 100.0

    if current_ticker:
        with st.spinner("Calculating intrinsic valuation..."):
            try:
                stock = yf.Ticker(current_ticker)
                info = stock.info or {}
                price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose') or 0.0
                shares = info.get('sharesOutstanding', 1) or 1
                
                rf, _ = fetch_risk_free_rate(is_my)
                beta, beta_fig, _ = run_dynamic_beta_regression(current_ticker, is_my)
                wacc = max(rf + (beta * custom_erp), custom_g2 + 0.02)

                # ==================================================================
                # 模型估算 (DCF, DDM, P/E)
                # ==================================================================
                val_dcf = val_ddm = val_pe = None
                
                fcf = info.get('freeCashflow', 0.0)
                if fcf > 0:
                    growth_dcf = min(max(info.get('earningsGrowth', 0.08), 0.02), 0.15)
                    pv_stage1 = sum([(fcf * ((1 + growth_dcf) ** y)) / ((1 + wacc) ** y) for y in range(1, 6)])
                    pv_tv = ((fcf * ((1 + growth_dcf) ** 5) * (1 + custom_g2)) / (wacc - custom_g2)) / ((1 + wacc) ** 5)
                    val_dcf = (pv_stage1 + pv_tv + info.get('totalCash', 0) - info.get('totalDebt', 0)) / shares

                dps = info.get('dividendRate', 0.0)
                if dps > 0:
                    val_ddm = (dps * (1 + custom_g2)) / (wacc - custom_g2) if wacc > custom_g2 else 0.0

                eps = info.get('trailingEps', 0.0)
                if eps > 0:
                    val_pe = eps * 16.0 # Simplified Sector PE

                sector = info.get('sector', 'Unknown')
                if sector in ['Financial Services', 'Utilities'] and val_ddm:
                    primary_val, primary_name = val_ddm, T["model_ddm_name"]
                elif val_dcf:
                    primary_val, primary_name = val_dcf, T["model_dcf_name"]
                elif val_pe:
                    primary_val, primary_name = val_pe, T["model_pe_name"]
                else:
                    primary_val, primary_name = None, "N/A"

                # ==================================================================
                # 综合诊断 Hero 大卡片
                # ==================================================================
                st.markdown(f"#### {T['result_header']}")
                if primary_val and price > 0:
                    diff_pct = (primary_val - price) / price * 100.0
                    is_under = primary_val > price
                    diff_col, bg_glow, card_border, v_txt, diff_lbl = ("#22c55e", "rgba(6,78,59,0.35)", "#10b981", T['verdict_under'], f"{T['upside_prefix']} +{diff_pct:.1f}%") if is_under else ("#f43f5e", "rgba(127,29,29,0.35)", "#f43f5e", T['verdict_over'], f"{T['downside_prefix']} {abs(diff_pct):.1f}%")
                    fv_str = f"{info.get('currency', 'USD')} {primary_val:.2f}"
                else:
                    diff_col, bg_glow, card_border, v_txt, diff_lbl, fv_str = "#94a3b8", "rgba(30,41,59,0.35)", "#334155", T['no_data'], "暂无足够数据", "N/A"

                st.markdown(f"""
                <div style="background: linear-gradient(135deg, {bg_glow} 0%, rgba(15,23,42,0.95) 100%); border: 1.5px solid {card_border}; border-radius: 14px; padding: 22px 26px; margin-bottom: 22px; box-shadow: 0 12px 28px -5px rgba(0,0,0,0.45); display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="color: #94a3b8; font-size: 13px; font-weight: 600;">{T['verdict_title']}</div>
                        <div style="font-size: 26px; font-weight: 800; color: #ffffff; margin: 4px 0 6px 0;">{v_txt}</div>
                        <div style="background: rgba(0,0,0,0.3); border: 1px solid {card_border}; border-radius: 20px; padding: 4px 12px; font-size: 13.5px; font-weight: 700; color: {diff_col}; display: inline-block;">{diff_lbl}</div>
                    </div>
                    <div style="background: rgba(15,23,42,0.7); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 14px 20px; text-align: right;">
                        <div style="color: #94a3b8; font-size: 12px; font-weight: 500;">{T['fair_price_rec']} (市价: {price:.2f})</div>
                        <div style="font-family: 'JetBrains Mono', monospace; font-size: 28px; font-weight: 800; color: #ffffff; margin: 2px 0;">{fv_str}</div>
                        <div style="color: #38bdf8; font-size: 11.5px; font-weight: 600;">基准模型：{primary_name}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # ==================================================================
                # 便当盒矩阵 (Bento Matrix) 对齐渲染
                # ==================================================================
                def render_bento(title, val, is_rec, currency, note, empty_msg):
                    bg, border, shadow, b_txt, b_bg, b_col, b_border = ("linear-gradient(135deg, rgba(30,41,59,0.9), rgba(15,23,42,0.95))", "#10b981", "0 8px 24px -4px rgba(16,185,129,0.2)", T["badge_recommended"], "rgba(16,185,129,0.2)", "#34d399", "rgba(16,185,129,0.4)") if is_rec else ("linear-gradient(135deg, rgba(30,41,59,0.9), rgba(15,23,42,0.95))", "#334155", "0 4px 14px rgba(0,0,0,0.25)", T["badge_reference"], "rgba(148,163,184,0.15)", "#94a3b8", "rgba(148,163,184,0.25)")
                    val_html = f"<div style='font-family: JetBrains Mono; font-size: 26px; font-weight: 800; color: #fff; margin: 8px 0;'>{currency} {val:.2f}</div>" if val else f"<div style='background: rgba(239,68,68,0.12); border: 1px solid rgba(239,68,68,0.25); border-radius: 8px; padding: 4px 8px; font-size: 11.5px; color: #f87171; display: inline-block; margin: 8px 0;'>⚠️ {empty_msg}</div>"
                    return f"""<div style="background: {bg}; border: 1.5px solid {border}; border-radius: 12px; padding: 18px; min-height: 160px; height: 100%; box-shadow: {shadow}; display: flex; flex-direction: column; justify-content: space-between;">
                        <div>
                            <div style="display: flex; justify-content: space-between; align-items: center;"><span style="font-size: 14.5px; font-weight: 700; color: #f8fafc;">{title}</span><span style="background: {b_bg}; color: {b_col}; border: 1px solid {b_border}; font-size: 11px; padding: 2px 8px; border-radius: 12px;">{b_txt}</span></div>
                            {val_html}
                        </div>
                        <div style="color: #94a3b8; font-size: 12px; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 8px;">💡 {note}</div>
                    </div>"""

                c1, c2, c3 = st.columns(3)
                curr = info.get('currency', 'USD')
                with c1: st.markdown(render_bento(T["model_dcf_name"], val_dcf, primary_name==T["model_dcf_name"], curr, "自由现金流贴现", T["no_data_dcf"]), unsafe_allow_html=True)
                with c2: st.markdown(render_bento(T["model_ddm_name"], val_ddm, primary_name==T["model_ddm_name"], curr, "股息及永续增长折现", T["no_data_ddm"]), unsafe_allow_html=True)
                with c3: st.markdown(render_bento(T["model_pe_name"], val_pe, primary_name==T["model_pe_name"], curr, "行业倍数估值", T["no_data_pe"]), unsafe_allow_html=True)
                st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

                # ==================================================================
                # 美股专属：华尔街一致预期 (Wall Street Consensus Cards)
                # ==================================================================
                if not is_my:
                    target_mean = info.get('targetMeanPrice')
                    target_high = info.get('targetHighPrice')
                    target_low = info.get('targetLowPrice')
                    num_analysts = info.get('numberOfAnalystOpinions', 0)
                    rating = str(info.get('recommendationKey', 'N/A')).upper()

                    if target_mean and num_analysts > 0:
                        st.markdown(f"#### {T['ws_header']}")
                        ws1, ws2, ws3 = st.columns(3)

                        card_box_style = "background: #131b2e; border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 18px 16px; text-align: center; min-height: 125px; height: 100%; display: flex; flex-direction: column; justify-content: center; box-shadow: 0 6px 18px rgba(0,0,0,0.3);"
                        lbl_style = "color: #94a3b8; font-size: 13px; font-weight: 500; margin-bottom: 6px;"
                        val_style = "font-family: 'JetBrains Mono', monospace; color: #ffffff !important; font-size: 24px; font-weight: 800; margin: 4px 0; white-space: nowrap;"
                        sub_style = "color: #38bdf8; font-size: 12px; font-weight: 600;"

                        with ws1:
                            st.markdown(f"<div style='{card_box_style}'><div style='{lbl_style}'>{T['ws_mean']}</div><div style='{val_style}'>${target_mean:.2f}</div><div style='{sub_style}'>👥 {num_analysts} Analysts</div></div>", unsafe_allow_html=True)
                        with ws2:
                            st.markdown(f"<div style='{card_box_style}'><div style='{lbl_style}'>{T['ws_range']}</div><div style='{val_style}'>${target_low:.2f} - ${target_high:.2f}</div><div style='color:#cbd5e1; font-size:12px;'>Min / Max Target</div></div>", unsafe_allow_html=True)
                        with ws3:
                            st.markdown(f"<div style='{card_box_style}'><div style='{lbl_style}'>{T['ws_rating']}</div><div style='{val_style}'>{rating}</div><div style='color:#4ade80; font-size:12px;'>🏛️ Consensus View</div></div>", unsafe_allow_html=True)

                        if primary_val and abs((primary_val - target_mean) / target_mean) <= 0.15:
                            st.markdown(f"<div style='background: rgba(16,185,129,0.12); border: 1px solid rgba(16,185,129,0.3); border-radius: 10px; padding: 12px 18px; color: #4ade80; font-size: 13.5px; font-weight: 600; margin-top: 14px;'>{T['ws_match']}</div>", unsafe_allow_html=True)
                        st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

                # ==================================================================
                # 小白词典 (等高 Bento Tiles)
                # ==================================================================
                st.markdown(f"#### {T['glossary_header']}")
                g1, g2, g3, g4 = st.columns(4)
                def render_glossary(icon, title, val_str, desc):
                    return f"<div style='background: #131b2e; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 16px 14px; min-height: 165px; height: 100%; box-shadow: 0 4px 12px rgba(0,0,0,0.25); display: flex; flex-direction: column; justify-content: space-between;'><div><div style='display:flex; align-items:center; gap:6px;'><span style='font-size:16px;'>{icon}</span><span style='color:#94a3b8; font-size:12.5px; font-weight:600;'>{title}</span></div><div style='font-family: JetBrains Mono; font-size: 22px; font-weight: 800; color: #fff; margin: 4px 0;'>{val_str}</div></div><div style='color: #cbd5e1; font-size: 11px; background: rgba(15,23,42,0.6); padding: 8px; border-radius: 6px;'>{desc}</div></div>"
                
                with g1: st.markdown(render_glossary("🎯", T["card_beta_title"], f"{beta:.2f}", T["card_beta_desc"]), unsafe_allow_html=True)
                with g2: st.markdown(render_glossary("🚀", T["card_growth_title"], f"{info.get('earningsGrowth', 0.08)*100:.1f}%", T["card_growth_desc"]), unsafe_allow_html=True)
                with g3: st.markdown(render_glossary("🛡️", T["card_wacc_title"], f"{wacc*100:.1f}%", T["card_wacc_desc"]), unsafe_allow_html=True)
                with g4: st.markdown(render_glossary("💎", T["card_fair_title"], f"{curr} {primary_val:.2f}" if primary_val else "N/A", T["card_fair_desc"]), unsafe_allow_html=True)

                st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

                # ==================================================================
                # 免责声明
                # ==================================================================
                st.markdown(f"<div style='background: rgba(245,158,11,0.08); border: 1px solid rgba(245,158,11,0.25); border-left: 4px solid #f59e0b; border-radius: 10px; padding: 18px 22px;'><div style='color: #f59e0b; font-size: 14px; font-weight: 700; margin-bottom: 8px;'>{T['disclaimer_title']}</div><div style='color: #cbd5e1; font-size: 12px;'>{T['disclaimer_content']}</div></div>", unsafe_allow_html=True)

            except Exception as e:
                st.error(f"测算遇到异常，请检查代码或重试。错误详情: {e}")

if __name__ == "__main__":
    main()
