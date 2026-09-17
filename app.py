import datetime
import numpy as np
import pandas as pd
import requests
import yfinance as yf
import streamlit as st
import plotly.graph_objects as go

# ==============================================================================
# 1. 页面基本配置
# ==============================================================================
st.set_page_config(page_title="Universal Quant Terminal V17", page_icon="💎", layout="wide", initial_sidebar_state="collapsed")

@st.cache_resource
def get_yf_session():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    })
    return session

# ==============================================================================
# 2. 绝对统治级 CSS 视觉引擎 (强制接管所有便当盒边框，绝不失效)
# ==============================================================================
PREMIUM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;700;800&display=swap');

/* 全局深空背景 */
.stApp {
    background: #030712 !important;
    font-family: 'Inter', -apple-system, sans-serif !important;
    color: #f8fafc !important;
}
.block-container { padding-top: 2rem !important; max-width: 1280px !important; }

/* 🌟 核心：强制所有 st.container(border=True) 变成极粗、高对比度、带强烈外发光的便当盒 */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: #0b132b !important; /* 高对比度深蓝实底，告别融为一体 */
    border: 3px solid #ff2a6d !important; /* 3像素极粗霓虹粉红边框，绝对一眼可见 */
    border-radius: 16px !important;
    box-shadow: 0 0 30px rgba(255, 42, 109, 0.6) !important; /* 强烈的外发光特效 */
    transition: all 0.3s ease !important;
    padding: 22px 26px !important;
    margin-bottom: 16px !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border: 3px solid #ff5e92 !important;
    box-shadow: 0 0 40px rgba(255, 42, 109, 0.9) !important;
    transform: translateY(-2px);
}

/* 按钮专属暗黑极客样式 */
.stButton > button {
    background: #0f172a !important;
    color: #ff2a6d !important;
    border: 2px solid #ff2a6d !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    transition: all 0.22s ease !important;
}
.stButton > button:hover {
    background: rgba(255, 42, 109, 0.25) !important;
    color: #ffffff !important;
    box-shadow: 0 0 20px rgba(255, 42, 109, 0.6) !important;
    transform: translateY(-2px);
}

