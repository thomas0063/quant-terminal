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
st.set_page_config(
    page_title="Universal Quant Terminal - Ultimate Edition", 
    page_icon="💎", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# ==============================================================================
# 2. 独家高级 CSS 视觉引擎 (Bento Box 等高对齐 + 冰蓝框架感 + 清爽深蓝背景)
# ==============================================================================
PREMIUM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

/* 全局背景：清爽的深石墨蓝渐变 */
.stApp {
    background: radial-gradient(circle at 50% 0%, #1e293b 0%, #0f172a 60%, #090d16 100%) !important;
    font-family: 'Inter', -apple-system, sans-serif !important;
    color: #f8fafc !important;
}
.block-container { padding-top: 2rem !important; max-width: 1280px !important; }

header[data-testid="stHeader"] { background: transparent !important; }

/* 🌟 核心：强制所有列内元素等高，并加上精致的天蓝色边框与深蓝实底 */
[data-testid="column"] > div {
    height: 100% !important;
}
[data-testid="stVerticalBlockBorderWrapper"] {
    background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.85) 100%) !important;
    border: 1px solid rgba(56, 189, 248, 0.3) !important;
    border-radius: 14px !important;
    box-shadow: 0 8px 24px -4px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.08) !important;
    backdrop-filter: blur(12px) !important;
    transition: all 0.3s ease !important;
    padding: 16px 20px !important;
    height: 100% !important;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border-color: #38bdf8 !important;
    box-shadow: 0 10px 30px -4px rgba(56, 189, 248, 0.3) !important;
    transform: translateY(-2px);
}

/* 按钮专属暗黑科技样式 */
.stButton > button {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%) !important;
    color: #38bdf8 !important;
    border: 1px solid rgba(56, 189, 248, 0.3) !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    transition: all 0.25s ease !important;
}
.stButton > button:hover {
    background: rgba(56, 189, 248, 0.15) !important;
    color: #ffffff !important;
    border-color: #38bdf8 !important;
    box-shadow: 0 6px 18px -2px rgba(56, 189, 248, 0.4) !important;
    transform: translateY(-2px);
}

