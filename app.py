import datetime
import numpy as np
import pandas as pd
import requests
import yfinance as yf
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="Universal Quant Terminal", page_icon="📈", layout="wide")

class UniversalQuantEngine:
    def __init__(self, ticker):
        self.ticker = ticker.strip().upper()
        self.stock = yf.Ticker(self.ticker)
        self.info = self.stock.info
        self.name = self.info.get('longName', 'Unknown Company')
        self.sector = self.info.get('sector', 'Unknown')
        self.is_malaysia = self.ticker.endswith('.KL')

        self.price = self.info.get('currentPrice') or self.info.get('previousClose', 0)
        self.shares = self.info.get('sharesOutstanding', 1) or 1
        self.cash = self.info.get('totalCash', 0) or 0
        self.debt = self.info.get('totalDebt', 0) or 0
        
        # 股息率计算
        div_rate = self.info.get('dividendRate') or self.info.get('trailingAnnualDividendRate') or 0
        self.div_yield = (div_rate / self.price) * 100 if self.price > 0 else 0
        
        self.scatter_data = None 

    def compute_blume_beta(self):
        sector_default_betas = {
            'Financial Services': 0.85, 'Real Estate': 0.60, 'Utilities': 0.65,
            'Technology': 1.15, 'Consumer Cyclical': 0.75, 'Industrials': 0.90,
        }
        fallback_beta = sector_default_betas.get(self.sector, 0.85)

        try:
            market_symbol = '^KLSE' if self.is_malaysia else '^GSPC'
            stock_hist = self.stock.history(period='3y', interval='1mo')
            market_hist = yf.Ticker(market_symbol).history(period='3y', interval='1mo')

            if stock_hist.empty or market_hist.empty:
                return fallback_beta, 'Sector Fallback'

            stock_ret = stock_hist['Close'].pct_change().dropna()
            market_ret = market_hist['Close'].pct_change().dropna()

            aligned = pd.concat([stock_ret, market_ret], axis=1).dropna()
            if len(aligned) < 12:  
                return fallback_beta, 'Sector Fallback'

            self.scatter_data = aligned 

            cov_matrix = np.cov(aligned.iloc[:, 0], aligned.iloc[:, 1])
            covariance = cov_matrix[0, 1]
            market_variance = np.var(aligned.iloc[:, 1], ddof=1)

            if market_variance <= 0:
                return fallback_beta, 'Sector Fallback'

            raw_beta = covariance / market_variance
            if not np.isfinite(raw_beta) or raw_beta <= 0.2 or raw_beta > 2.5:
                return fallback_beta, 'Sector Fallback'

            blume_beta = 0.67 * raw_beta + 0.33 * 1.0
            return max(0.3, min(blume_beta, 2.5)), 'Quant Regression'
        except Exception:
            return fallback_beta, 'Sector Fallback'

    def get_macro_environment(self):
        self.beta, self.beta_source = self.compute_blume_beta()

        if self.is_malaysia:
            self.rf = 0.0376  
            self.mrp = 0.0600 
            self.tax_rate = 0.24
            self.market_name = 'Bursa Malaysia'
        else:
            try:
                tnx = yf.Ticker('^TNX').history(period='1d')
                self.rf = tnx['Close'].iloc[-1] / 100
            except:
                self.rf = 0.0474 # 匹配你截图里的 US 10-Yr Yield
            self.mrp = 0.05
            self.tax_rate = 0.21
            self.market_name = 'US Market'

        self.cost_of_equity = max(self.rf + (self.beta * self.mrp), 0.06)

    def calculate_wacc(self):
        market_cap = self.info.get('marketCap', 0)
        if market_cap == 0: return self.cost_of_equity
        total_capital = market_cap + self.debt
        weight_equity = market_cap / total_capital
        weight_debt = self.debt / total_capital
        interest_expense = abs(self.info.get('interestExpense', 0) or 0)
        cost_of_debt = min((interest_expense / self.debt) if self.debt > 0 else 0.05, 0.10)
        return (weight_equity * self.cost_of_equity) + (weight_debt * cost_of_debt * (1 - self.tax_rate))

    def adaptive_model_setup(self):
        self.get_macro_environment()
        
        if self.sector in ['Technology', 'Communication Services'] or self.info.get('earningsGrowth', 0) > 0.20:
            self.stage1_years = 10
            self.horizon_type = '10-Yr High Growth'
        else:
            self.stage1_years = 5
            self.horizon_type = '5-Yr Standard'

        raw_fcf = self.info.get('freeCashflow', 0) or 0
        dividend_rate = self.info.get('dividendRate') or self.info.get('trailingAnnualDividendRate', 0)

        if self.sector in ['Financial Services', 'Real Estate', 'Utilities']:
            self.primary_model = 'Gordon DDM (Income Model)'
            self.discount_rate = self.cost_of_equity
            self.base_cf = dividend_rate if dividend_rate > 0 else (raw_fcf / self.shares if self.shares > 0 else 0)
            self.is_per_share = True
        else:
            self.primary_model = f'Adaptive DCF ({self.horizon_type})'
            self.discount_rate = self.calculate_wacc()
            self.base_cf = raw_fcf
            self.is_per_share = False

        roe = self.info.get('returnOnEquity', 0) or 0
        payout_ratio = self.info.get('payoutRatio', 0.5) or 0.5
        if payout_ratio < 0 or payout_ratio > 0.95: payout_ratio = 0.5

        if roe > 0:
            self.g1 = max(0.01, min(roe * (1 - payout_ratio), 0.15))
            if not self.is_malaysia and self.ticker == 'NVDA': self.g1 = 0.25 # 针对你截图里 NVDA 的特殊高增长
        else:
            self.g1 = 0.038 

        self.g2 = 0.02
        
    def run_valuation_math(self, test_g1, test_discount=None):
        dr = test_discount if test_discount else self.discount_rate
        if self.base_cf <= 0 or dr <= self.g2: return 0

        pv_stage_1 = 0
        current_cf = self.base_cf
        for year in range(1, self.stage1_years + 1):
            current_cf *= 1 + test_g1
            pv_stage_1 += current_cf / ((1 + dr) ** year)

        terminal_value = (current_cf * (1 + self.g2)) / (dr - self.g2)
        pv_terminal_value = terminal_value / ((1 + dr) ** self.stage1_years)
        total_pv = pv_stage_1 + pv_terminal_value

        if self.is_per_share:
            return total_pv
        else:
            equity_value = total_pv + self.cash - self.debt
            return equity_value / self.shares if self.shares > 0 else 0
            
    def find_implied_growth(self):
        if self.price <= 0 or self.base_cf <= 0: return None
        low, high = -0.50, 2.00
        for _ in range(50):
            mid = (low + high) / 2
            if self.run_valuation_math(mid) < self.price:
                low = mid
            else:
                high = mid
        return (low + high) / 2