label { color: #cbd5e1 !important; font-weight: 500 !important; }
p { color: #e2e8f0 !important; }
h1, h2, h3, h4, h5 { font-family: 'Inter', sans-serif !important; font-weight: 700 !important; color: #ffffff !important; }
h3 { color: #ff2a6d !important; text-shadow: 0 0 15px rgba(255, 42, 109, 0.4); margin-top: 10px !important; margin-bottom: 15px !important; }

/* 指标与输入框美化 */
[data-testid="stMetricValue"] { font-family: 'JetBrains Mono', monospace !important; font-weight: 800 !important; font-size: 1.9rem !important; color: #ffffff !important; }
[data-testid="stMetricLabel"] { font-weight: 600 !important; color: #94a3b8 !important; font-size: 0.85rem !important; text-transform: uppercase; }
div[data-baseweb="input"] > div, div[data-baseweb="select"] > div { background-color: #0f172a !important; border: 2px solid #ff2a6d !important; border-radius: 8px !important; color: #ffffff !important; }
</style>
"""
st.markdown(PREMIUM_CSS, unsafe_allow_html=True)

# ==============================================================================
# 3. 国际化多语言字典
# ==============================================================================
TEXTS = {
    "zh": {
        "title": "💎 智能量化金融终端 (ESG 旗舰版)",
        "subtitle": "融合 CAPM、DCF、WACC 与市场情绪测谎仪的专业机构级估值平台",
        "quick_tag": "🔥 热门快捷测评：",
        "input_label": "输入股票代码 (如 1155.KL, NVDA)：",
        "param_title": "⚙️ 估值核心参数设定 (小白建议保持默认)",
        "param_tip": "💡 **何时建议手动调整？** 永续增长率 (g)：长期通胀显著变化时微调。风险溢价 (ERP)：市场极端恐慌或狂热时修正。",
        "erp_label": "股市风险溢价要求 (ERP)",
        "g2_label": "长期永续通胀增长率 (Terminal Growth)",
        "esg_caption": "🌿 本系统已自动结合 ESG 行业风险溢价进行折现率修正。",
        
        "macro_title": "1. 🌐 动态宏观与资本成本",
        "macro_exp": "💡 Beta 衡量波动率。WACC 是要求的最低及格线回报率。",
        "engine_title": "2. ⚙️ 智能自适应估值引擎",
        "engine_exp": "💡 自动选择 DCF 或 DDM。g1 是前期高增长，g2 是永续增长。",
        "price": "当前市场价格",
        "fair_val": "内在公道估值",
        "safe_buy": "20% 安全边际买点",
        
        "lie_title": "3. 💡 市场情绪测谎仪",
        "lie_exp": "💡 反向推导当前市场价格到底在幻想这家公司未来每年增长多少。",
        "exec_title": "4. 🎯 最终投资评级",
        "rating_explain": "ℹ️ *学术释疑：‘情绪理性’代表未盲目炒作，但‘SELL’是因为当前市价高于内在公道价。*",
        
        "plain_title": "5. 🗣️ 小白通俗翻译器",
        "fx_title": "6. 💱 跨境汇率风险提示",
        "fx_content": "提示: 此乃美元计价资产，请注意 USD/MYR 汇率风险。",
        "my_fx_content": "提示: 本地资产计价 (MYR)，无直接跨境外汇风险暴露。",

        "ws_title": "7. 🏛️ 华尔街投行分析师共识",
        "ws_mean": "投行平均目标价",
        "ws_range": "目标预测区间 (Low-High)",
        "ws_rating": "机构综合评级",
        "ws_match": "✅ 模型算出的公道价与华尔街机构预测误差在 15% 以内，估值高度吻合！",

        "chart_title": "8. 📈 高级盘面与波动率回归分析",
        "beta_desc": "📊 红线斜率即为真实 Beta。R² 越小代表个股独立行情越强。",
        "glossary_title": "9. 📖 小白通俗金融词典",
        "g_beta_title": "🎯 Beta (波动敏感度)",
        "g_beta_desc": ">1 弹性高，涨跌猛；<1 抗跌属性强。",
        "g_growth_title": "🚀 Growth (预期增长率)",
        "g_growth_desc": "预期盈利递增比例，增长越快身价越高。",
        "g_wacc_title": "🛡️ WACC / 折现率",
        "g_wacc_desc": "买入要求的最低年化回报门槛。",
        "g_fv_title": "💎 Fair Value (内在价)",
        "g_fv_desc": "剥离情绪，依据造血能力算出的出厂价。",
        "disclaimer_title": "⚠️ 重要法律与风险免责声明",
        "disclaimer_1": "1. 仅供学术研究与交流，不构成财务建议。"
    },
    "en": {
        "title": "💎 Universal Quant Terminal",
        "subtitle": "Institutional-Grade Valuation Platform integrating CAPM, DCF, WACC & Lie Detector",
        "quick_tag": "🔥 Quick Select:",
        "input_label": "Enter Stock Ticker (e.g., 1155.KL, NVDA):",
        "param_title": "⚙️ Core Valuation Assumptions",
        "param_tip": "💡 Adjust Terminal (g) for inflation outlook, and ERP for extreme market cycles.",
        "erp_label": "Equity Risk Premium (ERP)",
        "g2_label": "Terminal Growth Rate (g)",
        "esg_caption": "🌿 ESG Sector Risk Premium automatically integrated.",
        
        "macro_title": "1. 🌐 DYNAMIC MACRO & WACC",
        "macro_exp": "💡 Beta measures volatility. WACC is your minimum required return.",
        "engine_title": "2. ⚙️ ADAPTIVE VALUATION ENGINE",
        "engine_exp": "💡 Automatically selects DCF or DDM based on sector.",
        "price": "Market Price",
        "fair_val": "Intrinsic Fair Value",
        "safe_buy": "Safe Buy Target",
        
        "lie_title": "3. 💡 MARKET PSYCHOLOGY (LIE DETECTOR)",
        "lie_exp": "💡 Reverse-engineers the growth rate investors are currently pricing in.",
        "exec_title": "4. 🎯 FINAL EXECUTIVE SUMMARY",
        "rating_explain": "ℹ️ *Rational Sentiment means no hype, but a SELL rating is triggered if price exceeds fair value.*",
        
        "plain_title": "5. 🗣️ PLAIN ENGLISH TRANSLATOR",
        "fx_title": "6. 💱 CROSS-BORDER FX RISK",
        "fx_content": "Note: USD asset; monitor USD/MYR fluctuations.",
        "my_fx_content": "Note: Local MYR asset; no direct foreign exchange exposure.",

        "ws_title": "7. 🏛️ WALL STREET CONSENSUS",
        "ws_mean": "Analyst Avg Target",
        "ws_range": "Target Range (Low-High)",
        "ws_rating": "Consensus Rating",
        "ws_match": "✅ Your Valuation aligns tightly with Wall Street targets (within 15% margin)!",

        "chart_title": "8. 📈 PRICE ACTION & REGRESSION",
        "beta_desc": "📊 Slope = Beta. High dispersion means independent trends.",
        "glossary_title": "9. 📖 BEGINNER'S GLOSSARY",
        "g_beta_title": "🎯 Beta",
        "g_beta_desc": ">1 aggressive, <1 defensive.",
        "g_growth_title": "🚀 Expected Growth",
        "g_growth_desc": "Projected annual growth.",
        "g_wacc_title": "🛡️ WACC",
        "g_wacc_desc": "Minimum hurdle rate of return.",
        "g_fv_title": "💎 Intrinsic Value",
        "g_fv_desc": "Value based on earning power, stripping away hype.",
        "disclaimer_title": "⚠️ Important Legal & Risk Disclaimer",
        "disclaimer_1": "1. Academic research only, not investment advice."
    }
}

# ==============================================================================
# 4. 金融引擎逻辑
# ==============================================================================
def get_fin_metric(df, keyword, default=0.0):
    if df is None or df.empty: return default
    try:
        matches = df[df.index.str.contains(keyword, case=False, na=False)]
        if not matches.empty:
            val = matches.iloc[0, 0]
            return float(val) if pd.notna(val) else default
    except Exception: pass
    return default

class UniversalQuantEngine:
    def __init__(self, ticker):
        self.ticker = ticker.strip().upper()
        self.session = get_yf_session()
        self.stock = yf.Ticker(self.ticker, session=self.session)
        
        try:
            self.info = self.stock.info
            if 'symbol' not in self.info: raise ValueError("Data missing")
        except Exception:
            st.error(f"⚠️ Yahoo Finance data unavailable for {self.ticker}.")
            st.stop() 

        self.name = self.info.get('longName', 'Unknown')
        self.sector = self.info.get('sector', 'Unknown')
        self.is_malaysia = self.ticker.endswith('.KL')
        
        self.price = self.info.get('currentPrice', self.info.get('previousClose', 0))
        self.shares = self.info.get('sharesOutstanding', 1)
        
        self.bs = self.stock.balance_sheet
        self.cash = self.info.get('totalCash') or get_fin_metric(self.bs, 'Cash And Cash Equivalents')
        self.debt = self.info.get('totalDebt') or get_fin_metric(self.bs, 'Total Debt')
        self.scatter_data = None 

    def get_esg_adjustment(self):
        if self.sector in ['Energy', 'Basic Materials', 'Industrials']: return 0.015, "🔴 High ESG Risk (+1.5%)"
        elif self.sector in ['Technology', 'Healthcare', 'Financial Services']: return -0.005, "🟢 Low ESG Risk (-0.5%)"
        return 0.00, "⚪ Neutral"

    def compute_blume_beta(self):
        fallback = 1.0
        try:
            market_sym = '^KLSE' if self.is_malaysia else '^GSPC'
            s_hist = yf.Ticker(self.ticker, session=self.session).history(period='3y', interval='1mo')
            m_hist = yf.Ticker(market_sym, session=self.session).history(period='3y', interval='1mo')
            
            s_ret = s_hist['Close'].pct_change().dropna()
            m_ret = m_hist['Close'].pct_change().dropna()
            aligned = pd.concat([s_ret, m_ret], axis=1).dropna()
            
            if len(aligned) < 12: return fallback, 'Insufficient Data'
            self.scatter_data = aligned 

            cov = np.cov(aligned.iloc[:, 0], aligned.iloc[:, 1])[0, 1]
            var = np.var(aligned.iloc[:, 1], ddof=1)
            raw_beta = cov / var
            
            if not np.isfinite(raw_beta) or raw_beta < 0.2 or raw_beta > 2.5: return fallback, 'Outlier Adjusted'
            return round((0.67 * raw_beta) + (0.33 * 1.0), 2), 'Blume Adjusted'
        except Exception:
            return fallback, 'System Default'

    def run_valuation(self, erp, terminal_g):
        self.beta, self.beta_type = self.compute_blume_beta()
        self.rf = 0.038 if self.is_malaysia else 0.042
        self.esg_adj, self.esg_tag = self.get_esg_adjustment()
        
        self.ke = self.rf + (self.beta * erp) + self.esg_adj
        self.tax = 0.24 if self.is_malaysia else 0.21
        
        market_cap = self.price * self.shares
        total_cap = market_cap + self.debt
        w_e = market_cap / total_cap if total_cap > 0 else 1
        w_d = self.debt / total_cap if total_cap > 0 else 0
        
        int_exp = abs(self.info.get('interestExpense', 0))
        kd = min((int_exp / self.debt) if self.debt > 0 else 0.05, 0.10)
        self.wacc = (w_e * self.ke) + (w_d * kd * (1 - self.tax))

        raw_fcf = self.info.get('freeCashflow', 0)
        if raw_fcf <= 0: raw_fcf = get_fin_metric(self.stock.cashflow, 'Free Cash Flow')
        div = self.info.get('dividendRate', self.info.get('trailingAnnualDividendRate', 0))

        if self.sector in ['Financial Services', 'Real Estate', 'Utilities']:
            self.model_name = 'Dividend Discount Model (DDM)'
            self.r = self.ke
            self.cf = div if div > 0 else raw_fcf
            self.per_share = True
        else:
            self.model_name = 'Discounted Cash Flow (DCF)'
            self.r = self.wacc
            self.cf = raw_fcf
            self.per_share = False

        self.g1 = min(max(self.info.get('earningsGrowth', 0), 0.05), 0.25)
        self.g2 = terminal_g
        self.horizon = 10 if self.sector in ['Technology', 'Communication Services'] else 5

        return self.calculate_pv(self.g1), self.find_implied_growth()

    def calculate_pv(self, test_g):
        if self.cf <= 0 or self.r <= self.g2: return 0
        pv1, curr_cf = 0, self.cf
        for y in range(1, self.horizon + 1):
            curr_cf *= (1 + test_g)
            pv1 += curr_cf / ((1 + self.r) ** y)
        pv_tv = (curr_cf * (1 + self.g2)) / (self.r - self.g2) / ((1 + self.r) ** self.horizon)
        total_pv = pv1 + pv_tv
        if self.per_share: return total_pv
        val = total_pv + self.cash - self.debt
        return val / self.shares if self.shares > 0 else 0

    def find_implied_growth(self):
        if self.price <= 0 or self.cf <= 0: return None
        low, high = -0.50, 2.00
        for _ in range(50):
            mid = (low + high) / 2
            if self.calculate_pv(mid) < self.price: low = mid
            else: high = mid
        return mid

# ==============================================================================
# 5. 图表生成 
# ==============================================================================
def draw_pro_candlestick(ticker, session):
    hist = yf.Ticker(ticker, session=session).history(period="1y", interval="1d")
    if hist.empty: return None
    hist['MA20'] = hist['Close'].rolling(window=20).mean()
    hist['MA50'] = hist['Close'].rolling(window=50).mean()
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], name='Price'))
    fig.add_trace(go.Scatter(x=hist.index, y=hist['MA20'], line=dict(color='#f59e0b', width=1.5), name='20-Day SMA'))
    fig.add_trace(go.Scatter(x=hist.index, y=hist['MA50'], line=dict(color='#0ea5e9', width=1.5), name='50-Day SMA'))
    fig.update_layout(xaxis_rangeslider_visible=False, height=350, margin=dict(l=0, r=0, t=10, b=0), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#94a3b8'), xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'), yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'), legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01))
    return fig

def draw_beta_scatter(engine):
    if engine.scatter_data is None: return None
    stock_ret, market_ret = engine.scatter_data.iloc[:, 0], engine.scatter_data.iloc[:, 1]
    corr = np.corrcoef(stock_ret, market_ret)[0, 1]
    r_squared = corr ** 2 if not np.isnan(corr) else 0.0
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=market_ret, y=stock_ret, mode='markers', marker=dict(color='#0ea5e9', size=7, opacity=0.8), name='Returns'))
    x_range = np.linspace(market_ret.min(), market_ret.max(), 100)
    fig.add_trace(go.Scatter(x=x_range, y=engine.beta * x_range, mode='lines', line=dict(color='#ff2a6d', width=2), name='Fit Line'))
    fig.update_layout(title=dict(text=f"Beta Regression (Beta = {engine.beta:.2f} | R² = {r_squared:.2f})", font=dict(color='#ffffff')), xaxis_title="Market Benchmark (%)", yaxis_title="Stock Return (%)", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#94a3b8'), xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'), yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'), showlegend=False, height=330, margin=dict(l=0, r=0, t=35, b=0))
    return fig

# ==============================================================================
# 6. UI 渲染与排版构建 (全部采用带边框容器)
# ==============================================================================
def main():
    c1, c2 = st.columns([3, 1])
    with c2:
        selected_lang = st.selectbox("🌐", options=["中文", "English"], index=0, label_visibility="collapsed")
        lang_key = "zh" if selected_lang == "中文" else "en"
        T = TEXTS[lang_key]

    with c1:
        st.markdown(f"<h1 style='font-size: 2.2rem; margin-bottom: 0;'>{T['title']}</h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: #ff2a6d; font-weight: 600; font-size: 14px; margin-top: -5px;'>{T['subtitle']}</p>", unsafe_allow_html=True)
    st.write("---")

    with st.container(border=True):
        if "ticker_input" not in st.session_state: st.session_state.ticker_input = "NVDA"
        def set_ticker(t): st.session_state.ticker_input = t
        
        st.write(T['quick_tag'])
        q1, q2, q3, q4 = st.columns(4)
        q1.button("🇺🇸 NVDA", on_click=set_ticker, args=("NVDA",), use_container_width=True)
        q2.button("🇺🇸 AAPL", on_click=set_ticker, args=("AAPL",), use_container_width=True)
        q3.button("🇲🇾 MAYBANK", on_click=set_ticker, args=("1155.KL",), use_container_width=True)
        q4.button("🇲🇾 TENAGA", on_click=set_ticker, args=("5347.KL",), use_container_width=True)
        
        col_in1, col_in2 = st.columns([2, 2])
        with col_in1:
            ticker_input = st.text_input(T['input_label'], key="ticker_input")
        
        with st.expander(T['param_title'], expanded=False):
            st.info(T['param_tip'])
            c_erp, c_g2 = st.columns(2)
            custom_erp = c_erp.slider(T['erp_label'], 4.0, 7.0, 5.0, 0.1) / 100
            custom_g2 = c_g2.slider(T['g2_label'], 1.0, 3.5, 2.0, 0.1) / 100
        st.caption(T['esg_caption'])

    if ticker_input:
        with st.spinner("Initializing Deep Valuation Engine..."):
            engine = UniversalQuantEngine(ticker_input)
            val, implied_g = engine.run_valuation(custom_erp, custom_g2)

            st.markdown(f"<h3 style='margin-top: 25px;'>🏢 {engine.name} ({engine.ticker}) <span style='font-size:14px; color:#94a3b8;'>| Sector: {engine.sector}</span></h3>", unsafe_allow_html=True)

            # --- Row 1: Macro & Engine ---
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                with st.container(border=True):
                    st.markdown(f"**{T['macro_title']}**")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Beta Risk", f"{engine.beta:.2f}")
                    c2.metric("Rf Rate", f"{engine.rf * 100:.2f}%")
                    c3.metric("WACC", f"{engine.r * 100:.2f}%")
                    st.caption(T['macro_exp'])
            with col_m2:
                with st.container(border=True):
                    st.markdown(f"**{T['engine_title']}** ({engine.model_name})")
                    e1, e2, e3 = st.columns(3)
                    e1.metric("Stage 1", f"{engine.horizon} Yrs")
                    e2.metric("Base g1", f"{engine.g1 * 100:.2f}%")
                    e3.metric("Term. g2", f"{engine.g2 * 100:.2f}%")
                    st.caption(T['engine_exp'])

            st.write("---")
            
            # --- Row 2: 三剑客卡片 (全部包裹进独立便当盒) ---
            p1_col, p2_col, p3_col = st.columns(3)
            with p1_col:
                with st.container(border=True):
                    st.metric(T['price'], f"{engine.price:.2f}")
                    st.caption("实时市场盘口基准价")
            with p2_col:
                with st.container(border=True):
                    st.metric(T['fair_val'], f"{val:.2f}")
                    st.caption("AI 核心量化内在公道价")
            with p3_col:
                with st.container(border=True):
                    st.metric(T['safe_buy'], f"{(val * 0.8):.2f}")
                    st.caption("含 20% 安全边际防守买点")

            if val > 0 and engine.price > 0:
                price_to_val = engine.price / val

                # --- Row 3: 测谎仪与评级 ---
                col_lie, col_rating = st.columns(2)
                with col_lie:
                    with st.container(border=True):
                        st.markdown(f"**{T['lie_title']}**")
                        implied_g_str = f"{implied_g * 100:.2f}%" if implied_g is not None else "N/A"
                        if implied_g is not None:
                            if implied_g > 0.40: diag, d_color = "🔥 EXTREME HYPE (Bubble)", "#ef4444"
                            elif implied_g < 0.0: diag, d_color = "🥶 EXTREME PESSIMISM", "#38bdf8"
                            else: diag, d_color = "⚖️ MODERATE EXPECTATIONS", "#22c55e"
                        else:
                            diag, d_color = "Data Unavailable", "#94a3b8"

                        st.markdown(f"Market Implied Growth Rate: <b style='color:#ff2a6d; font-size:22px;'>{implied_g_str}</b>", unsafe_allow_html=True)
                        st.markdown(f"Diagnosis: <b style='color:{d_color};'>{diag}</b>", unsafe_allow_html=True)
                        st.caption(T['lie_exp'])

                with col_rating:
                    with st.container(border=True):
                        st.markdown(f"**{T['exec_title']}**")
                        if price_to_val <= 0.70 and (implied_g is not None and implied_g < 0.0):
                            rating, reason, r_col = '🟢 STRONG BUY', 'Extreme pessimism creates massive margin of safety.', "#22c55e"
                        elif price_to_val <= 0.85:
                            rating, reason, r_col = '🟢 BUY', 'Solid value mispricing. Price meets 20% Margin of Safety.', "#22c55e"
                        elif 0.85 < price_to_val <= 1.15:
                            rating, reason, r_col = '🟡 HOLD', 'Fairly valued. Price aligns with intrinsic value.', "#f59e0b"
                        elif 1.15 < price_to_val <= 1.40:
                            rating, reason, r_col = '🔴 SELL', 'Overvalued. Price exceeds intrinsic value.', "#ef4444"
                        else:
                            rating, reason, r_col = '🔴 STRONG SELL', 'Severe bubble risk. Priced for perfection.', "#ef4444"
                            
                        st.markdown(f"Rating: <span style='color:{r_col}; font-size:20px; font-weight:800;'>{rating}</span>", unsafe_allow_html=True)
                        st.markdown(f"**Justification:** {reason}")
                        st.caption(T['rating_explain'])

                # --- Row 4: 翻译器与汇率 ---
                col_6, col_7 = st.columns(2)
                with col_6:
                    with st.container(border=True):
                        st.markdown(f"**{T['plain_title']}**")
                        st.write(f"- Hurdle Rate: {engine.r * 100:.2f}% (Min return)")
                        if implied_g is not None:
                            st.write(f"- Market Sentiment: {implied_g * 100:.2f}%")
                
                with col_7:
                    with st.container(border=True):
                        st.markdown(f"**{T['fx_title']}**")
                        if not engine.is_malaysia:
                            st.write(T['fx_content'])
                        else:
                            st.write(T['my_fx_content'])

                # --- Row 5: 华尔街共识 (美股专属) ---
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
                                st.markdown(f"<div style='color:#94a3b8; font-size:13px; font-weight:600;'>{T['ws_mean']}</div>", unsafe_allow_html=True)
                                st.markdown(f"<div style='font-size:24px; font-weight:800; font-family:JetBrains Mono;'>${target_mean:.2f}</div>", unsafe_allow_html=True)
                                st.markdown(f"<div style='color:#ff2a6d; font-size:12px;'>👥 {num_analysts} Analysts</div>", unsafe_allow_html=True)
                                
                        with ws_col2:
                            with st.container(border=True):
                                st.markdown(f"<div style='color:#94a3b8; font-size:13px; font-weight:600;'>{T['ws_range']}</div>", unsafe_allow_html=True)
                                st.markdown(f"<div style='font-size:20px; font-weight:800; font-family:JetBrains Mono;'>${target_low:.2f} - ${target_high:.2f}</div>", unsafe_allow_html=True)
                                st.markdown(f"<div style='color:#cbd5e1; font-size:12px;'>Low / High Target</div>", unsafe_allow_html=True)

                        with ws_col3:
                            with st.container(border=True):
                                st.markdown(f"<div style='color:#94a3b8; font-size:13px; font-weight:600;'>{T['ws_rating']}</div>", unsafe_allow_html=True)
                                st.markdown(f"<div style='font-size:22px; font-weight:800; font-family:JetBrains Mono;'>{rec_key}</div>", unsafe_allow_html=True)
                                st.markdown(f"<div style='color:#4ade80; font-size:12px;'>🏛️ Consensus View</div>", unsafe_allow_html=True)

                        if val > 0 and abs((val - target_mean) / target_mean) <= 0.15:
                            st.success(T['ws_match'], icon="✅")

            # --- Row 6: 图表 ---
            st.markdown(f"<br><h3>{T['chart_title']}</h3>", unsafe_allow_html=True)
            c_chart1, c_chart2 = st.columns([1.5, 1])
            with c_chart1:
                with st.container(border=True):
                    st.plotly_chart(draw_pro_candlestick(engine.ticker, engine.session), use_container_width=True)
            with c_chart2:
                with st.container(border=True):
                    st.plotly_chart(draw_beta_scatter(engine), use_container_width=True)
                    st.caption(T['beta_desc'])

            # --- Row 7: 词典 ---
            st.markdown(f"<br><h3>{T['glossary_title']}</h3>", unsafe_allow_html=True)
            g1, g2, g3, g4 = st.columns(4)
            with g1:
                with st.container(border=True):
                    st.markdown(f"**{T['g_beta_title']}**")
                    st.caption(T['g_beta_desc'])
            with g2:
                with st.container(border=True):
                    st.markdown(f"**{T['g_growth_title']}**")
                    st.caption(T['g_growth_desc'])
            with g3:
                with st.container(border=True):
                    st.markdown(f"**{T['g_wacc_title']}**")
                    st.caption(T['g_wacc_desc'])
            with g4:
                with st.container(border=True):
                    st.markdown(f"**{T['g_fv_title']}**")
                    st.caption(T['g_fv_desc'])

    # 免责声明
    st.write("---")
    with st.container(border=True):
        st.markdown(f"**{T['disclaimer_title']}**")
        st.caption(T['disclaimer_1'], unsafe_allow_html=True)

if __name__ == '__main__':
    main()