label { color: #cbd5e1 !important; font-weight: 500 !important; }
p { color: #e2e8f0 !important; }
h1, h2, h3, h4, h5 { font-family: 'Inter', sans-serif !important; font-weight: 700 !important; color: #ffffff !important; }
h3 { color: #38bdf8 !important; text-shadow: 0 0 15px rgba(56, 189, 248, 0.2); margin-bottom: 15px !important; }

/* 指标字体与输入框 */
[data-testid="stMetricValue"] { font-family: 'JetBrains Mono', monospace !important; font-weight: 800 !important; font-size: 1.8rem !important; color: #f8fafc !important; }
[data-testid="stMetricLabel"] { font-weight: 600 !important; color: #94a3b8 !important; font-size: 0.85rem !important; }
div[data-baseweb="input"] > div, div[data-baseweb="select"] > div { background-color: #0f172a !important; border: 1px solid rgba(56, 189, 248, 0.3) !important; border-radius: 8px !important; color: #ffffff !important; }
[data-testid="stAlert"] { border-radius: 12px !important; border: 1px solid rgba(56, 189, 248, 0.3) !important; background: rgba(15, 23, 42, 0.6) !important; backdrop-filter: blur(8px) !important; }
</style>
"""
st.markdown(PREMIUM_CSS, unsafe_allow_html=True)

@st.cache_resource
def get_yf_session():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    })
    return session

# ==============================================================================
# 3. 国际化多语言字典
# ==============================================================================
TEXTS = {
    "zh": {
        "title": "🌐 Universal Quant Terminal (旗舰融合版)",
        "subtitle": "完美融合 线性衰减DCF模型、三模型横向对比矩阵、Blume Beta 与市场情绪测谎仪",
        "market_label": "📌 步骤 1：挑选市场与热门标的",
        "market_my": "🇲🇾 马来西亚股市 (Bursa)",
        "market_us": "🇺🇸 美国股市 (US Equities)",
        "market_custom": "🔍 手动输入代码 (Custom Ticker)",
        "choose_stock": "从热门股票池中快速挑选：",
        "custom_label": "输入股票代码：",
        "custom_help": "马股请加 .KL (如: 1155.KL)；美股直接输入代码 (如: AAPL, NVDA)",
        "custom_placeholder": "例如: 1155.KL 或 AAPL",
        "quick_tag": "🔥 热门快捷测评：",
        
        "param_title": "⚙️ 步骤 2：估值核心参数设定 (小白建议保持默认)",
        "param_tip": "💡 **何时建议手动调整？**\n* **永续增长率 (g)**：当您预期该行业未来长期通胀或名义GDP增速显著高于/低于历史常态时可微调。\n* **风险溢价 (ERP)**：当市场处于极端恐慌（调高ERP）或极度狂热（调低ERP）周期时可手动修正。",
        "erp_label": "股市风险溢价要求 (Equity Risk Premium)",
        "g2_label": "长期永续通胀增长率 (Terminal Growth Rate)",
        "esg_caption": "🌿 本系统已自动结合可持续金融 (Sustainable Finance) 与 ESG 行业风险溢价进行折现率修正。",
        
        "macro_title": "[1. 动态宏观与资本成本 (DYNAMIC MACRO & COST OF CAPITAL)]",
        "macro_exp": "💡 **通俗解释 (Plain English)：** Beta 衡量股票相对于大盘的波动率。Rf 是无风险国债利率。WACC / 折现率是你作为投资者要求的最低及格线回报率。",
        "matrix_header": "📊 步骤 3：三大经典估值模型横向对比矩阵",
        "model_dcf_name": "两阶段线性衰减 DCF 模型",
        "model_ddm_name": "股息分红贴现模型 (DDM)",
        "model_pe_name": "市盈率倍数估值 (P/E Multiples)",
        "badge_recommended": "⭐ 系统主推",
        "badge_reference": "📌 辅助参考",
        "no_data_dcf": "现金流为负或数据不足",
        "no_data_ddm": "该公司不派发股息",
        "no_data_pe": "公司目前处于净亏损",
        
        "lie_title": "[4. 💡 市场情绪测谎仪 (MARKET PSYCHOLOGY / LIE DETECTOR)]",
        "lie_exp": "💡 **通俗解释 (Plain English)：** 测谎仪通过二分法反向推导，看看当前的市场价格到底在幻想这家公司未来每年增长多少。",
        "ws_title": "🏛️ 华尔街专业投行分析师共识与预期差雷达 (Wall Street & Expectation Gap)",
        "ws_mean": "投行平均目标价",
        "ws_range": "目标价区间",
        "ws_rating": "投行综合评级",
        "ws_tag": "投行机构共识",
        "gap_title": "⚡ 华尔街 vs 量化模型：深度预期差雷达 (Expectation Gap Analysis)",
        "ws_match": "✅ 模型算出的公道价与华尔街机构预测高度吻合，无重大预期差！",

        "chart_title": "[5. 📈 高级盘面与波动率回归分析]",
        "beta_desc": "📊 **Beta 收益率特征线散点分布图说明：**\n* 每个点代表过往某一周的收益率联动。红线斜率即为真实 Beta（马股对标 MSCI Malaysia ETF，美股对标 S&P 500）。\n* **$R^2$（拟合优度）补充解析**：点越密集贴近红线，说明该股越受大盘宏观主导；点越分散，说明该股具有极强的个股独立行情。",
        "glossary_title": "[6. 📖 小白通俗金融词典：这些数据代表什么？]",
        
        "g_beta_title": "##### 🎯 Beta (波动敏感度)",
        "g_beta_desc": "衡量这只股票相对于大盘是更活泼还是更稳健。Beta > 1 涨跌比大盘更猛，Beta < 1 走势更抗跌防守。",
        "g_growth_title": "##### 🚀 Growth (预期增长率)",
        "g_growth_desc": "未来公司现金流或盈利预计每年递增的比例。增长越快，股票当前公道身价就越高。",
        "g_wacc_title": "##### 🛡️ WACC / 折现率",
        "g_wacc_desc": "你买入这家公司所要求的最低年化回报门槛。风险越高、借钱越多的公司，要求越高。",
        "g_fv_title": "##### 💎 Fair Value (内在公道价)",
        "g_fv_desc": "剥离市场的短期情绪狂热与恐慌，根据公司真实资产、欠债与赚钱能力算出的厂牌公道价。",
        
        "disclaimer_title": "⚠️ 重要法律与风险免责声明",
        "disclaimer_1": "1. **非投资建议**：本系统所呈现的所有估值结果、公道价格、诊断与图表分析，仅供学术研究、个人学习交流与教学参考，不构成任何投资建议、买卖要约或财务建议。",
        "disclaimer_2": "2. **市场风险**：股票市场波动剧烈，历史数据和数学量化模型无法预知未来。公司的实际表现可能受到宏观经济、行业竞争及突发事件的影响。",
        "disclaimer_3": "3. **自主决策**：任何投资决策均应由投资者在独立调查或咨询持牌财务顾问的基础上自行做出。开发者与本系统不对依据本系统数据交易产生的任何盈亏承担法律责任。"
    },
    "en": {
        "title": "🌐 Universal Quant Terminal (Ultimate Edition)",
        "subtitle": "Integrating Fading Growth DCF, 3-Model Matrix, Blume Beta & Market Lie Detector",
        "market_label": "📌 Step 1: Select Market & Target Stock",
        "market_my": "🇲🇾 Bursa Malaysia",
        "market_us": "🇺🇸 US Equities",
        "market_custom": "🔍 Custom Ticker",
        "choose_stock": "Quick pick from popular pools:",
        "custom_label": "Enter Stock Ticker Symbol:",
        "custom_help": "For Malaysian stocks add .KL (e.g., 1155.KL); for US stocks enter ticker (e.g., AAPL, NVDA)",
        "custom_placeholder": "e.g., 1155.KL or AAPL",
        "quick_tag": "🔥 Quick Suggestions:",
        
        "param_title": "⚙️ Step 2: Core Valuation Assumptions (Defaults Recommended)",
        "param_tip": "💡 **When to adjust manually?**\n* **Terminal Growth (g)**: Adjust if you expect long-term structural inflation or GDP growth to deviate from historical norms.\n* **Equity Risk Premium (ERP)**: Adjust during extreme market cycles (higher ERP during panics, lower during bubbles).",
        "erp_label": "Equity Risk Premium (ERP)",
        "g2_label": "Terminal Growth Rate (g)",
        "esg_caption": "🌿 Sustainable Finance & ESG Sector Risk Premium automatically integrated into discount rate adjustments.",
        
        "macro_title": "[1. DYNAMIC MACRO & COST OF CAPITAL]",
        "macro_exp": "💡 **Plain English Explanation:** Beta measures stock volatility compared to the market. Rf is the benchmark government bond yield. WACC / Discount Rate is your hurdle rate / minimum required rate of return.",
        "matrix_header": "📊 Step 3: Multi-Model Valuation Matrix (DCF + DDM + P/E)",
        "model_dcf_name": "Two-Stage Fading Growth DCF",
        "model_ddm_name": "Dividend Discount Model (DDM)",
        "model_pe_name": "P/E Multiples Valuation",
        "badge_recommended": "⭐ System Recommended",
        "badge_reference": "📌 Reference",
        "no_data_dcf": "Negative or Missing Cash Flows",
        "no_data_ddm": "Company pays no dividend",
        "no_data_pe": "Company in net loss",
        
        "lie_title": "[4. 💡 MARKET PSYCHOLOGY (LIE DETECTOR)]",
        "lie_exp": "💡 **Plain English Explanation:** The lie detector uses reverse-engineering to find out what growth rate investors are currently pricing into the stock.",
        "ws_title": "🏛️ Wall Street Analyst Consensus & Expectation Gap Radar",
        "ws_mean": "Analyst Average Target Price",
        "ws_range": "Target Price Range",
        "ws_rating": "Consensus Rating",
        "ws_tag": "Institutional Consensus",
        "gap_title": "⚡ Wall Street vs. Quant Model: Expectation Gap Analysis",
        "ws_match": "✅ Your Valuation aligns tightly with Wall Street targets with minimal expectation gap!",

        "chart_title": "[5. Advanced Price Action & Regression Analysis]",
        "beta_desc": "📊 **Beta Scatter Plot Explanation:** Each dot represents past weekly return correlation. The red line slope represents the true Beta.\n* **$R^2$ Analysis**: Tight clustering indicates market-driven systemic risk; higher dispersion reflects strong independent trends.",
        "glossary_title": "[6. Beginner's Financial Glossary]",
        
        "g_beta_title": "##### 🎯 Beta (Sensitivity)",
        "g_beta_desc": "Measures stock volatility relative to the market. Beta > 1 means higher aggression, while Beta < 1 indicates defensive characteristics.",
        "g_growth_title": "##### 🚀 Expected Growth Rate",
        "g_growth_desc": "The projected annual growth rate of company cash flows or earnings. Higher growth drives higher fair value.",
        "g_wacc_title": "##### 🛡️ WACC / Discount Rate",
        "g_wacc_desc": "The minimum hurdle rate of return required by investors. Higher risks and debt levels demand a higher WACC.",
        "g_fv_title": "##### 💎 Intrinsic Fair Value",
        "g_fv_desc": "The calculated intrinsic value based on fundamental assets, liabilities, and earning power, stripping away market hype or panic.",
        
        "disclaimer_title": "⚠️ Important Legal & Risk Disclaimer",
        "disclaimer_1": "1. **Not Investment Advice**: All valuation results, fair prices, diagnostics, and charts presented herein are for academic research, personal learning, and educational purposes only. They do not constitute investment advice or financial recommendations.",
        "disclaimer_2": "2. **Market Risk**: The stock market is volatile, and historical data or quant models cannot predict the future. Company performance is subject to macroeconomic and unforeseen events.",
        "disclaimer_3": "3. **Independent Decision**: All investment decisions must be made independently by users after thorough research or consultation with licensed advisors. The developer accepts no liability for trading losses."
    }
}

# ==============================================================================
# 4. 财报稳健提取函数与核心量化引擎 (集成线性衰减 + Blume Beta + 三模型矩阵)
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

        self.name = self.info.get('longName', self.info.get('shortName', 'Unknown'))
        self.sector = self.info.get('sector', 'Unknown')
        self.industry = self.info.get('industry', 'Unknown')
        self.is_malaysia = self.ticker.endswith('.KL')
        self.currency = self.info.get('currency', 'MYR' if self.is_malaysia else 'USD')
        
        self.price = self.info.get('currentPrice', self.info.get('regularMarketPrice', self.info.get('previousClose', 0)))
        if self.price == 0.0:
            try:
                h = self.stock.history(period="5d")
                if not h.empty: self.price = float(h['Close'].dropna().iloc[-1])
            except Exception: pass

        self.shares = self.info.get('sharesOutstanding', 1) or 1
        self.bs = self.stock.balance_sheet
        self.fin = self.stock.financials
        self.cfs = self.stock.cashflow

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
            return round((0.67 * raw_beta) + (0.33 * 1.0), 2), 'Blume Adjusted'
        except Exception:
            return fallback, 'System Default'

    def run_valuation(self, erp, terminal_g):
        self.beta, self.beta_type = self.compute_blume_beta()
        self.rf = 0.0385 if self.is_malaysia else 0.042
        self.esg_adj, self.esg_tag = self.get_esg_adjustment()
        
        self.ke = self.rf + (self.beta * erp) + self.esg_adj
        self.tax = 0.24 if self.is_malaysia else 0.21
        
        market_cap = self.price * self.shares
        total_cap = market_cap + self.debt
        w_e = market_cap / total_cap if total_cap > 0 else 1
        w_d = self.debt / total_cap if total_cap > 0 else 0
        
        int_exp = abs(self.info.get('interestExpense', 0) or get_fin_metric(self.fin, 'Interest Expense'))
        kd = min((int_exp / self.debt) if self.debt > 0 else 0.05, 0.10)
        self.wacc = (w_e * self.ke) + (w_d * kd * (1 - self.tax))
        self.wacc = max(self.wacc, terminal_g + 0.02)

        # 自由现金流获取
        raw_fcf = self.info.get('freeCashflow', 0)
        if raw_fcf <= 0: raw_fcf = get_fin_metric(self.cfs, 'Free Cash Flow')
        if raw_fcf <= 0:
            ocf = get_fin_metric(self.cfs, 'Operating Cash Flow')
            capex = abs(get_fin_metric(self.cfs, 'Capital Expenditure'))
            if ocf > capex: raw_fcf = ocf - capex

        self.cf = raw_fcf
        self.g1 = min(max(self.info.get('earningsGrowth', 0) or 0.08, 0.03), 0.25)
        self.g2 = terminal_g
        self.horizon = 10 if self.sector in ['Technology', 'Communication Services'] else 5

        # 1. 计算两阶段线性衰减 DCF
        self.val_dcf = self.calculate_dcf_pv(self.g1)

        # 2. 计算 DDM (股息折现)
        div = self.info.get('dividendRate') or self.info.get('trailingAnnualDividendRate') or 0.0
        self.val_ddm = None
        if div > 0:
            g_ddm = min(self.g2, self.ke - 0.01)
            self.val_ddm = (div * (1.0 + g_ddm)) / (self.ke - g_ddm) if self.ke > g_ddm else 0.0

        # 3. 计算 P/E 倍数估值
        eps = self.info.get('trailingEps') or self.info.get('forwardEps') or 0.0
        if eps <= 0:
            net_inc = get_fin_metric(self.fin, 'Net Income')
            if net_inc > 0 and self.shares > 0: eps = net_inc / self.shares
        
        self.val_pe = None
        if eps > 0:
            if self.sector in ['Technology', 'Communication Services']: bench_pe = 24.0
            elif self.sector in ['Financial Services']: bench_pe = 11.5
            elif self.sector in ['Utilities', 'Real Estate']: bench_pe = 14.0
            else: bench_pe = 16.0
            self.val_pe = eps * bench_pe

        # 确定推荐的主模型
        if self.sector in ['Financial Services', 'Real Estate', 'Utilities'] and self.val_ddm is not None and self.val_ddm > 0:
            self.primary_name = 'DDM'
            self.primary_val = self.val_ddm
        elif self.val_dcf is not None and self.val_dcf > 0:
            self.primary_name = 'DCF'
            self.primary_val = self.val_dcf
        elif self.val_pe is not None and self.val_pe > 0:
            self.primary_name = 'PE'
            self.primary_val = self.val_pe
        else:
            self.primary_name = 'DCF'
            self.primary_val = self.val_dcf if self.val_dcf else 0.0

        implied_g = self.find_implied_growth()
        return self.primary_val, implied_g

    def calculate_dcf_pv(self, test_g):
        if self.cf <= 0 or self.wacc <= self.g2: return None
        pv1 = 0
        curr_cf = self.cf
        
        # 💡 机构级核心防护：线性衰减增长率，彻底根治复利失真 Bug
        growth_rates = np.linspace(test_g, self.g2, self.horizon)
        
        for y in range(1, self.horizon + 1):
            annual_g = growth_rates[y - 1]
            curr_cf *= (1 + annual_g)
            pv1 += curr_cf / ((1 + self.wacc) ** y)
        
        pv_tv = (curr_cf * (1 + self.g2)) / (self.wacc - self.g2) / ((1 + self.wacc) ** self.horizon)
        total_pv = pv1 + pv_tv
        equity_val = total_pv + self.cash - self.debt
        return equity_val / self.shares if self.shares > 0 else 0

    def find_implied_growth(self):
        if self.price <= 0 or self.cf <= 0: return None
        low, high = -0.50, 2.00
        for _ in range(50):
            mid = (low + high) / 2
            res = self.calculate_dcf_pv(mid)
            if res is None: break
            if res < self.price: low = mid
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
    fig.update_layout(xaxis_rangeslider_visible=False, height=350, margin=dict(l=0, r=0, t=10, b=0), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#94a3b8'), xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'), yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'), legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01))
    return fig

def draw_beta_scatter(engine):
    if engine.scatter_data is None: return None
    stock_ret, market_ret = engine.scatter_data.iloc[:, 0], engine.scatter_data.iloc[:, 1]
    corr = np.corrcoef(stock_ret, market_ret)[0, 1]
    r_squared = corr ** 2 if not np.isnan(corr) else 0.0

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=market_ret, y=stock_ret, mode='markers', marker=dict(color='#38bdf8', size=7, opacity=0.8), name='Returns'))
    x_range = np.linspace(market_ret.min(), market_ret.max(), 100)
    fig.add_trace(go.Scatter(x=x_range, y=engine.beta * x_range, mode='lines', line=dict(color='#ef4444', width=2), name='Beta Regression'))
    
    fig.update_layout(
        title=dict(text=f"Beta Regression (Beta = {engine.beta:.2f} | R² = {r_squared:.2f})", font=dict(color='#ffffff')),
        xaxis_title="Market Benchmark (MSCI Malaysia / S&P 500)", 
        yaxis_title="Stock Return (%)", 
        plot_bgcolor='rgba(0,0,0,0)', 
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#94a3b8'),
        xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
        showlegend=False, height=330, margin=dict(l=0, r=0, t=35, b=0)
    )
    return fig

# ==============================================================================
# 6. 主程序与融合 UI 渲染
# ==============================================================================
def main():
    col_title, col_lang = st.columns([3, 1.2])
    with col_lang:
        selected_lang = st.selectbox("🌐 Language / 语言", options=["中文", "English"], index=0)
        lang_key = "zh" if selected_lang == "中文" else "en"
        T = TEXTS[lang_key]

    with col_title:
        st.markdown(f"<h1 style='color: #ffffff; font-weight: 800; font-size: 1.9rem;'>{T['title']}</h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: #38bdf8; font-weight: 600; font-size: 13.5px; margin-top: -5px;'>{T['subtitle']}</p>", unsafe_allow_html=True)

    st.write("---")

    # 步骤 1：市场与股票挑选面板（结合了你朋友的直观下拉与热门快捷选择）
    st.markdown(f"#### {T['market_label']}")
    
    MY_STOCKS = [
        ("1155.KL", "Maybank (马来亚银行 - 金融分红王)"),
        ("1295.KL", "Public Bank (大众银行 - 稳健金融巨头)"),
        ("5347.KL", "Tenaga Nasional (国家能源 - 公用事业基建)"),
        ("0166.KL", "Inari Amertron (益纳利 - 科技半导体)"),
        ("5211.KL", "Sunway (双威集团 - 综合地产医疗)"),
    ]
    US_STOCKS = [
        ("NVDA", "NVIDIA Corporation (英伟达 - 全球 AI 算力芯片)"),
        ("AAPL", "Apple Inc. (苹果公司 - 消费电子生态)"),
        ("TSLA", "Tesla Inc. (特斯拉 - 电动车与机器人)"),
        ("MSFT", "Microsoft (微软 - 企业软件与云)"),
        ("AMZN", "Amazon.com (亚马逊 - 电商与 AWS)"),
    ]

    my_opts = [f"{t} | {name}" for t, name in MY_STOCKS]
    us_opts = [f"{t} | {name}" for t, name in US_STOCKS]

    if "active_ticker" not in st.session_state: st.session_state.active_ticker = "NVDA"
    if "active_market" not in st.session_state: st.session_state.active_market = "US"

    def select_quick(t, m):
        st.session_state.active_ticker = t
        st.session_state.active_market = m

    st.write(T['quick_tag'])
    q1, q2, q3, q4 = st.columns(4)
    q1.button("🇺🇸 NVDA", on_click=select_quick, args=("NVDA", "US"), use_container_width=True)
    q2.button("🇺🇸 AAPL", on_click=select_quick, args=("AAPL", "US"), use_container_width=True)
    q3.button("🇲🇾 1155.KL (Maybank)", on_click=select_quick, args=("1155.KL", "MY"), use_container_width=True)
    q4.button("🇲🇾 5347.KL (Tenaga)", on_click=select_quick, args=("5347.KL", "MY"), use_container_width=True)

    market_mode = st.radio("Market", options=["MY", "US", "CUSTOM"], format_func=lambda k: {"MY": T['market_my'], "US": T['market_us'], "CUSTOM": T['market_custom']}[k], horizontal=True, label_visibility="collapsed")

    if market_mode == "MY":
        sel_my = st.selectbox(T['choose_stock'], options=my_opts)
        current_ticker = sel_my.split(" | ")[0].strip()
    elif market_mode == "US":
        sel_us = st.selectbox(T['choose_stock'], options=us_opts)
        current_ticker = sel_us.split(" | ")[0].strip()
    else:
        current_ticker = st.text_input(T['custom_label'], value="NVDA", placeholder=T['custom_placeholder'], help=T['custom_help']).strip().upper()

    # 步骤 2：核心参数折叠抽屉
    with st.expander(T['param_title'], expanded=False):
        st.info(T['param_tip'])
        c_erp, c_g2 = st.columns(2)
        custom_erp = c_erp.slider(T['erp_label'], 4.0, 7.0, 5.0, 0.1) / 100
        custom_g2 = c_g2.slider(T['g2_label'], 1.0, 3.5, 2.0, 0.1) / 100
    st.caption(T['esg_caption'])

    if current_ticker:
        with st.spinner("Analyzing quantitative model..."):
            engine = UniversalQuantEngine(current_ticker)
            val, implied_g = engine.run_valuation(custom_erp, custom_g2)

            st.markdown(f"<h3 style='margin-top: 25px;'>🏢 {engine.name} ({engine.ticker}) <span style='font-size:14px; color:#94a3b8;'>| Sector: {engine.sector}</span></h3>", unsafe_allow_html=True)

            # [1. 宏观与资本成本卡片]
            with st.container(border=True):
                st.markdown(f"**{T['macro_title']}**")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Beta Risk", f"{engine.beta:.2f}", delta=engine.beta_type, delta_color="off")
                c2.metric("Rf Rate", f"{engine.rf * 100:.2f}%")
                c3.metric("WACC", f"{engine.wacc * 100:.2f}%", engine.esg_tag)
                c4.metric("Current Price", f"{engine.currency} {engine.price:.2f}")
                st.caption(T['macro_exp'])

            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

            # [2. 三大估值模型横向对比矩阵（融合你朋友矩阵的视觉与你引擎的准确度）]
            st.markdown(f"#### {T['matrix_header']}")
            m_col1, m_col2, m_col3 = st.columns(3)

            def render_matrix_card(title, model_val, price, is_rec, currency, note, empty_msg):
                badge_text = T["badge_recommended"] if is_rec else T["badge_reference"]
                card_border = "#10b981" if is_rec else "#334155"
                if model_val and model_val > 0:
                    val_str = f"{currency} {model_val:.2f}"
                    diff = (model_val - price) / price * 100.0 if price > 0 else 0
                    diff_sign = "+" if diff > 0 else ""
                    pill_color = "#22c55e" if diff > 0 else "#f43f5e"
                    status_html = f"<div style='color: {pill_color}; font-weight: 700; font-size: 13px;'>{diff_sign}{diff:.1f}% vs 市价</div>"
                else:
                    val_str = "N/A"
                    status_html = f"<div style='color: #f87171; font-size: 12px;'>⚠️ {empty_msg}</div>"

                return f"""
                <div style="background: linear-gradient(135deg, rgba(30, 41, 59, 0.9) 0%, rgba(15, 23, 42, 0.95) 100%); border: 1.5px solid {card_border}; border-radius: 12px; padding: 18px; min-height: 175px; display: flex; flex-direction: column; justify-content: space-between;">
                    <div>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <span style="font-size: 14px; font-weight: 700; color: #f8fafc;">{title}</span>
                            <span style="background: rgba(56, 189, 248, 0.15); color: #38bdf8; font-size: 10.5px; font-weight: 700; padding: 2px 8px; border-radius: 12px;">{badge_text}</span>
                        </div>
                        <div style="font-family: 'JetBrains Mono', monospace; font-size: 26px; font-weight: 800; color: #ffffff; margin: 4px 0;">{val_str}</div>
                        <div>{status_html}</div>
                    </div>
                    <div style="color: #94a3b8; font-size: 11.5px; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 8px; margin-top: 8px;">💡 {note}</div>
                </div>
                """

            with m_col1:
                st.markdown(render_matrix_card(T["model_dcf_name"], engine.val_dcf, engine.price, engine.primary_name == 'DCF', engine.currency, "基于线性衰减自由现金流与 WACC 资本成本折现。", T["no_data_dcf"]), unsafe_allow_html=True)
            with m_col2:
                st.markdown(render_matrix_card(T["model_ddm_name"], engine.val_ddm, engine.price, engine.primary_name == 'DDM', engine.currency, "基于历史股息分红及永续增长率折现。", T["no_data_ddm"]), unsafe_allow_html=True)
            with m_col3:
                st.markdown(render_matrix_card(T["model_pe_name"], engine.val_pe, engine.price, engine.primary_name == 'PE', engine.currency, "基于每股收益 (EPS) 乘以行业合理市盈率倍数。", T["no_data_pe"]), unsafe_allow_html=True)

            st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)

            # [3. 市场情绪测谎仪与 AI 诊断]
            col_lie, col_ai = st.columns(2)
            with col_lie:
                with st.container(border=True):
                    st.markdown(f"**{T['lie_title']}**")
                    implied_g_str = f"{implied_g * 100:.2f}%" if implied_g is not None else "N/A"
                    st.warning(f"To justify the current price of **{engine.price:.2f}**, the market implies a Growth Rate of **{implied_g_str} per year for {engine.horizon} years**.")
                    if implied_g is not None:
                        if implied_g > 0.40: diag = "-> **Diagnosis: EXTREME HYPE (Bubble Territory).**"
                        elif implied_g < 0.0: diag = "-> **Diagnosis: EXTREME PESSIMISM.**"
                        else: diag = "-> **Diagnosis: MODERATE EXPECTATIONS.**"
                        st.write(diag)
                    st.caption(T['lie_exp'])

            with col_ai:
                with st.container(border=True):
                    st.markdown(f"**🤖 智能估值综合裁决 (Quantitative Verdict)**")
                    st.write(f"- **系统精选基准模型:** {engine.primary_name}")
                    st.write(f"- **内在公道价值 (Intrinsic Fair Value):** `{engine.currency} {engine.primary_val:.2f}`")
                    if engine.price > 0 and engine.primary_val > 0:
                        ratio = engine.price / engine.primary_val
                        if ratio < 0.8:
                            st.success("-> **Verdict:** 🟢 严重低估 (具有极佳安全边际，可积极关注)")
                        elif ratio > 1.2:
                            st.error("-> **Verdict:** 🔴 明显高估 (市价已严重透支未来预期)")
                        else:
                            st.info("-> **Verdict:** 🟡 估值合理 (市场定价理性均衡)")

            # [4. 华尔街预期差雷达（仅美股生效）]
            if not engine.is_malaysia:
                target_mean = engine.info.get('targetMeanPrice')
                num_analysts = engine.info.get('numberOfAnalystOpinions', 0)
                if target_mean and num_analysts > 0:
                    st.markdown(f"<br><h3>{T['ws_title']}</h3>", unsafe_allow_html=True)
                    w1, w2, w3 = st.columns(3)
                    w1.metric(T['ws_mean'], f"${target_mean:.2f}", f"{num_analysts} Analysts")
                    w2.metric(T['ws_range'], f"${engine.info.get('targetLowPrice', 0):.2f} ~ ${engine.info.get('targetHighPrice', 0):.2f}")
                    w3.metric(T['ws_rating'], str(engine.info.get('recommendationKey', 'N/A')).upper())

            # [5. 盘面与波动率回归分析]
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
                    st.caption(T['beta_desc'])

            # [6. 小白金融词典]
            st.markdown(f"### {T['glossary_title']}")
            g1, g2, g3, g4 = st.columns(4)
            with g1:
                with st.container(border=True):
                    st.markdown(T['g_beta_title'])
                    st.caption(T['g_beta_desc'])
            with g2:
                with st.container(border=True):
                    st.markdown(T['g_growth_title'])
                    st.caption(T['g_growth_desc'])
            with g3:
                with st.container(border=True):
                    st.markdown(T['g_wacc_title'])
                    st.caption(T['g_wacc_desc'])
            with g4:
                with st.container(border=True):
                    st.markdown(T['g_fv_title'])
                    st.caption(T['g_fv_desc'])

    # 7. 底部免责声明
    st.markdown("---")
    with st.container(border=True):
        st.markdown(f"### {T['disclaimer_title']}")
        st.markdown(T['disclaimer_1'])
        st.markdown(T['disclaimer_2'])
        st.markdown(T['disclaimer_3'])

if __name__ == '__main__':
    main()
