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
st.set_page_config(page_title="Universal Quant Terminal V10", page_icon="💎", layout="wide", initial_sidebar_state="collapsed")

@st.cache_resource
def get_yf_session():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    })
    return session

# ==============================================================================
# 2. 独家高级 CSS 视觉引擎 (Obsidian Glassmorphism)
# ==============================================================================
PREMIUM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;700;800&display=swap');

/* 全局深空背景 */
.stApp {
    background: radial-gradient(circle at 50% 0%, #111827 0%, #030712 60%, #000000 100%) !important;
    font-family: 'Inter', -apple-system, sans-serif !important;
    color: #f8fafc !important;
}

/* 隐藏顶部空白 */
.block-container { padding-top: 2rem !important; max-width: 1280px !important; }

/* 将所有的 st.container(border=True) 渲染成极简毛玻璃卡片 */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: rgba(17, 24, 39, 0.4) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 16px !important;
    box-shadow: 0 4px 24px -4px rgba(0, 0, 0, 0.5) !important;
    backdrop-filter: blur(12px) !important;
    -webkit-backdrop-filter: blur(12px) !important;
    transition: all 0.3s ease !important;
    padding: 8px !important;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border: 1px solid rgba(56, 189, 248, 0.3) !important;
    box-shadow: 0 8px 32px 0 rgba(56, 189, 248, 0.1) !important;
    transform: translateY(-2px);
}