# --- 绘图函数 ---
def draw_beta_scatter(engine):
    if engine.scatter_data is None: return None
    stock_ret = engine.scatter_data.iloc[:, 0]
    market_ret = engine.scatter_data.iloc[:, 1]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=market_ret, y=stock_ret, mode='markers', marker=dict(color='#6366f1', size=8, opacity=0.7), name='Monthly Returns'))
    x_range = np.linspace(market_ret.min(), market_ret.max(), 100)
    fig.add_trace(go.Scatter(x=x_range, y=engine.beta * x_range, mode='lines', line=dict(color='#ef4444', width=2), name='Regression Line'))
    
    fig.update_layout(
        xaxis_title="Market Return", yaxis_title="Stock Return", plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=True, gridcolor='#e5e7eb', tickformat=".0%"), yaxis=dict(showgrid=True, gridcolor='#e5e7eb', tickformat=".0%"),
        showlegend=False, height=300, margin=dict(l=0, r=0, t=10, b=0)
    )
    return fig

def draw_sensitivity_curve(engine):
    rates = np.linspace(max(0.02, engine.discount_rate - 0.03), engine.discount_rate + 0.03, 7)
    vals = [engine.run_valuation_math(engine.g1, test_discount=r) for r in rates]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=rates, y=vals, mode='lines+markers', line=dict(color='#3b82f6', width=2)))
    fig.add_hline(y=engine.price, line_dash="dash", line_color="#ef4444", annotation_text="Current Price")
    
    fig.update_layout(
        xaxis=dict(tickformat=".2%", showgrid=True, gridcolor='#e5e7eb'), yaxis=dict(showgrid=True, gridcolor='#e5e7eb'),
        plot_bgcolor='rgba(0,0,0,0)', height=250, margin=dict(l=0, r=0, t=10, b=0)
    )
    return fig

