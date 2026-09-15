import datetime
import numpy as np
import pandas as pd
import requests
import yfinance as yf
import streamlit as st
import plotly.graph_objects as go

# ==============================================================================
# 1. 页面配置与反爬虫伪装
# ==============================================================================
st.set_page_config(page_title="Universal Quant V7.0", page_icon="💹", layout="wide")

@st.cache_resource
def get_yf_session():
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
    return session

def get_fin_metric(df, keyword, default=0.0):
    if df is None or df.empty: return default
    try:
        matches = df[df.index.str.contains(keyword, case=False, na=False)]
        if not matches.empty:
            val = matches.iloc[0, 0]
            return float(val) if pd.notna(val) else default
    except Exception: pass
    return default

# ==============================================================================
# 2. 核心量化引擎 (保留你的独家护城河)
# ==============================================================================
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
        if self.sector in ['Energy', 'Basic Materials', 'Industrials']: return 0.015, "🔴 High Carbon Risk (+1.5% Penalty)"
        elif self.sector in ['Technology', 'Healthcare', 'Financial Services']: return -0.005, "🟢 Sustainable/Green (-0.5% Reward)"
        return 0.00, "⚪ Neutral ESG Risk"

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
# 3. 高级可视化图表
# ==============================================================================
def draw_pro_candlestick(ticker, session):
    hist = yf.Ticker(ticker, session=session).history(period="1y", interval="1d")
    if hist.empty: return None
    hist['MA20'] = hist['Close'].rolling(window=20).mean()
    hist['MA50'] = hist['Close'].rolling(window=50).mean()

    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], name='Price'))
    fig.add_trace(go.Scatter(x=hist.index, y=hist['MA20'], line=dict(color='#f59e0b', width=1.5), name='20-Day SMA'))
    fig.add_trace(go.Scatter(x=hist.index, y=hist['MA50'], line=dict(color='#3b82f6', width=1.5), name='50-Day SMA'))
    fig.update_layout(xaxis_rangeslider_visible=False, height=350, margin=dict(l=0, r=0, t=10, b=0), plot_bgcolor='rgba(0,0,0,0)', legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01))
    return fig

def draw_beta_scatter(engine):
    if engine.scatter_data is None: return None
    stock_ret, market_ret = engine.scatter_data.iloc[:, 0], engine.scatter_data.iloc[:, 1]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=market_ret, y=stock_ret, mode='markers', marker=dict(color='#6366f1', size=7, opacity=0.8), name='Returns'))
    x_range = np.linspace(market_ret.min(), market_ret.max(), 100)
    fig.add_trace(go.Scatter(x=x_range, y=engine.beta * x_range, mode='lines', line=dict(color='#ef4444', width=2), name='Beta Regression'))
    fig.update_layout(xaxis_title="Market Benchmark", yaxis_title="Stock Return", plot_bgcolor='rgba(0,0,0,0)', showlegend=False, height=350, margin=dict(l=0, r=0, t=10, b=0))
    return fig

