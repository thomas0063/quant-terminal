import numpy as np
import pandas as pd
import requests
import streamlit as st
import yfinance as yf

# --- 网页页面配置 ---
st.set_page_config(
    page_title="Universal Quant Terminal", page_icon="🌐", layout="wide"
)

st.title("🌐 Universal Quant Terminal (Web Edition)")
st.markdown(
    "**Institutional-Grade Cross-Market Valuation Engine** (Supports Bursa"
    " Malaysia & US Market with AI Lie Detector)"
)


class WebUniversalQuantEngine:

  def __init__(self, ticker):
    self.ticker = ticker.strip().upper()
    self.stock = yf.Ticker(self.ticker)
    self.info = self.stock.info
    self.name = self.info.get("longName", "Unknown Company")
    self.sector = self.info.get("sector", "Unknown")
    self.is_malaysia = self.ticker.endswith(".KL")

    self.price = self.info.get("currentPrice") or self.info.get(
        "previousClose", 0
    )
    self.shares = self.info.get("sharesOutstanding", 1) or 1
    self.cash = self.info.get("totalCash", 0) or 0
    self.debt = self.info.get("totalDebt", 0) or 0

  def compute_blume_beta(self):
    sector_default_betas = {
        "Financial Services": 0.85,
        "Real Estate": 0.60,
        "Utilities": 0.65,
        "Technology": 1.15,
        "Consumer Cyclical": 0.75,
        "Industrials": 0.90,
    }
    fallback_beta = sector_default_betas.get(self.sector, 0.85)
    try:
      market_symbol = "^KLSE" if self.is_malaysia else "^GSPC"
      stock_hist = self.stock.history(period="3y", interval="1mo")
      market_hist = yf.Ticker(market_symbol).history(
          period="3y", interval="1mo"
      )

      if stock_hist.empty or market_hist.empty:
        return fallback_beta, "sector_fallback"

      stock_ret = stock_hist["Close"].pct_change().dropna()
      market_ret = market_hist["Close"].pct_change().dropna()

      aligned = pd.concat([stock_ret, market_ret], axis=1).dropna()
      if len(aligned) < 12:
        return fallback_beta, "sector_fallback"

      cov_matrix = np.cov(aligned.iloc[:, 0], aligned.iloc[:, 1])
      covariance = cov_matrix[0, 1]
      market_variance = np.var(aligned.iloc[:, 1], ddof=1)

      if market_variance <= 0:
        return fallback_beta, "sector_fallback"

      raw_beta = covariance / market_variance
      if not np.isfinite(raw_beta) or raw_beta <= 0.2 or raw_beta > 2.5:
        return fallback_beta, "sector_fallback"

      blume_beta = 0.67 * raw_beta + 0.33 * 1.0  # Blume 调整[cite: 1, 2]
      final_beta = max(0.3, min(blume_beta, 2.5))
      return round(final_beta, 2), "quant_regression"
    except Exception:
      return fallback_beta, "sector_fallback"

  def get_macro_environment(self):
    self.beta, self.beta_source = self.compute_blume_beta()
    if self.is_malaysia:
      self.rf = 0.038
      self.mrp = 0.06
      self.tax_rate = 0.24
      self.market_name = "Bursa Malaysia (KLSE)"
    else:
      try:
        tnx = yf.Ticker("^TNX").history(period="1d")
        self.rf = tnx["Close"].iloc[-1] / 100
      except Exception:
        self.rf = 0.042
      self.mrp = 0.05
      self.tax_rate = 0.21
      self.market_name = "US Market"
    self.cost_of_equity = self.rf + (self.beta * self.mrp)

  def calculate_wacc(self):
    market_cap = self.info.get("marketCap", 0)
    if market_cap == 0:
      return self.cost_of_equity
    total_capital = market_cap + self.debt
    weight_equity = market_cap / total_capital
    weight_debt = self.debt / total_capital
    interest_expense = abs(self.info.get("interestExpense", 0) or 0)
    cost_of_debt = min(
        (interest_expense / self.debt) if self.debt > 0 else 0.05, 0.10
    )
    return (weight_equity * self.cost_of_equity) + (
        weight_debt * cost_of_debt * (1 - self.tax_rate)
    )

  def run_analysis(self):
    self.get_macro_environment()

    # 预测年限
    if (
        self.sector in ["Technology", "Communication Services"]
        or self.info.get("earningsGrowth", 0) > 0.20
    ):
      self.stage1_years = 10
      horizon_type = "Long-Term Growth (10-Yr)"
    else:
      self.stage1_years = 5
      horizon_type = "Standard (5-Yr)"

    raw_fcf = self.info.get("freeCashflow", 0) or 0
    dividend_rate = self.info.get("dividendRate") or self.info.get(
        "trailingAnnualDividendRate", 0
    )

    if raw_fcf <= 0 and not self.is_malaysia:
      total_revenue = self.info.get("totalRevenue", 0) or 0
      raw_fcf = total_revenue * 0.12 if total_revenue > 0 else 0

    if self.sector in ["Financial Services", "Real Estate", "Utilities"]:
      self.discount_rate = self.cost_of_equity
      self.base_cf = dividend_rate if dividend_rate > 0 else raw_fcf
      self.is_per_share = True
    else:
      self.discount_rate = self.calculate_wacc()
      self.base_cf = raw_fcf
      self.is_per_share = False

    # 内生 ROE 增长率
    roe = self.info.get("returnOnEquity", 0) or 0
    payout_ratio = self.info.get("payoutRatio", 0.5) or 0.5
    if roe > 0:
      sustainable_growth = roe * (1 - payout_ratio)
      self.g1 = max(0.01, min(sustainable_growth, 0.15))
      self.growth_source = "Endogenous ROE (Sustainable)"
    else:
      eps_growth = self.info.get("earningsGrowth", 0) or 0
      self.g1 = (
          min(eps_growth, 0.25)
          if eps_growth > 0
          else (0.12 if self.stage1_years == 10 else 0.05)
      )
      self.growth_source = "Fallback Preset"

    if not self.is_malaysia and self.g1 > 0.30:
      self.g1 = 0.30
    self.g2 = 0.02

    # 折现数学
    if self.base_cf <= 0 or self.discount_rate <= self.g2:
      return None

    pv_stage_1 = 0
    current_cf = self.base_cf
    for year in range(1, self.stage1_years + 1):
      current_cf *= 1 + self.g1
      pv_stage_1 += current_cf / ((1 + self.discount_rate) ** year)

    terminal_value = (current_cf * (1 + self.g2)) / (
        self.discount_rate - self.g2
    )
    pv_terminal_value = terminal_value / (
        (1 + self.discount_rate) ** self.stage1_years
    )
    total_pv = pv_stage_1 + pv_terminal_value

    if self.is_per_share:
      val = total_pv
    else:
      equity_value = total_pv + self.cash - self.debt
      val = equity_value / self.shares if self.shares > 0 else 0

    # 测谎仪二分法
    low, high = -0.50, 2.00
    for _ in range(50):
      mid = (low + high) / 2
      # 简易测谎测试
      cur = self.base_cf
      pv = 0
      for y in range(1, self.stage1_years + 1):
        cur *= 1 + mid
        pv += cur / ((1 + self.discount_rate) ** y)
      tv = (cur * (1 + self.g2)) / (self.discount_rate - self.g2)
      tpv = tv / ((1 + self.discount_rate) ** self.stage1_years)
      t_val = (
          (pv + tpv)
          if self.is_per_share
          else ((pv + tpv + self.cash - self.debt) / self.shares)
      )
      if t_val < self.price:
        low = mid
      else:
        high = mid
    implied_g1 = (low + high) / 2

    return {
      "name": self.name,
      "sector": self.sector,
      "market": self.market_name,
      "beta": self.beta,
      "beta_source": self.beta_source,
      "discount_rate": self.discount_rate,
      "g1": self.g1,
      "growth_source": self.growth_source,
      "price": self.price,
      "valuation": val,
      "implied_g1": implied_g1,
    }


