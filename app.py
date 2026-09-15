import datetime
import numpy as np
import pandas as pd
import requests
import yfinance as yf
import streamlit as st
import plotly.graph_objects as go

# ==============================================================================
# 1. 页面配置与反爬虫伪装 (Anti-Rate Limit)
# ==============================================================================
st.set_page_config(page_title="Universal Quant Terminal V5.0", page_icon="📈", layout="wide")

@st.cache_resource
def get_yf_session():
    """Create a persistent session with a browser disguise to prevent Yahoo blocks."""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    })
    return session

# ==============================================================================
# 2. 中英双语词典 (Bilingual Dictionary)
# ==============================================================================
TEXTS = {
    "zh": {
        "title": "💡 智能量化金融终端 (ESG 增强版)",
        "subtitle": "融合 CAPM、DCF 与 ESG 风险溢价的专业估值系统 | 支持马股 (Bursa) 与美股 (US)",
        "step1": "📌 步骤 1：选择股票",
        "quick_tag": "🔥 热门快捷测评：",
        "input_label": "手动输入股票代码 (如 1155.KL, NVDA)：",
        "btn_analyze": "开始深度量化测算 🔎",
        "step2": "⚙️ 步骤 2：宏观与估值参数设定 (小白可保持默认)",
        "param_g": "长期永续增长率 (Terminal Growth, g)",
        "param_erp": "市场风险溢价要求 (Equity Risk Premium)",
        "esg_tag": "🌿 自动启用 ESG 行业风险溢价调节",
        "res_header": "📊 估值核心面板",
        "price": "当前市场价格",
        "wacc": "WACC / 折现率",
        "fair_val": "内在公道估值",
        "margin": "20% 安全边际买点",
        "lie_detector": "💡 市场情绪测谎仪 (Implied Growth)",
        "ws_header": "🏛️ 华尔街机构一致预期 (Wall Street Consensus)",
        "chart_header": "📈 高级价格行为与回归分析",
        "glossary_header": "📖 小白通俗金融词典 (Beginner's Glossary)"
    },
    "en": {
        "title": "💡 Universal Quant Terminal (ESG Edition)",
        "subtitle": "Professional Valuation System integrating CAPM, DCF & ESG Risk | Supports Bursa & US Equities",
        "step1": "📌 Step 1: Select Stock",
        "quick_tag": "🔥 Quick Select:",
        "input_label": "Custom Ticker (e.g., 1155.KL, NVDA):",
        "btn_analyze": "Run Quantitative Analysis 🔎",
        "step2": "⚙️ Step 2: Macro & Valuation Parameters (Defaults Recommended)",
        "param_g": "Terminal Growth Rate (g)",
        "param_erp": "Equity Risk Premium (ERP)",
        "esg_tag": "🌿 ESG Sector Risk Premium Auto-Adjust Enabled",
        "res_header": "📊 Core Valuation Dashboard",
        "price": "Current Market Price",
        "wacc": "WACC / Discount Rate",
        "fair_val": "Intrinsic Fair Value",
        "margin": "Safe Buy Target (20% Margin)",
        "lie_detector": "💡 Market Psychology (Lie Detector)",
        "ws_header": "🏛️ Wall Street Consensus",
        "chart_header": "📈 Advanced Price Action & Regression",
        "glossary_header": "📖 Beginner's Glossary & ESG Metrics"
    }
}

# ==============================================================================
# 3. 黄金防崩溃提取函数 (Safe Extract)
# ==============================================================================
def safe_extract_item(df, item_name, default=0.0):
    """Safely extracts financial data from messy yfinance dataframes."""
    if df is None or df.empty: return default
    try:
        for idx in df.index:
            if str(idx).strip().lower() == str(item_name).strip().lower():
                row = df.loc[idx]
                if hasattr(row, 'iloc') and len(row) > 0: val = row.iloc[0]
                elif hasattr(row, '__iter__') and len(row) > 0: val = list(row)[0]
                else: val = row
                if pd.notna(val): return float(val)
    except Exception: pass
    return default

