import datetime
import numpy as np
import pandas as pd
import requests
import yfinance as yf
import streamlit as st
import plotly.graph_objects as go

# ==============================================================================
# 1. 页面基本配置与反爬虫会话
# ==============================================================================
st.set_page_config(page_title="Universal Quant Terminal V8.0", page_icon="💹", layout="wide")

@st.cache_resource
def get_yf_session():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    })
    return session

# ==============================================================================
# 2. 国际化多语言字典 (中英双语完美支持 - 包含你所有的旧版深度解释)
# ==============================================================================
TEXTS = {
    "zh": {
        "title": "🌐 智能量化金融终端 (ESG 双语旗舰版)",
        "subtitle": "融合 CAPM、DCF、WACC 与市场情绪测谎仪的专业机构级估值平台",
        "lang_label": "🌐 语言 / Language",
        "quick_tag": "🔥 热门快捷测评：",
        "input_label": "输入股票代码 (如 1155.KL, NVDA, AAPL)：",
        "param_header": "⚙️ 估值核心宏观参数设定",
        "erp_label": "股市风险溢价要求 (ERP)",
        "g2_label": "长期永续增长率 (Terminal g)",
        "esg_caption": "🌿 本系统已自动结合可持续金融 (Sustainable Finance) 与 ESG 行业风险溢价进行折现率修正。",
        
        # 结果面板
        "macro_title": "[1. 动态宏观与资本成本 (DYNAMIC MACRO & COST OF CAPITAL)]",
        "macro_exp": "💡 **通俗解释 (Plain English)：** Beta 衡量股票相对于大盘的波动率。Rf 是无风险国债利率。WACC / 折现率是你作为投资者要求的最低及格线回报率。",
        "engine_title": "[2. 智能自适应估值引擎 (UNIVERSAL ADAPTIVE ENGINE)]",
        "engine_exp": "💡 **通俗解释 (Plain English)：** 系统根据行业特性自动调整预测周期。g1 是基于 ROE 算出的可持续增长率，g2 是长期永续增长率。",
        "price": "当前市场价格",
        "wacc": "WACC / 折现率",
        "fair_val": "内在公道估值",
        "safe_buy": "20% 安全边际买点",
        
        # 测谎仪与AI顾问
        "lie_title": "[3. 💡 市场情绪测谎仪 (MARKET PSYCHOLOGY / LIE DETECTOR)]",
        "lie_exp": "💡 **通俗解释 (Plain English)：** 测谎仪通过二分法反向推导，看看当前的市场价格到底在幻想这家公司未来每年增长多少。",
        "ai_title": "[4. 🤖 双视角 AI 投资顾问 (DUAL-PERSPECTIVE AI ADVISORY)]",
        "inc_title": "🔸 视角 A：保守派收息策略 (Conservative Income)",
        "cap_title": "🔹 视角 B：进取派资本增值 (Capital Appreciation)",
        "exec_title": "[5. 🎯 最终投资评级与执行摘要 (EXECUTIVE SUMMARY)]",
        
        # 翻译器与风险
        "plain_title": "[6. 🗣️ 小白通俗翻译器 (PLAIN ENGLISH TRANSLATOR)]",
        "fx_title": "[7. 💱 跨境汇率风险提示 (CROSS-BORDER FX RISK)]",
        "fx_content": "- **提示：** 此乃美元计价资产，请注意美元兑马币 (USD/MYR) 的汇率波动风险。",
        "chart_title": "[8. 📈 高级盘面与波动率回归分析]"
    },
    "en": {
        "title": "🌐 Universal Quant Terminal (Bilingual ESG Edition)",
        "subtitle": "Institutional-Grade Valuation Platform integrating CAPM, DCF, WACC & Market Lie Detector",
        "lang_label": "🌐 Language / 语言",
        "quick_tag": "🔥 Quick Select:",
        "input_label": "Enter Stock Ticker (e.g., 1155.KL, NVDA, AAPL):",
        "param_header": "⚙️ Core Macro Assumptions",
        "erp_label": "Equity Risk Premium (ERP)",
        "g2_label": "Terminal Growth Rate (g)",
        "esg_caption": "🌿 Sustainable Finance & ESG Sector Risk Premium automatically integrated into discount rate adjustments.",
        
        # Results
        "macro_title": "[1. DYNAMIC MACRO & COST OF CAPITAL]",
        "macro_exp": "💡 **Plain English Explanation:** Beta measures stock volatility compared to the market. Rf is the benchmark government bond yield. WACC / Discount Rate is your hurdle rate / minimum required rate of return.",
        "engine_title": "[2. UNIVERSAL ADAPTIVE ENGINE]",
        "engine_exp": "💡 **Plain English Explanation:** The model automatically adjusts projection length. g1 is the sustainable growth rate derived from ROE, and g2 is the perpetual rate.",
        "price": "Current Market Price",
        "wacc": "WACC / Discount Rate",
        "fair_val": "Intrinsic Fair Value",
        "safe_buy": "Safe Buy Target (20% MoS)",
        
        # Lie Detector & AI
        "lie_title": "[3. 💡 MARKET PSYCHOLOGY (LIE DETECTOR)]",
        "lie_exp": "💡 **Plain English Explanation:** The lie detector uses reverse-engineering to find out what growth rate investors are currently pricing into the stock.",
        "ai_title": "[4. 🤖 DUAL-PERSPECTIVE AI ADVISORY]",
        "inc_title": "🔸 Perspective A: Conservative Income",
        "cap_title": "🔹 Perspective B: Capital Appreciation",
        "exec_title": "[5. 🎯 FINAL EXECUTIVE SUMMARY & RATING]",
        
        # Translator & FX
        "plain_title": "[6. 🗣️ PLAIN ENGLISH TRANSLATOR]",
        "fx_title": "[7. 💱 CROSS-BORDER FX RISK ADVISORY]",
        "fx_content": "- **Note:** USD-denominated asset; monitor USD/MYR exchange rate fluctuations.",
        "chart_title": "[8. 📈 Advanced Price Action & Regression Analysis]"
    }
}