# --- 网页交互界面 ---
user_ticker = st.text_input(
    "Enter Stock Ticker (e.g., 1155.KL, NVDA, AAPL):", "1155.KL"
)

if st.button("Run Valuation & Analysis"):
  with st.spinner("Analyzing financial statements & running quant models..."):
    try:
      engine = WebUniversalQuantEngine(user_ticker)
      res = engine.run_analysis()

      if res:
        st.success(f"Successfully Analyzed: {res['name']} ({user_ticker})")

        # 核心指标展示卡片
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Current Price", f"RM / $ {res['price']:.2f}")
        col2.metric("Calculated Value", f"{res['valuation']:.2f}")
        col3.metric(
            "Margin of Safety",
            f"{((res['valuation'] - res['price'])/res['price'])*100:.2f}%",
        )
        col4.metric("Market Implied g1", f"{res['implied_g1']*100:.2f}%")

        # 详细参数面板
        st.markdown("### 📊 Macro & Model Parameters")
        st.write(
            f"- **Sector & Market**: {res['sector']} | {res['market']}"
        )
        st.write(
            f"- **Beta Risk**: {res['beta']:.2f} (Source: {res['beta_source']})"
            "[cite: 1, 2]"
        )
        st.write(f"- **Required Discount Rate (WACC/Ke)**: {res['discount_rate']*100:.2f}%")
        st.write(
            f"- **Baseline Growth (g1)**: {res['g1']*100:.2f}% (Source:"
            f" {res['growth_source']})"
        )

        # 心理学测谎仪诊断
        st.markdown("### 💡 Market Psychology (Lie Detector)")
        if res["implied_g1"] > 0.40:
          st.error(
              "⚠️ EXTREME HYPE (Bubble Territory): The market expects"
              " miraculous growth."
          )
        elif res["implied_g1"] < 0.0:
          st.info(
              "🔥 EXTREME PESSIMISM (Deep Value): The market expects shrinking"
              " cash flows."
          )
        else:
          st.markdown(
              "⚖️ **MODERATE EXPECTATIONS**: Balanced market sentiment."
          )

        # 最终评级结论
        st.markdown("### 🎯 Executive Summary & Plain English Guide")
        ratio = res["price"] / res["valuation"]
        if ratio <= 0.85:
          st.success("Rating: 🟢 BUY / STRONG BUY - Attractive margin of safety.")
        elif 0.85 < ratio <= 1.15:
          st.warning("Rating: 🟡 HOLD - Fairly valued relative to fundamentals.")
        else:
          st.error(
              "Rating: 🔴 SELL / STRONG SELL - Overvalued and priced for"
              " perfection."
          )

        st.info(
            "🗣️ **Plain English Takeaway**: Your hurdle rate is"
            f" {res['discount_rate']*100:.2f}%. The market is pricing in a"
            f" growth rate of {res['implied_g1']*100:.2f}%. Make sure the"
            " company's real-world execution matches this expectation before"
            " deploying capital."
        )
      else:
        st.error("Insufficient financial metrics for model convergence.")
    except Exception as e:
      st.error(f"Error processing ticker: {e}")