# ==============================================================================
# 4. 极致 UI 排版 (Dashboard Architecture)
# ==============================================================================
def main():
    st.markdown("<h1 style='color: #0f172a; font-weight: 800; font-size: 2.2rem;'>🌐 Universal Quant Terminal</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #64748b; margin-top: -10px;'>Institutional-Grade Valuation Dashboard with ESG & Market Psychology Integration</p>", unsafe_allow_html=True)
    
    # 模块 A：顶置控制台 (Command Center)
    with st.container(border=True):
        st.markdown("#### 🎛️ Input & Assumptions")
        col_in1, col_in2, col_in3 = st.columns([2, 1, 1])
        
        with col_in1:
            if "ticker_input" not in st.session_state: st.session_state.ticker_input = "NVDA"
            def set_ticker(t): st.session_state.ticker_input = t
            
            # 完美的快捷键药丸 (Pills)
            st.write("🔥 **Quick Load:**")
            q1, q2, q3, q4 = st.columns(4)
            q1.button("🇺🇸 NVDA", on_click=set_ticker, args=("NVDA",), use_container_width=True)
            q2.button("🇺🇸 AAPL", on_click=set_ticker, args=("AAPL",), use_container_width=True)
            q3.button("🇲🇾 MAYBANK", on_click=set_ticker, args=("1155.KL",), use_container_width=True)
            q4.button("🇲🇾 TENAGA", on_click=set_ticker, args=("5347.KL",), use_container_width=True)
            
            ticker_input = st.text_input("Custom Ticker:", key="ticker_input")
            
        with col_in2:
            custom_erp = st.slider("Equity Risk Premium", 4.0, 7.0, 5.0, 0.1, help="Expected return of stock market over risk-free rate.") / 100
        with col_in3:
            custom_g2 = st.slider("Terminal Growth (g)", 1.0, 3.5, 2.0, 0.1, help="Perpetual economic growth rate.") / 100

    if ticker_input:
        with st.spinner(f"Initiating Quantum Analysis for {ticker_input.upper()}..."):
            engine = UniversalQuantEngine(ticker_input)
            val, implied_g = engine.run_valuation(custom_erp, custom_g2)

            st.markdown(f"### 🏢 **{engine.name} ({engine.ticker})** | `{engine.sector}`")
            st.divider()

            # 模块 B：终极估值结论大卡片 (The Verdict)
            if val > 0 and engine.price > 0:
                diff_pct = (val - engine.price) / engine.price * 100
                if diff_pct > 15 and (implied_g is not None and implied_g < 0.05):
                    verdict_color, verdict_text = "#10b981", "🟢 UNDERVALUED (Deep Margin of Safety)"
                elif diff_pct < -15:
                    verdict_color, verdict_text = "#ef4444", "🔴 OVERVALUED (Premium Pricing)"
                else:
                    verdict_color, verdict_text = "#f59e0b", "🟡 FAIRLY VALUED (Rational Pricing)"
            else:
                verdict_color, verdict_text = "#64748b", "⚪ INSUFFICIENT DATA"

            # 顶级 HTML 卡片设计 (完全秒杀你朋友的简单文本)
            st.markdown(f"""
                <div style="background-color: {verdict_color}15; border: 2px solid {verdict_color}; border-radius: 12px; padding: 20px; text-align: center; margin-bottom: 20px;">
                    <h2 style="color: {verdict_color}; margin: 0; font-weight: 800;">{verdict_text}</h2>
                    <p style="color: #475569; margin-top: 5px; font-size: 1.1rem;">Intrinsic Value: <b>${val:.2f}</b> &nbsp;|&nbsp; Current Price: <b>${engine.price:.2f}</b></p>
                </div>
            """, unsafe_allow_html=True)

            # 模块 C：矩阵看板 (Matrix Board)
            col_m1, col_m2 = st.columns(2)
            
            # 左侧：你的核心武器 (Lie Detector + Dual Engine)
            with col_m1:
                with st.container(border=True):
                    st.markdown("#### 🧠 Market Psychology & ESG")
                    implied_g_str = f"{implied_g * 100:.2f}%" if implied_g is not None else "N/A"
                    st.metric("Market Implied Growth Rate", implied_g_str)
                    
                    if implied_g is not None:
                        if implied_g > 0.40: st.error("⚠️ **Bubble Alert:** Market is pricing in extreme, unrealistic growth.")
                        elif implied_g < 0.0: st.success("🔥 **Deep Value:** Market expects cash flows to shrink. High safety margin.")
                        else: st.info("⚖️ **Balanced:** Market sentiment aligns with rational growth expectations.")
                    
                    st.markdown("---")
                    st.markdown(f"**ESG Diagnosis:** {engine.esg_tag}")

            # 右侧：你朋友的 Wall Street 参考 (被你完美吸收)
            with col_m2:
                with st.container(border=True):
                    st.markdown("#### 🏛️ Capital & Institutional Consensus")
                    st.metric("Discount Rate (WACC / Ke)", f"{engine.r*100:.2f}%", f"Beta: {engine.beta:.2f}", delta_color="off")
                    
                    if not engine.is_malaysia and engine.info.get('targetMeanPrice'):
                        ws_tgt = engine.info.get('targetMeanPrice')
                        st.markdown("---")
                        st.metric("Wall Street Target", f"${ws_tgt:.2f}", f"{(ws_tgt - engine.price)/engine.price*100:+.1f}% vs Price")
                    else:
                        st.markdown("---")
                        st.write("*(Wall Street target data unavailable for this equity)*")

            # 模块 D：高级技术图表并排 (比你朋友的上下排版更紧凑高级)
            st.markdown("### 📈 Pro Charting & Regression")
            chart_col1, chart_col2 = st.columns(2)
            with chart_col1:
                with st.container(border=True):
                    st.markdown("**1-Year Price Action (MA20 & MA50)**")
                    st.plotly_chart(draw_pro_candlestick(engine.ticker, engine.session), use_container_width=True)
            with chart_col2:
                with st.container(border=True):
                    st.markdown(f"**3-Year Beta Regression (β = {engine.beta:.2f})**")
                    st.plotly_chart(draw_beta_scatter(engine), use_container_width=True)

            # 模块 E：小白通俗金融词典 (Institution Glossary - 防抄袭重构版)
            st.markdown("### 📖 Institutional Analyst Glossary")
            g1, g2, g3, g4 = st.columns(4)
            with g1:
                with st.container(border=True):
                    st.markdown("##### 🎯 Beta")
                    st.caption("Volatility index. >1 means aggressive stock, <1 means defensive. Adjusted via Blume's technique.")
            with g2:
                with st.container(border=True):
                    st.markdown("##### 🛡️ WACC")
                    st.caption("The Weighted Average Cost of Capital. Serves as the ultimate hurdle rate for corporate valuation.")
            with g3:
                with st.container(border=True):
                    st.markdown("##### 🌿 ESG Premium")
                    st.caption("Discount rate penalty/reward based on the sector's environmental and regulatory risk profile.")
            with g4:
                with st.container(border=True):
                    st.markdown("##### 🕵️ Implied Growth")
                    st.caption("Reverse-engineered growth rate priced into the *current* market value. Acts as a lie detector.")

if __name__ == '__main__':
    main()
