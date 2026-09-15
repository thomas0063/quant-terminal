# 🌐 Universal Quant Terminal (ESG Bilingual Edition)

An institutional-grade quantitative stock valuation and research terminal built with **Python, Streamlit, and Plotly**. It integrates **CAPM with Blume-Adjusted Beta, DCF/DDM models, WACC with ESG Risk Premiums, and an AI-driven Market Psychology Lie Detector**. Supports both **Bursa Malaysia** and **US Equities** with instant **Bilingual (English/Chinese)** switching.

---

## 🌟 Core Academic & Technical Highlights

1. **Sustainable Finance & ESG-Adjusted WACC**
   - Going beyond standard corporate finance, the system automatically evaluates sector-specific environmental and regulatory risks. 
   - High-carbon or high-risk sectors (e.g., Energy, Materials) receive a **discount rate penalty (+1.5%)**, while green/low-risk sectors receive a reward, mathematically refining the intrinsic valuation to align with modern Sustainable Finance principles.

2. **Blume-Adjusted Beta & R² Regression Analysis**
   - Utilizes 3-year weekly adjusted returns to perform Ordinary Least Squares (OLS) regression against professional benchmarks (**iShares MSCI Malaysia ETF (EWM)** for Bursa equities and **S&P 500** for US equities).
   - Applies **Blume's Adjustment ($0.67\beta + 0.33$)** to correct historical mean-reversion bias. Displays real-time scatter plots with dynamic **$R^2$ (Goodness of Fit)** metrics to distinguish between systemic market risk and independent growth drivers.

3. **Market Psychology "Lie Detector" (Implied Growth)**
   - Employs a reverse-engineering binary search algorithm to calculate the exact Stage 1 growth rate that investors are currently pricing into the stock. Instantly flags extreme market bubbles or deep-value pessimism.

4. **Adaptive Valuation Engine (DCF & DDM)**
   - Automatically switches between **Discounted Cash Flow (DCF)** and **Dividend Discount Model (DDM)** based on industry characteristics (e.g., DDM for Financials and Utilities).
   - Features a robust, vector-based financial extractor (`get_fin_metric`) designed to safely parse unstable Yahoo Finance data structures and prevent runtime crashes.

5. **Instant Bilingual User Interface (EN / ZH)**
   - Fully internationalized terminal architecture allowing users to toggle between English and Chinese on the fly, making complex financial metrics accessible to bilingual evaluators.

---

## 🚀 Local Installation & Execution

1. **Clone the repository**:
   ```bash
   git clone [https://github.com/thomas0063/quant-terminal.git](https://github.com/thomas0063/quant-terminal.git)
   cd quant-terminal
