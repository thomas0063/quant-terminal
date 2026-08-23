import datetime
import numpy as np
import pandas as pd
import requests
import yfinance as yf
import streamlit as st

# 1. 网页全局设置 (必须放在最开头)
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
                else:
                    raise Exception()
            except Exception:
                self.rf = 0.038
            self.mrp = 0.06
            self.tax_rate = 0.24
            self.market_name = 'Bursa Malaysia (KLSE)'
        else:
            try:
                tnx = yf.Ticker('^TNX').history(period='1d')
                self.rf = tnx['Close'].iloc[-1] / 100
            except Exception:
                self.rf = 0.042
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

        self.g2 = 0.02

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

    # ====== 🌟 核心前端数据打包引擎 (取代了原本的 print) ======
    def get_valuation_data(self):
        self.adaptive_model_setup()
        val = self.run_valuation_math(self.g1)
        implied_g1 = self.find_implied_growth()

        # 计算安全边际
        mos_pct = ((val - self.price) / self.price) * 100 if val > 0 and self.price > 0 else 0

        # 判断最终评级
        rating, reason, color = "N/A", "Insufficient Data", "normal"
        if val > 0 and self.price > 0:
            price_to_val_ratio = self.price / val
            if price_to_val_ratio <= 0.70 and (implied_g1 is not None and implied_g1 < 0.0):
                rating, reason, color = '🟢 STRONG BUY', f'Extreme pessimism creates massive margin of safety. Deep value mispricing.', 'success'
            elif price_to_val_ratio <= 0.85:
                rating, reason, color = '🟢 BUY', f'Solid value mispricing. Price ({self.price:.2f}) meets 20% margin of safety.', 'success'
            elif 0.85 < price_to_val_ratio <= 1.15:
                rating, reason, color = '🟡 HOLD', 'Fairly valued relative to fundamentals.', 'warning'
            elif 1.15 < price_to_val_ratio <= 1.40:
                rating, reason, color = '🔴 SELL', f'Overvalued. Market price exceeds intrinsic valuation ({val:.2f}).', 'error'
            else:
                rating, reason, color = '🔴 STRONG SELL', 'Severe bubble risk. Priced for perfection.', 'error'

        # 判断市场心理
        psy_diag = "N/A"
        if implied_g1 is not None:
            if implied_g1 > 0.35:
                psy_diag = '⚠️ **EXTREME HYPE:** The market expects miraculous growth. Highly vulnerable to a sharp correction.'
            elif implied_g1 < 0.0:
                psy_diag = '🔥 **EXTREME PESSIMISM:** The market expects shrinking cash flows. Deep value territory if fundamentals hold.'
            else:
                psy_diag = '⚖️ **MODERATE EXPECTATIONS:** Balanced market sentiment.'

        return {
            "name": self.name,
            "sector": self.sector,
            "market": self.market_name,
            "price": self.price,
            "val": val,
            "mos_pct": mos_pct,
            "implied_g1": implied_g1,
            "beta": self.beta,
            "beta_source": self.beta_source,
            "discount_rate": self.discount_rate,
            "g1": self.g1,
            "growth_source": self.growth_source,
            "rating": rating,
            "reason": reason,
            "color": color,
            "psy_diag": psy_diag
        }


# ==========================================
# 🎨 STREAMLIT 网页前端渲染层 (替换了 while True)
# ==========================================
def main():
    st.title("🌐 Universal Quant Terminal")
    st.markdown("Institutional-grade valuation engine incorporating Endogenous ROE and CAPM regression.")

    # 侧边栏输入框
    st.sidebar.header("⚙️ Terminal Settings")
    ticker_input = st.sidebar.text_input("Enter Stock Ticker (e.g., 1155.KL, NVDA, AAPL)", "1155.KL")
    
    if st.sidebar.button("Run Valuation", type="primary"):
        with st.spinner(f"Running adaptive valuation for {ticker_input.upper()}..."):
            try:
                # 1. 运行引擎获取数据
                engine = UniversalQuantEngine(ticker_input)
                data = engine.get_valuation_data()

                st.subheader(f"{data['name']} ({ticker_input.upper()})")

                # 2. 顶部四大核心数据面板 (对应你朋友截图的第一排)
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Current Price", f"{data['price']:.2f}")
                col2.metric("Calculated Value", f"{data['val']:.2f}")
                col3.metric("Margin of Safety", f"{data['mos_pct']:.2f}%")
                
                implied_g1_str = f"{data['implied_g1']*100:.2f}%" if data['implied_g1'] is not None else "N/A"
                col4.metric("Market Implied g1", implied_g1_str)

                st.divider() # 一条分割线

                # 3. 宏观与参数模块
                st.markdown("### 📊 Macro & Model Parameters")
                st.markdown(f"- **Sector & Market:** {data['sector']} | {data['market']}")
                st.markdown(f"- **Beta Risk:** {data['beta']:.2f} (Source: {data['beta_source']})")
                st.markdown(f"- **Required Discount Rate (WACC/Ke):** {data['discount_rate']*100:.2f}%")
                st.markdown(f"- **Baseline Growth (g1):** {data['g1']*100:.2f}% (Source: {data['growth_source']})")

                # 4. 市场测谎仪
                st.markdown("### 💡 Market Psychology (Lie Detector)")
                st.write(data['psy_diag'])

                # 5. 执行摘要与大白话建议框
                st.markdown("### 🎯 Executive Summary & Plain English Guide")
                
                # 根据评级颜色输出不同的漂亮框框
                rating_text = f"Rating: **{data['rating']}** - {data['reason']}"
                if data['color'] == 'success':
                    st.success(rating_text)
                elif data['color'] == 'warning':
                    st.warning(rating_text)
                else:
                    st.error(rating_text)

                # 纯英文通俗解读蓝框
                plain_text = f"**Plain English Takeaway:** Your hurdle rate is {data['discount_rate']*100:.2f}%. The market is pricing in a growth rate of {implied_g1_str}. Make sure the company's real-world execution matches this expectation before deploying capital."
                st.info(plain_text)

                # 🌟 额外彩蛋：加一个简单的历史走势图
                st.markdown("### 📈 Historical Price Chart (1 Year)")
                chart_data = engine.stock.history(period="1y")
                if not chart_data.empty:
                    st.line_chart(chart_data['Close'])

            except Exception as e:
                st.error(f"Error processing {ticker_input}: {e}")
                st.info("Check if the ticker is correct or if Yahoo Finance data is available.")

if __name__ == '__main__':
    main()