# ==============================================================================
# 4. 核心量化引擎 (带 ESG 整合)
# ==============================================================================
class UniversalQuantEngine:
    def __init__(self, ticker):
        self.ticker = ticker.strip().upper()
        self.session = get_yf_session()
        self.stock = yf.Ticker(self.ticker, session=self.session)
        
        try:
            self.info = self.stock.info
            if not self.info or 'symbol' not in self.info:
                raise ValueError("Incomplete data received.")
        except Exception as e:
            st.error(f"⚠️ Yahoo Finance data is unavailable for this ticker. ({e})")
            st.stop() 

        self.name = self.info.get('longName', 'Unknown Company')
        self.sector = self.info.get('sector', 'Unknown')
        self.is_malaysia = self.ticker.endswith('.KL')

        self.price = self.info.get('currentPrice') or self.info.get('previousClose', 0)
        self.shares = self.info.get('sharesOutstanding', 1) or 1
        
        # 使用 safe_extract_item 深度防崩溃读取债务和现金
        self.bs = self.stock.balance_sheet
        self.cash = self.info.get('totalCash') or safe_extract_item(self.bs, 'Cash And Cash Equivalents') or 0
        self.debt = self.info.get('totalDebt') or safe_extract_item(self.bs, 'Total Debt') or 0
        self.scatter_data = None 

    def get_esg_adjustment(self):
        """🌟 FYP 核心功能：根据行业计算 ESG 风险溢价"""
        high_risk = ['Energy', 'Basic Materials', 'Industrials']
        low_risk = ['Technology', 'Healthcare', 'Financial Services']
        if self.sector in high_risk:
            self.esg_status = "⚠️ High Carbon/ESG Risk (Discount Rate Penalty +1.5%)"
            return 0.015
        elif self.sector in low_risk:
            self.esg_status = "🌱 Low ESG Risk (Discount Rate Reward -0.5%)"
            return -0.005
        self.esg_status = "⚖️ Neutral ESG Risk (No Adjustment)"
        return 0.00

    def compute_blume_beta(self):
        sector_defaults = {'Financial Services': 0.85, 'Real Estate': 0.60, 'Utilities': 0.65, 'Technology': 1.15, 'Industrials': 0.90}
        fallback_beta = sector_defaults.get(self.sector, 0.85)

        try:
            market_symbol = '^KLSE' if self.is_malaysia else '^GSPC'
            stock_hist = yf.Ticker(self.ticker, session=self.session).history(period='3y', interval='1mo')
            market_hist = yf.Ticker(market_symbol, session=self.session).history(period='3y', interval='1mo')
            
            if stock_hist.empty or market_hist.empty: return fallback_beta, 'Sector Fallback'
            
            stock_ret = stock_hist['Close'].pct_change().dropna()
            market_ret = market_hist['Close'].pct_change().dropna()
            aligned = pd.concat([stock_ret, market_ret], axis=1).dropna()
            
            if len(aligned) < 12: return fallback_beta, 'Sector Fallback'
            self.scatter_data = aligned 

            cov_matrix = np.cov(aligned.iloc[:, 0], aligned.iloc[:, 1])
            raw_beta = cov_matrix[0, 1] / np.var(aligned.iloc[:, 1], ddof=1)
            
            if not np.isfinite(raw_beta) or raw_beta <= 0.2 or raw_beta > 2.5: return fallback_beta, 'Sector Fallback'
            blume_beta = 0.67 * raw_beta + 0.33 * 1.0
            return round(max(0.3, min(blume_beta, 2.5)), 2), 'Blume Adjusted Regression'
        except Exception:
            return fallback_beta, 'Sector Fallback'

    def adaptive_model_setup(self, custom_erp, custom_g2):
        self.beta, self.beta_source = self.compute_blume_beta()
        self.rf = 0.038 if self.is_malaysia else 0.042
        
        # CAPM + ESG 整合
        self.base_ke = self.rf + (self.beta * custom_erp)
        self.esg_premium = self.get_esg_adjustment()
        self.cost_of_equity = self.base_ke + self.esg_premium
        self.tax_rate = 0.24 if self.is_malaysia else 0.21

        # WACC Calculation
        market_cap = self.price * self.shares
        total_cap = market_cap + self.debt
        w_e = market_cap / total_cap if total_cap > 0 else 1
        w_d = self.debt / total_cap if total_cap > 0 else 0
        interest_exp = abs(self.info.get('interestExpense', 0) or 0)
        cost_of_debt = min((interest_exp / self.debt) if self.debt > 0 else 0.05, 0.10)
        self.wacc = (w_e * self.cost_of_equity) + (w_d * cost_of_debt * (1 - self.tax_rate))

        self.stage1_years = 10 if self.sector in ['Technology', 'Communication Services'] else 5
        self.g2 = custom_g2

        # Model Selection (DCF vs DDM)
        raw_fcf = self.info.get('freeCashflow', 0) or 0
        if raw_fcf <= 0: raw_fcf = safe_extract_item(self.stock.cashflow, 'Free Cash Flow', 0.0)
        div_rate = self.info.get('dividendRate') or self.info.get('trailingAnnualDividendRate', 0)

        if self.sector in ['Financial Services', 'Real Estate', 'Utilities']:
            self.model_type = 'Dividend Discount Model (DDM)'
            self.discount_rate = self.cost_of_equity
            self.base_cf = div_rate if div_rate > 0 else raw_fcf
            self.is_per_share = True
        else:
            self.model_type = 'Discounted Cash Flow (DCF)'
            self.discount_rate = self.wacc
            self.base_cf = raw_fcf
            self.is_per_share = False

        eps_growth = self.info.get('earningsGrowth', 0) or 0
        self.g1 = min(max(eps_growth, 0.05), 0.25)

    def run_valuation_math(self, test_g1):
        if self.base_cf <= 0 or self.discount_rate <= self.g2: return 0
        pv_stage_1 = 0
        current_cf = self.base_cf
        for year in range(1, self.stage1_years + 1):
            current_cf *= 1 + test_g1
            pv_stage_1 += current_cf / ((1 + self.discount_rate) ** year)
        
        terminal_value = (current_cf * (1 + self.g2)) / (self.discount_rate - self.g2)
        pv_tv = terminal_value / ((1 + self.discount_rate) ** self.stage1_years)
        total_pv = pv_stage_1 + pv_tv

        if self.is_per_share: return total_pv
        else:
            equity_val = total_pv + self.cash - self.debt
            return equity_val / self.shares if self.shares > 0 else 0

    def find_implied_growth(self):
        if self.price <= 0 or self.base_cf <= 0: return None
        low, high = -0.50, 2.00
        for _ in range(50):
            mid = (low + high) / 2
            if self.run_valuation_math(mid) < self.price: low = mid
            else: high = mid
        return (low + high) / 2

