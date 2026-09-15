import datetime
import numpy as np
import pandas as pd
import requests
import yfinance as yf
import streamlit as st
import plotly.graph_objects as go

# ==============================================================================
# 1. Page Config & Terminal Layout
# ==============================================================================
st.set_page_config(page_title="Universal Quant Terminal V6.1", page_icon="💹", layout="wide")

@st.cache_resource
def get_yf_session():
    """Persistent session for stability."""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    })
    return session

# ==============================================================================
# 2. ORIGINAL LOGIC: Robust Financial Extractor (Anti-Plagiarism)
# ==============================================================================
def get_fin_metric(df, keyword, default=0.0):
    """Uses Pandas string matching to safely find financial metrics."""
    if df is None or df.empty: return default
    try:
        matches = df[df.index.str.contains(keyword, case=False, na=False)]
        if not matches.empty:
            val = matches.iloc[0, 0]
            return float(val) if pd.notna(val) else default
    except Exception:
        pass
    return default

# ==============================================================================
# 3. Core Valuation Engine (With ESG Integration)
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
            st.error(f"⚠️ Yahoo Finance data unavailable for {self.ticker}. Please try another stock.")
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
        if self.sector in ['Energy', 'Basic Materials', 'Industrials']: return 0.015, "🔴 High ESG Risk (Penalty +1.5%)"
        elif self.sector in ['Technology', 'Healthcare', 'Financial Services']: return -0.005, "🟢 Low ESG Risk (Reward -0.5%)"
        return 0.00, "⚪ Neutral ESG Risk (No Adj)"

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
# 4. Advanced Visualization
# ==============================================================================
def draw_pro_candlestick(ticker, session):
    hist = yf.Ticker(ticker, session=session).history(period="1y", interval="1d")
    if hist.empty: return None
    hist['MA20'] = hist['Close'].rolling(window=20).mean()
    hist['MA50'] = hist['Close'].rolling(window=50).mean()

    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], name='Price'))
    fig.add_trace(go.Scatter(x=hist.index, y=hist['MA20'], line=dict(color='orange', width=1.5), name='20-Day SMA'))
    fig.add_trace(go.Scatter(x=hist.index, y=hist['MA50'], line=dict(color='blue', width=1.5), name='50-Day SMA'))
    fig.update_layout(xaxis_rangeslider_visible=False, height=400, margin=dict(l=0, r=0, t=10, b=0), plot_bgcolor='rgba(0,0,0,0)', legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01))
    return fig