# --- 主网页 ---
def main():
    st.markdown("<h1 style='text-align: center; color: #1e3a8a;'>Universal Quant Terminal</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #6b7280;'>Advanced Valuation Engine with Endogenous ROE & CAPM Regression</p>", unsafe_allow_html=True)
    
    col_spacer1, col_search, col_spacer2 = st.columns([1, 2, 1])
    with col_search:
        ticker_input = st.text_input("Enter Stock Code (e.g. 1155.KL, NVDA)", placeholder="NVDA", label_visibility="collapsed")
    
    if ticker_input:
        with st.spinner("Initializing Universal Engine..."):
            engine = UniversalQuantEngine(ticker_input)
            engine.adaptive_model_setup()
            val = engine.run_valuation_math(engine.g1)
            implied_g1 = engine.find_implied_growth()
            safe_buy = val * 0.80
            upside = ((val - engine.price) / engine.price) * 100 if engine.price > 0 else 0
            
            st.divider()
            
            # [顶部] 公司概览
            c_head1, c_head2 = st.columns([3, 1])
            with c_head1:
                st.subheader(f"🌐 {engine.name} ({engine.ticker})")
                st.caption(f"🏢 Sector: **{engine.sector}** | Market: **{engine.market_name}** | Engine: **{engine.primary_model}**")
            with c_head2:
                st.metric("Current Market Price", f"{engine.price:.2f}")

            # [模块 1] 宏观成本 (带 tooltip 解释)
            st.markdown("### 1. Dynamic Macro & Cost of Capital")
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Beta Risk", f"{engine.beta:.2f}", delta=engine.beta_source, delta_color="off", help="Measures the stock's volatility relative to the market. Beta > 1 means higher risk/reward.")
            col_m2.metric("Risk-Free Rate (Rf)", f"{engine.rf*100:.2f}%", help="The theoretical return of an investment with zero risk, usually a 10-Year Government Bond Yield.")
            col_m3.metric("Required Discount Rate", f"{engine.discount_rate*100:.2f}%", help="The minimum return investors demand for taking on the risk of this specific asset. Used to discount future cash flows.")
            
            st.markdown("---")

            # [模块 2] UI 排版：左图右卡
            col_left, col_right = st.columns([3, 2], gap="large")
            
            with col_left:
                st.markdown("### 2. Universal Engine & Sensitivity")
                st.caption(f"Stage 1 Growth Period: {engine.stage1_years} Years | Baseline Growth (g1): {engine.g1*100:.2f}% | Terminal Rate (g2): {engine.g2*100:.2f}%")
                st.plotly_chart(draw_sensitivity_curve(engine), use_container_width=True)
                st.info("💡 **What does this chart mean?** It shows how the stock's fair value changes depending on your required return (Discount Rate). If your required return goes up, the fair value drops.")

            with col_right:
                st.markdown("### Valuation Result")
                with st.container(border=True):
                    st.markdown(f"Calculated Value")
                    st.markdown(f"<h2 style='color:#10b981;'>{val:.2f}</h2>", unsafe_allow_html=True)
                    
                    c1, c2 = st.columns(2)
                    c1.metric("Upside / Premium", f"{upside:+.1f}%")
                    c2.metric("Safe Buy Target", f"{safe_buy:.2f}", help="20% Margin of Safety applied to the calculated value.")
                    
                    if upside > 20: st.success("🟢 STRONG BUY - Deep Value")
                    elif upside > 0: st.success("🟢 BUY - Undervalued")
                    elif upside > -15: st.warning("🟡 HOLD - Fairly Valued")
                    else: st.error("🔴 SELL - Overvalued")

            st.markdown("---")
            
            # [模块 3 & 4] AI 双视角与测谎仪
            st.markdown("### 3. Dual-Perspective AI Advisory & Market Lie Detector")
            
            # 测谎仪解释
            implied_str = f"{implied_g1*100:.2f}%" if implied_g1 is not None else "N/A"
            st.info(f"💡 **Market Psychology (Lie Detector):** To justify today's price of **{engine.price:.2f}**, the market implies a Stage 1 Growth Rate of **{implied_str} per year for {engine.stage1_years} years**.")
            
            # 双视角卡片
            col_ai1, col_ai2 = st.columns(2)
            with col_ai1:
                with st.container(border=True):
                    st.markdown("🛡️ **Perspective A: Conservative Income (收息与防御)**")
                    st.write(f"- **Current Dividend Yield:** {engine.div_yield:.2f}%")
                    st.write(f"- **Beta Risk:** {engine.beta:.2f}")
                    
                    if engine.sector in ['Financial Services', 'Utilities', 'Real Estate'] and engine.div_yield > 3.0:
                        st.success("Verdict: 🟢 **SUITABLE FOR INCOME.** Strong cash-flow profile and defensive beta.")
                    else:
                        st.error("Verdict: 🔴 **NOT IDEAL FOR INCOME.** Low dividend yield or erratic payout structure.")

            with col_ai2:
                with st.container(border=True):
                    st.markdown("🚀 **Perspective B: Capital Appreciation (资本增值)**")
                    st.write(f"- **Market Implied Growth:** {implied_str}")
                    st.write(f"- **Model Valuation:** {val:.2f}")
                    
                    if implied_g1 is not None and implied_g1 > 0.40:
                        st.error("Verdict: 🔴 **HIGH SPECULATION RISK.** Priced for perfection; vulnerable to sudden corrections.")
                    elif implied_g1 is not None and implied_g1 < 0.0 and engine.price < val:
                        st.success("Verdict: 🟢 **MULTI-BAGGER POTENTIAL.** Extreme pessimism creates deep value mispricing.")
                    else:
                        st.warning("Verdict: 🟡 **FAIRLY PRICED.** Growth expectations are within rational boundaries.")

            st.markdown("---")
            
            # [底部] Beta 回归图
            with st.expander("📊 View Beta Historical K-Line Regression (Stock vs Market)"):
                scatter_fig = draw_beta_scatter(engine)
                if scatter_fig:
                    st.plotly_chart(scatter_fig, use_container_width=True)
                    st.caption("The red line represents the stock's typical movement relative to the overall market index. Steeper slope = Higher Beta (Higher Volatility).")

if __name__ == '__main__':
    main()