# ==============================================================================
# Helper Functions (Charts)
# ==============================================================================
def draw_beta_scatter(engine):
    if engine.scatter_data is None: return None
    stock_ret, market_ret = engine.scatter_data.iloc[:, 0], engine.scatter_data.iloc[:, 1]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=market_ret, y=stock_ret, mode='markers', marker=dict(color='#6366f1', size=8), name='Monthly Returns'))
    x_range = np.linspace(market_ret.min(), market_ret.max(), 100)
    fig.add_trace(go.Scatter(x=x_range, y=engine.beta * x_range, mode='lines', line=dict(color='#ef4444', width=2), name='Regression Line'))
    fig.update_layout(xaxis_title="Market Return", yaxis_title="Stock Return", plot_bgcolor='rgba(0,0,0,0)', showlegend=False, height=280, margin=dict(l=0, r=0, t=10, b=0))
    return fig

def draw_candlestick(engine):
    hist = engine.stock.history(period="1y", interval="1d")
    if hist.empty or 'Close' not in hist.columns: return None
    fig = go.Figure(data=[go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'])])
    fig.update_layout(xaxis_rangeslider_visible=False, height=350, margin=dict(l=0, r=0, t=10, b=0), plot_bgcolor='rgba(0,0,0,0)')
    return fig

# ==============================================================================
# 5. 主程序与 UI 渲染 (Main App)
# ==============================================================================
def main():
    # 顶部双语切换器
    col_title, col_lang = st.columns([4, 1])
    with col_lang:
        selected_lang = st.selectbox("🌐 Language / 语言", ["中文", "English"])
        lang = "zh" if selected_lang == "中文" else "en"
        T = TEXTS[lang]
        
    with col_title:
        st.markdown(f"<h1 style='color: #1e3a8a;'>{T['title']}</h1>", unsafe_allow_html=True)
        st.caption(T['subtitle'])
    st.divider()

    # 快捷输入与选股
    if "ticker_input" not in st.session_state: st.session_state.ticker_input = "NVDA"
    def set_ticker(t): st.session_state.ticker_input = t

    st.write(T['step1'])
    q1, q2, q3, q4, q5 = st.columns(5)
    q1.button("🇺🇸 NVDA", on_click=set_ticker, args=("NVDA",), use_container_width=True)
    q2.button("🇺🇸 TSLA", on_click=set_ticker, args=("TSLA",), use_container_width=True)
    q3.button("🇺🇸 AAPL", on_click=set_ticker, args=("AAPL",), use_container_width=True)
    q4.button("🇲🇾 1155.KL (Maybank)", on_click=set_ticker, args=("1155.KL",), use_container_width=True)
    q5.button("🇲🇾 5347.KL (Tenaga)", on_click=set_ticker, args=("5347.KL",), use_container_width=True)

    col_search, col_btn = st.columns([4, 1])
    with col_search:
        ticker = st.text_input(T['input_label'], key="ticker_input")

    # 参数调节滑动条
    with st.expander(T['step2'], expanded=False):
        c_g, c_erp = st.columns(2)
        custom_g = c_g.slider(T['param_g'], 1.0, 3.5, 2.0, 0.1) / 100
        custom_erp = c_erp.slider(T['param_erp'], 4.0, 7.0, 5.0, 0.1) / 100
        st.caption(T['esg_tag'])

    if ticker:
        with st.spinner("Computing quantitative model & ESG factors..."):
            engine = UniversalQuantEngine(ticker)
            engine.adaptive_model_setup(custom_erp, custom_g)
            val = engine.run_valuation_math(engine.g1)
            implied_g = engine.find_implied_growth()

            # --- [1. 核心估值结果] ---
            st.markdown(f"### {T['res_header']}: {engine.name} ({engine.ticker})")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric(T['price'], f"{engine.price:.2f}")
            c2.metric(T['wacc'], f"{engine.discount_rate * 100:.2f}%", engine.esg_status)
            c3.metric(f"{T['fair_val']} ({engine.model_type.split(' ')[0]})", f"{val:.2f}")
            c4.metric(T['margin'], f"{(val * 0.80):.2f}")

            # --- [2. 市场测谎仪] ---
            st.markdown(f"### {T['lie_detector']}")
            if implied_g is not None:
                st.warning(f"To justify the current price of **{engine.price:.2f}**, the market expects a growth rate of **{implied_g * 100:.2f}% per year**.")
            else:
                st.warning("Unable to calculate implied growth (Negative Cashflows).")

            # --- [3. 华尔街预期对照组] ---
            if not engine.is_malaysia:
                target_mean = engine.info.get('targetMeanPrice')
                if target_mean:
                    st.markdown(f"### {T['ws_header']}")
                    st.info(f"**Analyst Consensus Target:** **${target_mean:.2f}** | Your Model: **${val:.2f}**")

            # --- [4. 动态图表] ---
            st.markdown(f"### {T['chart_header']}")
            with st.expander("📊 View Candlestick & Beta Scatter", expanded=True):
                c_chart1, c_chart2 = st.columns([1.2, 1])
                with c_chart1:
                    st.markdown("##### 🕯️ 1-Year Candlestick")
                    st.plotly_chart(draw_candlestick(engine), use_container_width=True)
                with c_chart2:
                    st.markdown("##### 🎯 3-Year Beta Regression")
                    st.plotly_chart(draw_beta_scatter(engine), use_container_width=True)

            # --- [5. 小白通俗金融词典 (附带 ESG 解释)] ---
            st.markdown("---")
            st.markdown(f"### {T['glossary_header']}")
            g1, g2, g3 = st.columns(3)
            with g1:
                st.info("**🎯 Beta (波动率)**\n\n>1 表示比大盘波动更剧烈，<1 表示走势防守抗跌。")
            with g2:
                st.info("**🛡️ WACC (加权折现率)**\n\n要求回报的及格线。高风险公司要求的回报更高，估值更低。")
            with g3:
                st.success("**🌿 ESG Risk Premium**\n\n高碳排放行业受法规风险影响，提升折现率作为惩罚；环保行业则享受折现率优待。")

if __name__ == '__main__':
    main()