# ==============================================================================
# 5. UI Architecture: The Bloomberg-Style Dashboard
# ==============================================================================
def main():
    # --- SIDEBAR (Control Panel) ---
    st.sidebar.markdown("## ⚙️ Terminal Controls")
    
    st.sidebar.markdown("**1. Ticker Selection**")
    quick_tickers = {"NVIDIA": "NVDA", "Apple": "AAPL", "Tesla": "TSLA", "Maybank": "1155.KL", "Public Bank": "1295.KL", "Tenaga Nasional": "5347.KL"}
    sel_name = st.sidebar.selectbox("Quick Load", list(quick_tickers.keys()))
    
    ticker_input = st.sidebar.text_input("Or type custom ticker:", quick_tickers[sel_name])
    
    st.sidebar.markdown("**2. Macro Assumptions**")
    custom_erp = st.sidebar.slider("Market Risk Premium (ERP)", 4.0, 7.0, 5.0, 0.1) / 100
    custom_g2 = st.sidebar.slider("Terminal Growth (g)", 1.0, 3.5, 2.0, 0.1) / 100

    st.sidebar.info("💡 **Academic Note:**\nThis terminal integrates standard CAPM with **ESG Risk Premiums** for sustainable finance evaluation.")

    # --- MAIN DASHBOARD ---
    st.title("🌐 Universal Quant Terminal V6.1")
    
    if ticker_input:
        with st.spinner(f"Connecting to data pipelines for {ticker_input.upper()}..."):
            engine = UniversalQuantEngine(ticker_input)
            val, implied_g = engine.run_valuation(custom_erp, custom_g2)

            st.markdown(f"**{engine.name} ({engine.ticker})** | 🏢 Sector: `{engine.sector}` | 💰 Market Cap: `${(engine.price * engine.shares):,.0f}`")
            st.divider()

            # The Tabs Architecture
            tab_val, tab_esg, tab_chart = st.tabs(["🎯 Core Valuation Dashboard", "🌿 ESG & Cost of Capital", "📈 Pro Price Action"])

            # ---------------------------------------------------------
            # TAB 1: CORE VALUATION (Restored UI Masterpieces)
            # ---------------------------------------------------------
            with tab_val:
                # 1. Re-added WACC to the top metrics clearly
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Current Market Price", f"{engine.price:.2f}")
                c2.metric("WACC / Discount Rate", f"{engine.r*100:.2f}%")
                c3.metric(f"Intrinsic Value ({engine.model_name.split(' ')[0]})", f"{val:.2f}")
                c4.metric("Safe Buy (20% MoS)", f"{(val * 0.8):.2f}")

                st.markdown("---")

                # 2. Re-added MARKET PSYCHOLOGY (LIE DETECTOR)
                st.markdown("### 💡 MARKET PSYCHOLOGY (LIE DETECTOR)")
                implied_g_str = f"{implied_g * 100:.2f}%" if implied_g is not None else "N/A"
                st.warning(f"To justify the current price of **{engine.price:.2f}**, the market implies a Stage 1 Growth Rate of **{implied_g_str} per year for {engine.horizon} years**.")
                
                if implied_g is not None:
                    if implied_g > 0.40: st.write("-> **Diagnosis: EXTREME HYPE (Bubble Territory).** The market expects miraculous growth.")
                    elif implied_g < 0.0: st.write("-> **Diagnosis: EXTREME PESSIMISM.** The market expects shrinking cash flows.")
                    else: st.write("-> **Diagnosis: MODERATE EXPECTATIONS.** Balanced market sentiment.")

                # 3. Re-added DUAL-PERSPECTIVE AI ADVISORY
                st.markdown("### 🤖 DUAL-PERSPECTIVE AI ADVISORY")
                div_rate = engine.info.get('dividendRate') or engine.info.get('trailingAnnualDividendRate') or 0
                div_yield = (div_rate / engine.price) * 100 if engine.price > 0 else 0

                col_a, col_b = st.columns(2)
                with col_a:
                    with st.container(border=True):
                        st.markdown("🔸 **Perspective A: Conservative Income**")
                        st.write(f"- Current Dividend Yield: {div_yield:.2f}% | Beta Risk: {engine.beta:.2f}")
                        if engine.sector in ['Financial Services', 'Utilities', 'Real Estate'] and div_yield > 3.0:
                            st.success("-> **Verdict:** 🟢 SUITABLE FOR INCOME. Strong cash-flow profile.")
                        else:
                            st.error("-> **Verdict:** 🔴 NOT IDEAL FOR INCOME. Low dividend yield.")
                with col_b:
                    with st.container(border=True):
                        st.markdown("🔹 **Perspective B: Capital Appreciation**")
                        st.write(f"- Market Implied Growth: {implied_g_str} | Model Valuation: {val:.2f}")
                        if implied_g is not None and implied_g < 0.0 and engine.price < val:
                            st.success("-> **Verdict:** 🟢 MULTI-BAGGER POTENTIAL. Deep value mispricing.")
                        elif implied_g is not None and implied_g > 0.40:
                            st.error("-> **Verdict:** 🔴 HIGH SPECULATION RISK. Priced for perfection.")
                        else:
                            st.info("-> **Verdict:** 🟢 / 🟡 FAIRLY PRICED or Growth Opportunity.")

                # 4. Final Executive Rating
                st.markdown("### 🎯 FINAL EXECUTIVE SUMMARY & RATING")
                if val > 0 and engine.price > 0:
                    price_to_val = engine.price / val
                    if price_to_val <= 0.70 and (implied_g is not None and implied_g < 0.0): rating, reason = '🟢 STRONG BUY', 'Extreme pessimism creates massive margin of safety.'
                    elif price_to_val <= 0.85: rating, reason = '🟢 BUY', 'Solid value mispricing. Meets the 20% margin of safety requirement.'
                    elif 0.85 < price_to_val <= 1.15: rating, reason = '🟡 HOLD', 'Fairly valued. Current market price aligns with intrinsic value.'
                    elif 1.15 < price_to_val <= 1.40: rating, reason = '🔴 SELL', 'Overvalued. Market price exceeds the intrinsic valuation.'
                    else: rating, reason = '🔴 STRONG SELL', 'Severe bubble risk. Implied growth is priced for perfection.'
                    
                    with st.container(border=True):
                        st.markdown(f"- **Final Investment Rating : {rating}**")
                        st.markdown(f"- **Core Justification : {reason}**")

                # Wall Street Integration Check
                if not engine.is_malaysia and engine.info.get('targetMeanPrice'):
                    ws_tgt = engine.info.get('targetMeanPrice')
                    st.markdown("---")
                    st.info(f"🏛️ **Wall Street Analyst Consensus Target:** **${ws_tgt:.2f}** | Your Model: **${val:.2f}**")

            # ---------------------------------------------------------
            # TAB 2: ESG & MACRO
            # ---------------------------------------------------------
            with tab_esg:
                st.markdown("### Cost of Capital Breakdown (CAPM)")
                e1, e2, e3, e4 = st.columns(4)
                e1.metric("Risk-Free Rate", f"{engine.rf*100:.2f}%")
                e2.metric("Beta Risk", f"{engine.beta:.2f}", engine.beta_type)
                e3.metric("ESG Premium Adjustment", f"{engine.esg_adj*100:+.2f}%")
                e4.metric("Final Discount Rate (WACC)", f"{engine.wacc*100:.2f}%")
                
                st.info(f"**ESG Sector Diagnosis:** {engine.esg_tag}")
                st.caption("*Note: High ESG risk sectors face a higher cost of capital, mathematically lowering their intrinsic valuation.*")

            # ---------------------------------------------------------
            # TAB 3: PRO CHARTS
            # ---------------------------------------------------------
            with tab_chart:
                c_chart, c_beta = st.columns([1.5, 1])
                with c_chart:
                    st.markdown("**1Y Price Action with Simple Moving Averages**")
                    k_fig = draw_pro_candlestick(engine.ticker, engine.session)
                    if k_fig: st.plotly_chart(k_fig, use_container_width=True)
                with c_beta:
                    st.markdown("**3Y Volatility Regression (Beta)**")
                    st.info(f"The stock moves **{engine.beta}x** relative to the benchmark index.")
                    st.caption("A Beta > 1 implies higher volatility (aggression), while < 1 implies defensive characteristics.")

if __name__ == '__main__':
    main()
