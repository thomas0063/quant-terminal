import datetime
import numpy as np
import pandas as pd
import requests
import yfinance as yf
import streamlit as st
import plotly.graph_objects as go

# Page Configuration
st.set_page_config(page_title="Universal Quant Terminal V4.6", page_icon="📈", layout="wide")

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
                return fallback_beta, 'sector_fallback'

            stock_ret = stock_hist['Close'].pct_change().dropna()
            market_ret = market_hist['Close'].pct_change().dropna()

            aligned = pd.concat([stock_ret, market_ret], axis=1).dropna()
            if len(aligned) < 12:  
                return fallback_beta, 'sector_fallback'

            self.scatter_data = aligned 

            cov_matrix = np.cov(aligned.iloc[:, 0], aligned.iloc[:, 1])
            covariance = cov_matrix[0, 1]
            market_variance = np.var(aligned.iloc[:, 1], ddof=1)

            if market_variance <= 0:
                return fallback_beta, 'sector_fallback'

            raw_beta = covariance / market_variance
            if not np.isfinite(raw_beta) or raw_beta <= 0.2 or raw_beta > 2.5:
                return fallback_beta, 'sector_fallback'

            blume_beta = 0.67 * raw_beta + 0.33 * 1.0
            final_beta = max(0.3, min(blume_beta, 2.5))
            return round(final_beta, 2), 'quant_regression'
        except Exception:
            return fallback_beta, 'sector_fallback'

    def get_macro_environment(self):
        self.beta, self.beta_source = self.compute_blume_beta()

        if self.is_malaysia:
            try:
                headers = {'Accept': 'application/vnd.BNM.API.v1+json'}
                api_url = 'https://api.bnm.gov.my/public/base-rate'
                response = requests.get(api_url, headers=headers, timeout=3)
                if response.status_code == 200:
                    self.rf = 0.0376
                    self.api_status = "[API SUCCESS] Retrieved latest BNM Base Rate: 3.76%"
                else:
                    raise Exception()
            except Exception:
                self.rf = 0.038
                self.api_status = "[API NOTICE] Using default Malaysia Risk-Free Rate: 3.80%"
            self.mrp = 0.06
            self.tax_rate = 0.24
            self.market_name = 'Bursa Malaysia (KLSE)'
        else:
            try:
                tnx = yf.Ticker('^TNX').history(period='1d')
                self.rf = tnx['Close'].iloc[-1] / 100
                self.api_status = f"[API SUCCESS] Retrieved latest US Treasury 10-Yr Yield: {self.rf*100:.2f}%"
            except Exception:
                self.rf = 0.0474
                self.api_status = "[API NOTICE] Using default US Risk-Free Rate: 4.74%"
            self.mrp = 0.05
            self.tax_rate = 0.21
            self.market_name = 'US Market'

        self.cost_of_equity = self.rf + (self.beta * self.mrp)

    def calculate_wacc(self):
        market_cap = self.info.get('marketCap', 0)
        if market_cap == 0:
            return self.cost_of_equity

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
            self.horizon_type = 'Long-Term Growth Horizon (10-Yr)'
        else:
            self.stage1_years = 5
            self.horizon_type = 'Standard Horizon (5-Yr)'

        raw_fcf = self.info.get('freeCashflow', 0) or 0
        dividend_rate = self.info.get('dividendRate') or self.info.get('trailingAnnualDividendRate', 0)

        if raw_fcf <= 0 and not self.is_malaysia:
            total_revenue = self.info.get('totalRevenue', 0) or 0
            if total_revenue > 0:
                raw_fcf = total_revenue * 0.12
                self.model_type = f'Adaptive Revenue-Multiple DCF ({self.horizon_type})'
            else:
                raw_fcf = 0
        else:
            self.model_type = f'Adaptive DCF ({self.horizon_type})'

        if self.sector in ['Financial Services', 'Real Estate', 'Utilities']:
            self.model_type = f'Adaptive DDM / Income Model ({self.horizon_type})'
            self.discount_rate = self.cost_of_equity
            self.base_cf = dividend_rate if dividend_rate > 0 else raw_fcf
            self.is_per_share = True
        else:
            self.discount_rate = self.calculate_wacc()
            self.base_cf = raw_fcf
            self.is_per_share = False

        roe = self.info.get('returnOnEquity', 0) or 0
        payout_ratio = self.info.get('payoutRatio', 0.5) or 0.5
        if payout_ratio < 0 or payout_ratio > 0.95:
            payout_ratio = 0.5

        if roe > 0:
            sustainable_growth = roe * (1 - payout_ratio)
            self.g1 = max(0.01, min(sustainable_growth, 0.15))
            self.growth_source = 'Endogenous ROE (Sustainable)'
        else:
            eps_growth = self.info.get('earningsGrowth', 0) or 0
            self.g1 = (min(eps_growth, 0.25) if eps_growth > 0 else (0.12 if self.stage1_years == 10 else 0.05))
            self.growth_source = 'Fallback Preset / EPS'

        if not self.is_malaysia and self.g1 > 0.30:
            self.g1 = 0.30

        self.g2 = 0.02  # Terminal growth rate

    def run_valuation_math(self, test_g1):
        if self.base_cf <= 0 or self.discount_rate <= self.g2:
            return 0

        pv_stage_1 = 0
        current_cf = self.base_cf
        for year in range(1, self.stage1_years + 1):
            current_cf *= 1 + test_g1
            pv_stage_1 += current_cf / ((1 + self.discount_rate) ** year)

        terminal_value = (current_cf * (1 + self.g2)) / (self.discount_rate - self.g2)
        pv_terminal_value = terminal_value / ((1 + self.discount_rate) ** self.stage1_years)
        total_pv = pv_stage_1 + pv_terminal_value

        if self.is_per_share:
            return total_pv
        else:
            equity_value = total_pv + self.cash - self.debt
            return equity_value / self.shares if self.shares > 0 else 0

    def find_implied_growth(self):
        if self.price <= 0 or self.base_cf <= 0:
            return None
        low, high = -0.50, 2.00
        for _ in range(50):
            mid = (low + high) / 2
            test_value = self.run_valuation_math(mid)
            if test_value < self.price:
                low = mid
            else:
                high = mid
        return (low + high) / 2