# ==============================================================================
# 3. 防崩溃财报提取函数
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

# ==============================================================================
# 4. 核心量化引擎 (WACC + Blume Beta + ESG)
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
# 5. 图表生成函数
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
# 6. 主程序与双语 UI 渲染
# ==============================================================================
def main():
    # 顶部双语切换栏
    col_title, col_lang = st.columns([3, 1.2])
    with col_lang:
        selected_lang = st.selectbox("🌐 Language / 语言", options=["中文", "English"], index=0)
        lang_key = "zh" if selected_lang == "中文" else "en"
        T = TEXTS[lang_key]

    with col_title:
        st.markdown(f"<h1 style='color: #0f172a; font-weight: 800; font-size: 2rem;'>{T['title']}</h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: #64748b; margin-top: -10px;'>{T['subtitle']}</p>", unsafe_allow_html=True)

    st.divider()

    # 快捷输入与选股面板
    with st.container(border=True):
        if "ticker_input" not in st.session_state: st.session_state.ticker_input = "NVDA"
        def set_ticker(t): st.session_state.ticker_input = t
        
        st.write(T['quick_tag'])
        q1, q2, q3, q4 = st.columns(4)
        q1.button("🇺🇸 NVDA", on_click=set_ticker, args=("NVDA",), use_container_width=True)
        q2.button("🇺🇸 AAPL", on_click=set_ticker, args=("AAPL",), use_container_width=True)
        q3.button("🇲🇾 MAYBANK (1155.KL)", on_click=set_ticker, args=("1155.KL",), use_container_width=True)
        q4.button("🇲🇾 TENAGA (5347.KL)", on_click=set_ticker, args=("5347.KL",), use_container_width=True)
        
        col_in1, col_in2, col_in3 = st.columns([2, 1, 1])
        with col_in1:
            ticker_input = st.text_input(T['input_label'], key="ticker_input")
        with col_in2:
            custom_erp = st.slider(T['erp_label'], 4.0, 7.0, 5.0, 0.1) / 100
        with col_in3:
            custom_g2 = st.slider(T['g2_label'], 1.0, 3.5, 2.0, 0.1) / 100
        
        st.caption(T['esg_caption'])

    if ticker_input:
        with st.spinner("Analyzing quantitative model..."):
            engine = UniversalQuantEngine(ticker_input)
            val, implied_g = engine.run_valuation(custom_erp, custom_g2)

            st.markdown(f"### 🏢 **{engine.name} ({engine.ticker})** | Sector: `{engine.sector}`")
            st.divider()

            # -------------------------------------------------------------
            # [1. 动态宏观与资本成本]
            # -------------------------------------------------------------
            st.markdown(f"### {T['macro_title']}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Beta Risk", f"{engine.beta:.2f}", delta=engine.beta_type, delta_color="off")
            c2.metric("Risk-Free Rate (Rf)", f"{engine.rf * 100:.2f}%")
            c3.metric("WACC / Discount Rate", f"{engine.r * 100:.2f}%", engine.esg_tag)
            st.info(T['macro_exp'])

            # -------------------------------------------------------------
            # [2. 智能自适应估值引擎]
            # -------------------------------------------------------------
            st.markdown(f"### {T['engine_title']}: {engine.model_type}")
            e1, e2, e3 = st.columns(3)
            e1.metric("Stage 1 Growth Period", f"{engine.horizon} Years")
            e2.metric("Baseline Growth Rate (g1)", f"{engine.g1 * 100:.2f}%")
            e3.metric("Terminal Rate (g2)", f"{engine.g2 * 100:.2f}%")
            st.info(T['engine_exp'])

            # 核心价格卡片
            st.markdown("---")
            p1, p2, p3 = st.columns(3)
            p1.metric(T['price'], f"{engine.price:.2f}")
            p2.metric(T['fair_val'], f"{val:.2f}")
            p3.metric(T['safe_buy'], f"{(val * 0.8):.2f}", "20% Margin of Safety")

            if val > 0 and engine.price > 0:
                price_to_val = engine.price / val

                # -------------------------------------------------------------
                # [3. 市场测谎仪 (Lie Detector)]
                # -------------------------------------------------------------
                st.markdown(f"### {T['lie_title']}")
                implied_g_str = f"{implied_g * 100:.2f}%" if implied_g is not None else "N/A"
                st.warning(f"To justify the current price of **{engine.price:.2f}**, the market implies a Growth Rate of **{implied_g_str} per year for {engine.horizon} years**.")
                
                if implied_g is not None:
                    if implied_g > 0.40: diag = "-> **Diagnosis: EXTREME HYPE (Bubble Territory).** The market expects miraculous growth."
                    elif implied_g < 0.0: diag = "-> **Diagnosis: EXTREME PESSIMISM.** The market expects shrinking cash flows."
                    else: diag = "-> **Diagnosis: MODERATE EXPECTATIONS.** Balanced market sentiment."
                    st.write(diag)
                st.info(T['lie_exp'])

                # -------------------------------------------------------------
                # [4. 双视角 AI 投资顾问 (Dual-Perspective AI Advisory)]
                # -------------------------------------------------------------
                st.markdown(f"### {T['ai_title']}")
                div_rate = engine.info.get('dividendRate') or engine.info.get('trailingAnnualDividendRate') or 0
                div_yield = (div_rate / engine.price) * 100 if engine.price > 0 else 0

                ai_a, ai_b = st.columns(2)
                with ai_a:
                    with st.container(border=True):
                        st.markdown(T['inc_title'])
                        st.write(f"- Current Dividend Yield: {div_yield:.2f}% | Beta Risk: {engine.beta:.2f}")
                        if engine.sector in ['Financial Services', 'Utilities', 'Real Estate'] and div_yield > 3.0:
                            st.success("-> **Verdict:** 🟢 SUITABLE FOR INCOME. Strong cash-flow profile.")
                        else:
                            st.error("-> **Verdict:** 🔴 NOT IDEAL FOR INCOME. Low dividend yield or erratic payout.")
                with ai_b:
                    with st.container(border=True):
                        st.markdown(T['cap_title'])
                        st.write(f"- Market Implied Growth: {implied_g_str} | Model Valuation: {val:.2f}")
                        if implied_g is not None and implied_g < 0.0 and engine.price < val:
                            st.success("-> **Verdict:** 🟢 MULTI-BAGGER POTENTIAL. Deep value mispricing.")
                        elif implied_g is not None and implied_g > 0.40:
                            st.error("-> **Verdict:** 🔴 HIGH SPECULATION RISK. Priced for perfection.")
                        else:
                            st.info("-> **Verdict:** 🟢 / 🟡 FAIRLY PRICED or Growth Opportunity.")

                # -------------------------------------------------------------
                # [5. 最终投资评级与执行摘要]
                # -------------------------------------------------------------
                st.markdown(f"### {T['exec_title']}")
                if price_to_val <= 0.70 and (implied_g is not None and implied_g < 0.0):
                    rating, reason = '🟢 STRONG BUY', f'Extreme pessimism creates massive margin of safety. Price ({engine.price:.2f}) is heavily discounted relative to intrinsic value ({val:.2f}).'
                elif price_to_val <= 0.85:
                    rating, reason = '🟢 BUY', f'Solid value mispricing. Current price ({engine.price:.2f}) meets the 20% margin of safety requirement.'
                elif 0.85 < price_to_val <= 1.15:
                    rating, reason = '🟡 HOLD', f'Fairly valued. Current market price ({engine.price:.2f}) aligns with intrinsic value ({val:.2f}).'
                elif 1.15 < price_to_val <= 1.40:
                    rating, reason = '🔴 SELL', f'Overvalued. Market price ({engine.price:.2f}) exceeds the intrinsic valuation ({val:.2f}).'
                else:
                    rating, reason = '🔴 STRONG SELL', f'Severe bubble risk. Implied growth is priced for perfection, leaving it vulnerable to crashes.'

                with st.container(border=True):
                    st.markdown(f"- **Final Investment Rating : {rating}**")
                    st.markdown(f"- **Core Justification : {reason}**")

                # -------------------------------------------------------------
                # [6. 小白通俗翻译器]
                # -------------------------------------------------------------
                st.markdown(f"### {T['plain_title']}")
                with st.container(border=True):
                    st.markdown(f"- **Required Hurdle Rate / Discount Rate:** {engine.r * 100:.2f}%")
                    st.markdown("  👉 This represents your minimum required return. If returns fall below this rate, it is not worth the risk.")
                    if implied_g is not None:
                        st.markdown(f"- **Market Sentiment / Implied Growth:** {implied_g * 100:.2f}%")
                        if implied_g > 0.35:
                            st.markdown("  👉 **【⚠️ SEVERE BUBBLE WARNING】** Stock price prices in miraculous growth. Highly vulnerable to correction!")
                        elif implied_g < 0.0:
                            st.markdown("  👉 **【🔥 EXTREME PESSIMISM / DEEP VALUE】** Market prices in perpetual decline. Potential deep value opportunity.")
                        else:
                            st.markdown("  👉 **【⚖️ BALANCED & RATIONAL】** Market sentiment is calm and pricing is reasonable.")

                # -------------------------------------------------------------
                # [7. 跨境汇率风险提示 (美股专属)]
                # -------------------------------------------------------------
                if not engine.is_malaysia:
                    st.markdown(f"### {T['fx_title']}")
                    st.warning(T['fx_content'])
                    
                    # 华尔街一致预期对照
                    ws_tgt = engine.info.get('targetMeanPrice')
                    if ws_tgt:
                        st.markdown("---")
                        st.info(f"🏛️ **Wall Street Analyst Consensus Target:** **${ws_tgt:.2f}** | Your Model Intrinsic Value: **${val:.2f}**")

            # -------------------------------------------------------------
            # [8. 高级盘面与波动率回归分析]
            # -------------------------------------------------------------
            st.markdown(f"### {T['chart_title']}")
            c_chart1, c_chart2 = st.columns(2)
            with c_chart1:
                with st.container(border=True):
                    st.markdown("**1-Year Candlestick (MA20 & MA50)**")
                    st.plotly_chart(draw_pro_candlestick(engine.ticker, engine.session), use_container_width=True)
            with c_chart2:
                with st.container(border=True):
                    st.markdown(f"**3-Year Beta Regression (β = {engine.beta:.2f})**")
                    st.plotly_chart(draw_beta_scatter(engine), use_container_width=True)

if __name__ == '__main__':
    main()