/* 标题与文字发光优化 */
h1, h2, h3, h4, h5 {
    font-family: 'Inter', sans-serif !important;
    font-weight: 700 !important;
    color: #ffffff !important;
    letter-spacing: -0.5px !important;
}
h3 { color: #38bdf8 !important; text-shadow: 0 0 15px rgba(56, 189, 248, 0.2); margin-bottom: 15px !important; }

/* 数据指标 (Metrics) 极客字体 */
[data-testid="stMetricValue"] {
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 800 !important;
    font-size: 1.8rem !important;
    color: #f8fafc !important;
}
[data-testid="stMetricLabel"] {
    font-weight: 600 !important;
    color: #94a3b8 !important;
    font-size: 0.85rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
}
[data-testid="stMetricDelta"] {
    font-family: 'JetBrains Mono', monospace !important;
}

/* 输入框与选择框的暗黑处理 */
div[data-baseweb="input"] > div, div[data-baseweb="select"] > div {
    background-color: #0f172a !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 8px !important;
    color: #ffffff !important;
}

/* 提示框警报框精美化 */
[data-testid="stAlert"] {
    border-radius: 12px !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    background: rgba(15, 23, 42, 0.5) !important;
    backdrop-filter: blur(8px) !important;
}
</style>
"""
st.markdown(PREMIUM_CSS, unsafe_allow_html=True)

# ==============================================================================
# 3. 国际化多语言字典 (100% 完整保留原有所有解释)
# ==============================================================================
TEXTS = {
    "zh": {
        "title": "💎 智能量化金融终端 (ESG 旗舰版)",
        "subtitle": "融合 CAPM、DCF、WACC 与市场情绪测谎仪的专业机构级估值平台",
        "quick_tag": "🔥 热门快捷测评：",
        "input_label": "输入股票代码 (如 1155.KL, NVDA, AAPL)：",
        
        "param_title": "⚙️ 估值核心参数设定 (小白建议保持默认)",
        "param_tip": "💡 **何时建议手动调整？**\n* **永续增长率 (g)**：当您预期长期通胀显著高于/低于常态时微调。\n* **风险溢价 (ERP)**：市场极端恐慌（调高）或极度狂热（调低）时修正。",
        "erp_label": "股市风险溢价要求 (Equity Risk Premium)",
        "g2_label": "长期永续通胀增长率 (Terminal Growth Rate)",
        "esg_caption": "🌿 本系统已自动结合 ESG 行业风险溢价进行折现率修正。",
        
        "macro_title": "1. 🌐 动态宏观与资本成本",
        "macro_exp": "💡 **通俗解释：** Beta 衡量股票相对于大盘的波动率。Rf 是无风险国债利率。WACC 是你要求的最低及格线回报率。",
        "engine_title": "2. ⚙️ 智能自适应估值引擎",
        "engine_exp": "💡 **通俗解释：** 系统自动选择 DCF 或 DDM。g1 是前期高增长率，g2 是长期永续增长率。",
        "price": "当前市场价格",
        "wacc": "WACC / 折现率",
        "fair_val": "内在公道估值",
        "safe_buy": "20% 安全边际买点",
        
        "lie_title": "3. 💡 市场情绪测谎仪 (MARKET PSYCHOLOGY)",
        "lie_exp": "💡 **通俗解释：** 测谎仪通过二分法反向推导，看看当前的市场价格到底在幻想这家公司未来每年增长多少。",
        "ai_title": "4. 🤖 双视角 AI 投资顾问",
        "inc_title": "🔸 视角 A：保守派收息策略",
        "cap_title": "🔹 视角 B：进取派资本增值",
        "exec_title": "5. 🎯 最终投资评级与执行摘要",
        "rating_explain": "ℹ️ *学术释疑：‘市场情绪理性’代表投资者没有盲目炒作泡沫，但给出 ‘SELL’ 评级是因为当前市价高于内在公道价（缺乏安全边际）。即：好公司 ≠ 好价格。*",
        
        "plain_title": "6. 🗣️ 小白通俗翻译器",
        "fx_title": "7. 💱 跨境汇率风险提示",
        "fx_content": "- **提示：** 此乃美元计价资产，请注意美元兑马币 (USD/MYR) 的汇率风险。",
        
        "chart_title": "8. 📈 高级盘面与波动率回归分析",
        "beta_desc": "📊 **Beta 收益率特征线散点分布图说明：**\n* 每个点代表过往某一周的收益率联动。红线斜率即为真实 Beta。\n* **$R^2$ 解析**：点越密集说明越受大盘宏观主导；越分散说明有个股独立行情。",
        "glossary_title": "9. 📖 小白通俗金融词典",
        
        "g_beta_title": "🎯 Beta (波动敏感度)",
        "g_beta_desc": "衡量相对于大盘更活泼还是更稳健。>1 弹性高，<1 更抗跌。",
        "g_growth_title": "🚀 Growth (预期增长率)",
        "g_growth_desc": "未来盈利预计每年递增的比例。增长越快，公道价越高。",
        "g_wacc_title": "🛡️ WACC / 折现率",
        "g_wacc_desc": "你买入这家公司要求的最低年化回报门槛。",
        "g_fv_title": "💎 Fair Value (内在价)",
        "g_fv_desc": "剥离市场情绪，根据公司真实资产与赚钱能力算出的出厂价。",
        
        "disclaimer_title": "⚠️ 重要法律与风险免责声明",
        "disclaimer_1": "1. **非投资建议**：本系统结果仅供学术研究与交流，不构成财务建议。",
        "disclaimer_2": "2. **市场风险**：历史数据和量化模型无法绝对预知未来。",
        "disclaimer_3": "3. **自主决策**：任何决策应由投资者自行做出，开发者不承担法律责任。"
    },
    "en": {
        "title": "💎 Universal Quant Terminal",
        "subtitle": "Institutional-Grade Valuation Platform integrating CAPM, DCF, WACC & Lie Detector",
        "quick_tag": "🔥 Quick Select:",
        "input_label": "Enter Stock Ticker (e.g., 1155.KL, NVDA):",
        
        "param_title": "⚙️ Core Valuation Assumptions",
        "param_tip": "💡 **When to adjust?**\n* **Terminal (g)**: Adjust if long-term inflation outlook changes.\n* **ERP**: Adjust during extreme market panic or hype.",
        "erp_label": "Equity Risk Premium (ERP)",
        "g2_label": "Terminal Growth Rate (g)",
        "esg_caption": "🌿 ESG Sector Risk Premium automatically integrated.",
        
        "macro_title": "1. 🌐 DYNAMIC MACRO & COST OF CAPITAL",
        "macro_exp": "💡 **Plain English:** Beta measures volatility. WACC is your minimum required return.",
        "engine_title": "2. ⚙️ ADAPTIVE VALUATION ENGINE",
        "engine_exp": "💡 **Plain English:** Automatically selects DCF or DDM based on sector.",
        "price": "Market Price",
        "wacc": "WACC / Discount",
        "fair_val": "Intrinsic Fair Value",
        "safe_buy": "Safe Buy Target",
        
        "lie_title": "3. 💡 MARKET PSYCHOLOGY (LIE DETECTOR)",
        "lie_exp": "💡 **Plain English:** Reverse-engineers the growth rate investors are currently pricing in.",
        "ai_title": "4. 🤖 DUAL-PERSPECTIVE AI ADVISORY",
        "inc_title": "🔸 A: Conservative Income",
        "cap_title": "🔹 B: Capital Appreciation",
        "exec_title": "5. 🎯 FINAL EXECUTIVE SUMMARY",
        "rating_explain": "ℹ️ *Note: Rational Sentiment means no hype, but a SELL rating is triggered strictly if price exceeds fair value. Good company ≠ Good price.*",
        
        "plain_title": "6. 🗣️ PLAIN ENGLISH TRANSLATOR",
        "fx_title": "7. 💱 CROSS-BORDER FX RISK",
        "fx_content": "- **Note:** USD asset; monitor USD/MYR fluctuations.",
        
        "chart_title": "8. 📈 ADVANCED PRICE ACTION & REGRESSION",
        "beta_desc": "📊 **Beta Scatter Plot:** Each dot represents weekly returns. Slope = Beta.\n* **$R^2$**: Tight clustering means market-driven; high dispersion means independent trends.",
        "glossary_title": "9. 📖 BEGINNER'S GLOSSARY",
        
        "g_beta_title": "🎯 Beta",
        "g_beta_desc": "Volatility relative to market. >1 aggressive, <1 defensive.",
        "g_growth_title": "🚀 Expected Growth",
        "g_growth_desc": "Projected annual growth. Higher growth drives higher value.",
        "g_wacc_title": "🛡️ WACC",
        "g_wacc_desc": "Minimum hurdle rate of return required by investors.",
        "g_fv_title": "💎 Intrinsic Value",
        "g_fv_desc": "Calculated value based on assets and earning power, stripping away hype.",
        
        "disclaimer_title": "⚠️ Important Legal & Risk Disclaimer",
        "disclaimer_1": "1. **Educational Only**: Results are for academic research, not investment advice.",
        "disclaimer_2": "2. **Market Risk**: Quant models cannot perfectly predict the future.",
        "disclaimer_3": "3. **Independent Decision**: Users assume all trading risks."
    }
}

# ==============================================================================
# 4. 金融引擎逻辑 (100% 完整保留原有逻辑)
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
            return round((0.67 * raw_beta) + (0.33 * 1.0), 2), 'Blume Adjusted Regression'
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
# 5. 图表生成 (完美融入暗黑主题)
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
    
    fig.update_layout(
        xaxis_rangeslider_visible=False, height=350, margin=dict(l=0, r=0, t=10, b=0),
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#94a3b8'),
        xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )
    return fig

def draw_beta_scatter(engine):
    if engine.scatter_data is None: return None
    stock_ret, market_ret = engine.scatter_data.iloc[:, 0], engine.scatter_data.iloc[:, 1]
    
    corr = np.corrcoef(stock_ret, market_ret)[0, 1]
    r_squared = corr ** 2 if not np.isnan(corr) else 0.0

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=market_ret, y=stock_ret, mode='markers', marker=dict(color='#0ea5e9', size=7, opacity=0.8), name='Returns'))
    x_range = np.linspace(market_ret.min(), market_ret.max(), 100)
    fig.add_trace(go.Scatter(x=x_range, y=engine.beta * x_range, mode='lines', line=dict(color='#f43f5e', width=2), name='Fit Line'))
    
    fig.update_layout(
        title=dict(text=f"Beta Regression (Beta = {engine.beta:.2f} | R² = {r_squared:.2f})", font=dict(color='#ffffff')),
        xaxis_title="Market Benchmark (%)", yaxis_title="Stock Return (%)", 
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#94a3b8'),
        xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
        showlegend=False, height=330, margin=dict(l=0, r=0, t=35, b=0)
    )
    return fig

# ==============================================================================
# 6. UI 渲染与排版构建
# ==============================================================================
def main():
    # 顶部导航
    c1, c2 = st.columns([3, 1])
    with c2:
        selected_lang = st.selectbox("🌐", options=["中文", "English"], index=0, label_visibility="collapsed")
        lang_key = "zh" if selected_lang == "中文" else "en"
        T = TEXTS[lang_key]

    with c1:
        st.markdown(f"<h1 style='font-size: 2.2rem; margin-bottom: 0;'>{T['title']}</h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: #0ea5e9; font-weight: 600; font-size: 14px; margin-top: -5px;'>{T['subtitle']}</p>", unsafe_allow_html=True)
    st.write("---")

    # 控制台
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

    # 引擎计算区
    if ticker_input:
        with st.spinner("Initializing Deep Valuation Engine..."):
            engine = UniversalQuantEngine(ticker_input)
            val, implied_g = engine.run_valuation(custom_erp, custom_g2)

            st.markdown(f"<h3 style='margin-top: 25px;'>🏢 {engine.name} ({engine.ticker}) <span style='font-size:14px; color:#94a3b8;'>| Sector: {engine.sector}</span></h3>", unsafe_allow_html=True)

            # 模块 1 & 2
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

            # 核心估值条
            st.write("---")
            p1, p2, p3 = st.columns(3)
            p1.metric(T['price'], f"{engine.price:.2f}")
            p2.metric(T['fair_val'], f"{val:.2f}")
            p3.metric(T['safe_buy'], f"{(val * 0.8):.2f}")

            if val > 0 and engine.price > 0:
                price_to_val = engine.price / val

                # 模块 3 & 4 (测谎仪 & AI)
                st.markdown(f"<br><h3>{T['lie_title']}</h3>", unsafe_allow_html=True)
                implied_g_str = f"{implied_g * 100:.2f}%" if implied_g is not None else "N/A"
                
                if implied_g is not None:
                    if implied_g > 0.40: diag, d_color = "🔥 EXTREME HYPE (Bubble)", "#ef4444"
                    elif implied_g < 0.0: diag, d_color = "🥶 EXTREME PESSIMISM", "#38bdf8"
                    else: diag, d_color = "⚖️ MODERATE EXPECTATIONS", "#22c55e"
                else:
                    diag, d_color = "Data Unavailable", "#94a3b8"

                with st.container(border=True):
                    st.markdown(f"To justify the price of **{engine.price:.2f}**, the market implies a Growth Rate of <b style='color:#0ea5e9; font-size:20px;'>{implied_g_str}</b> per year.", unsafe_allow_html=True)
                    st.markdown(f"Diagnosis: <b style='color:{d_color};'>{diag}</b>", unsafe_allow_html=True)
                    st.caption(T['lie_exp'])

                # 模块 5 最终评级
                st.markdown(f"<br><h3>{T['exec_title']}</h3>", unsafe_allow_html=True)
                if price_to_val <= 0.70 and (implied_g is not None and implied_g < 0.0):
                    rating, reason, r_col = '🟢 STRONG BUY', f'Extreme pessimism creates massive margin of safety.', "#22c55e"
                elif price_to_val <= 0.85:
                    rating, reason, r_col = '🟢 BUY', f'Solid value mispricing. Price meets 20% Margin of Safety.', "#22c55e"
                elif 0.85 < price_to_val <= 1.15:
                    rating, reason, r_col = '🟡 HOLD', f'Fairly valued. Price aligns with intrinsic value.', "#f59e0b"
                elif 1.15 < price_to_val <= 1.40:
                    rating, reason, r_col = '🔴 SELL', f'Overvalued. Price exceeds intrinsic value.', "#ef4444"
                else:
                    rating, reason, r_col = '🔴 STRONG SELL', f'Severe bubble risk. Priced for perfection.', "#ef4444"

                with st.container(border=True):
                    st.markdown(f"**Final Rating:** <span style='color:{r_col}; font-size:18px; font-weight:800;'>{rating}</span>", unsafe_allow_html=True)
                    st.markdown(f"**Justification:** {reason}")
                    st.caption(T['rating_explain'])

                # 模块 6 & 7
                col_6, col_7 = st.columns(2)
                with col_6:
                    st.markdown(f"**{T['plain_title']}**")
                    with st.container(border=True):
                        st.write(f"- Hurdle Rate: {engine.r * 100:.2f}% (Min return)")
                        if implied_g is not None:
                            st.write(f"- Market Sentiment: {implied_g * 100:.2f}%")
                
                with col_7:
                    if not engine.is_malaysia:
                        st.markdown(f"**{T['fx_title']}**")
                        with st.container(border=True):
                            st.write(T['fx_content'])
                            ws_tgt = engine.info.get('targetMeanPrice')
                            if ws_tgt: st.write(f"🏛️ WS Target: **${ws_tgt:.2f}** | Model: **${val:.2f}**")

            # 模块 8 图表
            st.markdown(f"<br><h3>{T['chart_title']}</h3>", unsafe_allow_html=True)
            c_chart1, c_chart2 = st.columns([1.5, 1])
            with c_chart1:
                with st.container(border=True):
                    st.plotly_chart(draw_pro_candlestick(engine.ticker, engine.session), use_container_width=True)
            with c_chart2:
                with st.container(border=True):
                    st.plotly_chart(draw_beta_scatter(engine), use_container_width=True)
                    st.caption(T['beta_desc'])

            # 模块 9 词典
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

    # 模块 10 免责
    st.write("---")
    with st.container(border=True):
        st.markdown(f"**{T['disclaimer_title']}**")
        st.caption(T['disclaimer_1'] + "<br>" + T['disclaimer_2'] + "<br>" + T['disclaimer_3'], unsafe_allow_html=True)

if __name__ == '__main__':
    main()