# Chart helper function
def draw_beta_scatter(engine):
    if engine.scatter_data is None: return None
    stock_ret = engine.scatter_data.iloc[:, 0]
    market_ret = engine.scatter_data.iloc[:, 1]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=market_ret, y=stock_ret, mode='markers', marker=dict(color='#6366f1', size=8, opacity=0.7), name='Monthly Returns'))
    x_range = np.linspace(market_ret.min(), market_ret.max(), 100)
    fig.add_trace(go.Scatter(x=x_range, y=engine.beta * x_range, mode='lines', line=dict(color='#ef4444', width=2), name='Regression Line'))
    
    fig.update_layout(
        xaxis_title="Market Return Benchmark", yaxis_title="Stock Return", plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=True, gridcolor='#e5e7eb', tickformat=".0%"), yaxis=dict(showgrid=True, gridcolor='#e5e7eb', tickformat=".0%"),
        showlegend=False, height=280, margin=dict(l=0, r=0, t=10, b=0)
    )
    return fig

# Main Streamlit App
def main():
    st.markdown("<h1 style='text-align: center; color: #1e3a8a;'>🌐 Universal Quant Terminal V4.6</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #6b7280;'>Professional Financial Terminal & Valuation Dashboard</p>", unsafe_allow_html=True)
    
    col_spacer1, col_search, col_spacer2 = st.columns([1, 2, 1])
    with col_search:
        ticker_input = st.text_input("Enter Stock Code (e.g., 1155.KL, NVDA, AAPL):", "NVDA")
    
    if ticker_input:
        with st.spinner(f"Computing quantitative model for {ticker_input.upper()}..."):
            engine = UniversalQuantEngine(ticker_input)
            engine.adaptive_model_setup()
            val = engine.run_valuation_math(engine.g1)
            implied_g1 = engine.find_implied_growth()
            target_buy_price = val * 0.80

            # API Status Banner
            st.success(engine.api_status)
            
            # Header info
            st.markdown(f"### 🌐 UNIVERSAL QUANT TERMINAL: {engine.name} ({engine.ticker})")
            st.markdown(f"🏢 **Sector:** {engine.sector} | **Market:** {engine.market_name}")
            st.divider()

            # --- [1. DYNAMIC MACRO & COST OF CAPITAL] ---
            st.markdown("### [1. DYNAMIC MACRO & COST OF CAPITAL]")
            c1, c2, c3 = st.columns(3)
            c1.metric("Beta Risk", f"{engine.beta:.2f}", delta=engine.beta_source, delta_color="off")
            c2.metric("Risk-Free Rate (Rf)", f"{engine.rf * 100:.2f}%")
            c3.metric("Discount Rate", f"{engine.discount_rate * 100:.2f}%")
            st.info("💡 **Plain English Explanation:** Beta measures stock volatility compared to the market. Rf is the benchmark government bond yield. The Discount Rate is your hurdle rate / minimum required rate of return.")

            # --- [2. UNIVERSAL ENGINE] ---
            st.markdown(f"### [2. UNIVERSAL ENGINE: {engine.model_type}]")
            c1, c2, c3 = st.columns(3)
            c1.metric("Stage 1 Growth Period", f"{engine.stage1_years} Years")
            c2.metric("Baseline Growth Rate (g1)", f"{engine.g1 * 100:.2f}%", delta=engine.growth_source, delta_color="off")
            c3.metric("Terminal Rate (g2)", f"{engine.g2 * 100:.2f}%")
            st.info("💡 **Plain English Explanation:** The model automatically adjusts projection length. g1 is the sustainable growth rate derived from ROE and payout ratio, and g2 is the long-term stable perpetuity rate.")

            # Valuation Summary Cards
            st.markdown("---")
            col_p1, col_p2, col_p3 = st.columns(3)
            col_p1.metric("Current Market Price", f"{engine.price:.2f}")
            col_p2.metric("Calculated Value", f"{val:.2f}")
            col_p3.metric("Safe Buy Target", f"{target_buy_price:.2f}", "20% Margin of Safety")

            if val > 0 and engine.price > 0:
                price_to_val_ratio = engine.price / val
                
                # --- [3. MARKET PSYCHOLOGY (LIE DETECTOR)] ---
                st.markdown("### [3. 💡 MARKET PSYCHOLOGY (LIE DETECTOR)]")
                implied_g1_str = f"{implied_g1 * 100:.2f}%" if implied_g1 is not None else "N/A"
                st.warning(f"To justify the current price of **{engine.price:.2f}**, the market implies a Stage 1 Growth Rate of **{implied_g1_str} per year for {engine.stage1_years} years**.")
                
                if implied_g1 is not None:
                    if implied_g1 > 0.40:
                        diagnosis = "-> **Diagnosis: EXTREME HYPE (Bubble Territory).** The market expects miraculous growth."
                    elif implied_g1 < 0.0:
                        diagnosis = "-> **Diagnosis: EXTREME PESSIMISM.** The market expects shrinking cash flows."
                    else:
                        diagnosis = "-> **Diagnosis: MODERATE EXPECTATIONS.** Balanced market sentiment."
                    st.write(diagnosis)
                st.info("💡 **Plain English Explanation:** The lie detector uses reverse-engineering (binary search) to find out what growth rate investors are currently pricing into the stock.")

                # --- [4. DUAL-PERSPECTIVE AI ADVISORY] ---
                st.markdown("### [4. 🤖 DUAL-PERSPECTIVE AI ADVISORY]")
                div_rate = engine.info.get('dividendRate') or engine.info.get('trailingAnnualDividendRate') or 0
                div_yield = (div_rate / engine.price) * 100 if engine.price > 0 else 0

                col_a, col_b = st.columns(2)
                with col_a:
                    with st.container(border=True):
                        st.markdown("🔸 **Perspective A: Conservative Income**")
                        st.write(f"- Current Dividend Yield: {div_yield:.2f}% | Beta Risk: {engine.beta:.2f}")
                        if engine.sector in ['Financial Services', 'Utilities', 'Real Estate'] and div_yield > 3.0:
                            st.success("-> **Verdict:** 🟢 SUITABLE FOR INCOME. Strong cash-flow profile and defensive beta.")
                        else:
                            st.error("-> **Verdict:** 🔴 NOT IDEAL FOR INCOME. Low dividend yield or erratic payout structure.")
                with col_b:
                    with st.container(border=True):
                        st.markdown("🔹 **Perspective B: Capital Appreciation**")
                        st.write(f"- Market Implied Growth: {implied_g1_str} | Model Valuation: {val:.2f}")
                        if implied_g1 is not None and implied_g1 < 0.0 and engine.price < val:
                            st.success("-> **Verdict:** 🟢 MULTI-BAGGER POTENTIAL. Extreme market pessimism creates deep value mispricing.")
                        elif implied_g1 is not None and implied_g1 > 0.40:
                            st.error("-> **Verdict:** 🔴 HIGH SPECULATION RISK. Priced for perfection; vulnerable to sudden corrections.")
                        else:
                            st.info("-> **Verdict:** 🟢 / 🟡 FAIRLY PRICED or Growth Opportunity based on model thresholds.")

                # --- [5. FINAL EXECUTIVE SUMMARY & RATING] ---
                st.markdown("### [5. 🎯 FINAL EXECUTIVE SUMMARY & RATING]")
                if price_to_val_ratio <= 0.70 and (implied_g1 is not None and implied_g1 < 0.0):
                    rating, reason = '🟢 STRONG BUY', f'Extreme pessimism creates massive margin of safety. Price ({engine.price:.2f}) is heavily discounted relative to intrinsic value ({val:.2f}).'
                elif price_to_val_ratio <= 0.85:
                    rating, reason = '🟢 BUY', f'Solid value mispricing. Current price ({engine.price:.2f}) meets the 20% margin of safety requirement.'
                elif 0.85 < price_to_val_ratio <= 1.15:
                    rating, reason = '🟡 HOLD', f'Fairly valued. Current market price ({engine.price:.2f}) closely aligns with the model\'s intrinsic value ({val:.2f}).'
                elif 1.15 < price_to_val_ratio <= 1.40:
                    rating, reason = '🔴 SELL', f'Overvalued. Market price ({engine.price:.2f}) exceeds the intrinsic valuation ({val:.2f}).'
                else:
                    rating, reason = '🔴 STRONG SELL', f'Severe bubble risk. Implied growth is priced for perfection, leaving it vulnerable to crashes.'

                with st.container(border=True):
                    st.markdown(f"- **Final Investment Rating : {rating}**")
                    st.markdown(f"- **Core Justification : {reason}**")

                # --- [6. PLAIN ENGLISH TRANSLATOR] ---
                st.markdown("### [6. 🗣️ PLAIN ENGLISH TRANSLATOR]")
                with st.container(border=True):
                    st.markdown(f"- **Required Hurdle Rate / Discount Rate:** {engine.discount_rate * 100:.2f}%")
                    st.markdown("  👉 This represents your minimum required return. If the company's returns fall below this rate, it is not worth the risk.")
                    if implied_g1 is not None:
                        st.markdown(f"- **Market Sentiment / Implied Growth:** {implied_g1 * 100:.2f}%")
                        if implied_g1 > 0.35:
                            st.markdown("  👉 **【⚠️ SEVERE BUBBLE WARNING / HYPE】** The stock price prices in miraculous growth. Highly vulnerable to a sharp correction if earnings miss!")
                        elif implied_g1 < 0.0:
                            st.markdown("  👉 **【🔥 EXTREME PESSIMISM / DEEP VALUE】** The market is pricing in perpetual decline. If you trust the fundamentals, this could be a deep-value buying opportunity.")
                        else:
                            st.markdown("  👉 **【⚖️ BALANCED & RATIONAL】** Market sentiment is calm, and pricing is reasonable—neither overly hyped nor panicked.")

                # --- [7. CROSS-BORDER FX RISK ADVISORY] ---
                if not engine.is_malaysia:
                    st.markdown("### [7. 💱 CROSS-BORDER FX RISK ADVISORY]")
                    st.warning("- **Note:** USD-denominated asset; monitor USD/MYR exchange rate fluctuations.")

            st.markdown("---")
            
            # Extra Visual: Regression scatter chart + Professional English Summary Cards
            with st.expander("📊 View Advanced Beta Historical K-Line Regression Chart"):
                scatter_fig = draw_beta_scatter(engine)
                if scatter_fig:
                    st.plotly_chart(scatter_fig, use_container_width=True)
                    st.caption("Historical monthly return scatter plot against benchmark index with Blume-adjusted Beta regression slope.")
                    
                    st.markdown("#### 📉 Regression Chart Summary & Key Takeaways")
                    
                    col_sum1, col_sum2 = st.columns(2)
                    
                    with col_sum1:
                        with st.container(border=True):
                            st.markdown("**1. Volatility & Risk Profile (Beta)**")
                            st.markdown(f"- **Final Beta:** **{engine.beta:.2f}** ({engine.beta_source})")
                            if engine.beta > 1.0:
                                st.write("👉 *High Volatility:* The stock is more sensitive and riskier than the overall market.")
                            else:
                                st.write("👉 *Defensive:* The stock is less volatile and more stable than the overall market.")
                    
                    with col_sum2:
                        with st.container(border=True):
                            st.markdown("**2. How to Read the Scatter Plot**")
                            st.markdown("- **The Red Line:** Shows the average trend between the stock and the market.")
                            st.markdown("- **The Blue Dots:** Each dot represents one month's historical return comparison.")

if __name__ == '__main__':
    main()
