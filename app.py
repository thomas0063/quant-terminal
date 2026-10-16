import datetime
import numpy as np
import pandas as pd
import requests
import yfinance as yf
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import scipy.stats as stats

# ==============================================================================
# 1. 页面基本配置与高级 CSS 视觉引擎 (Bento Box + Tabs)
# ==============================================================================
st.set_page_config(page_title="Ultimate Quant & PE Terminal V9.7", page_icon="💹", layout="wide", initial_sidebar_state="collapsed")

PREMIUM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

.stApp {
    background: radial-gradient(circle at 50% 0%, #1e293b 0%, #0f172a 60%, #090d16 100%) !important;
    font-family: 'Inter', -apple-system, sans-serif !important;
    color: #f8fafc !important;
}
.block-container { padding-top: 2rem !important; max-width: 1400px !important; }
header[data-testid="stHeader"] { background: transparent !important; }

.stTabs [data-baseweb="tab-list"] {
    gap: 8px; background-color: rgba(15, 23, 42, 0.6); border-radius: 12px; padding: 8px; border: 1px solid rgba(56, 189, 248, 0.2);
}
.stTabs [data-baseweb="tab"] {
    color: #94a3b8 !important; font-weight: 600 !important; border-radius: 8px !important; padding: 10px 14px !important; font-size: 12px !important; transition: all 0.3s ease;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #38bdf8 0%, #0284c7 100%) !important; color: #ffffff !important; box-shadow: 0 4px 15px rgba(56, 189, 248, 0.4);
}

[data-testid="column"] > div { height: 100% !important; }
[data-testid="stVerticalBlockBorderWrapper"] {
    background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.85) 100%) !important;
    border: 1px solid rgba(56, 189, 248, 0.3) !important; border-radius: 14px !important;
    box-shadow: 0 8px 24px -4px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.08) !important;
    backdrop-filter: blur(12px) !important; transition: all 0.3s ease !important; padding: 16px 20px !important;
    height: 100% !important; display: flex; flex-direction: column; justify-content: space-between;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border-color: #38bdf8 !important; box-shadow: 0 10px 30px -4px rgba(56, 189, 248, 0.3) !important; transform: translateY(-2px);
}

.stButton > button {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%) !important; color: #38bdf8 !important;
    border: 1px solid rgba(56, 189, 248, 0.3) !important; border-radius: 8px !important; font-weight: 600 !important; font-size: 13px !important; transition: all 0.25s ease !important;
}
.stButton > button:hover {
    background: rgba(56, 189, 248, 0.15) !important; color: #ffffff !important; border-color: #38bdf8 !important; box-shadow: 0 6px 18px -2px rgba(56, 189, 248, 0.4) !important; transform: translateY(-2px);
}

label { color: #cbd5e1 !important; font-weight: 500 !important; }
p { color: #e2e8f0 !important; }
h1, h2, h3, h4, h5 { font-family: 'Inter', sans-serif !important; font-weight: 700 !important; color: #ffffff !important; }
h3 { color: #38bdf8 !important; text-shadow: 0 0 15px rgba(56, 189, 248, 0.2); margin-bottom: 15px !important; }
[data-testid="stMetricValue"] { font-family: 'JetBrains Mono', monospace !important; font-weight: 800 !important; font-size: 1.8rem !important; color: #f8fafc !important; }
[data-testid="stMetricLabel"] { font-weight: 600 !important; color: #94a3b8 !important; font-size: 0.85rem !important; }
div[data-baseweb="input"] > div, div[data-baseweb="select"] > div { background-color: #0f172a !important; border: 1px solid rgba(56, 189, 248, 0.3) !important; border-radius: 8px !important; color: #ffffff !important; }
</style>
"""
st.markdown(PREMIUM_CSS, unsafe_allow_html=True)

# ==============================================================================
# 2. 国际化多语言字典
# ==============================================================================
TEXTS = {
    "zh": {
        "title": "🌐 智能量化与衍生品金融终端 (V9.7 旗舰全功能版)",
        "subtitle": "完美融合 线性衰减DCF、凯利公式、最大回撤、几何布朗运动(GBM)、协整配对、LBO、有效前沿与智能期权顾问",
        "quick_tag": "🔥 热门快捷测评：",
        "input_label": "输入股票代码 (如 1155.KL, NVDA, AAPL)：",
        
        "param_title": "⚙️ 步骤 2：估值核心参数设定 (可保持默认) 👈 (小白用户建议直接保持默认，无需改动)",
        "param_tip": "💡 **何时建议手动调整？**\n* **永续增长率 (g)**：当您预期该行业未来长期通胀或名义GDP增速显著高于/低于历史常态时可微调。\n* **风险溢价 (ERP)**：当市场处于极端恐慌（调高ERP）或极度狂热（调低ERP）周期时可手动修正。",
        "erp_label": "股市风险溢价要求 (Equity Risk Premium)",
        "g2_label": "长期永续通胀增长率 (Terminal Growth Rate)",
        "esg_caption": "🌿 本系统已自动结合可持续金融 (Sustainable Finance) 与 ESG 行业风险溢价进行折现率修正。",
        
        "macro_title": "[1. 动态宏观与资本成本 (DYNAMIC MACRO & COST OF CAPITAL - CAPM)]",
        "macro_exp": "💡 **通俗解释 (Plain English)：** Beta 衡量股票相对于大盘的波动率（回归点斜率）。Rf 是无风险国债利率。WACC / 折现率是你作为投资者要求的最低及格线回报率。",
        
        "matrix_header": "[2. 三大经典估值模型横向对比矩阵 (DCF + DDM + P/E)]",
        "model_dcf_name": "两阶段线性衰减 DCF 模型",
        "model_ddm_name": "股息分红贴现模型 (DDM)",
        "model_pe_name": "市盈率倍数估值 (P/E Multiples)",
        "badge_recommended": "⭐ 系统主推",
        "badge_reference": "📌 辅助参考",
        "no_data_dcf": "现金流为负或数据不足",
        "no_data_ddm": "该公司不派发股息",
        "no_data_pe": "公司目前处于净亏损",
        "vs_market": "vs 市价",
        "note_dcf": "基于线性衰减自由现金流与 WACC 资本成本折现。",
        "note_ddm": "基于历史股息分红及永续增长率折现。",
        "note_pe": "基于每股收益 (EPS) 乘以行业合理市盈率倍数。",
        
        "price": "当前市场价格",
        "fair_val": "内在公道估值 (衰减后)",
        "fair_val_desc": "💡 **关于【内在公道估值 (衰减后)】的通俗解释**：剥离短期市场狂热与恐慌炒作，根据公司真实赚钱能力算出的保守身价。**“衰减后”**代表模型让高速增长逐年平稳递减，彻底防止科技巨头复利失真。",
        "safe_buy": "20% 安全边际买点",

        "heat_title": "[3. 🌡️ 核心参数敏感性分析矩阵与凯利公式仓位 (DCF HEATMAP & KELLY CRITERION)]",
        "heat_desc": "💡 **图表说明**：投行通常不给出单一绝对估值。纵轴代表不同的**折现率 (WACC)**，横轴代表**永续增长率 (g)**。矩阵中的数值为对应假设下的内在公道价。<br>👉 <span style='color:#10b981;'>**绿色区域**</span> 代表该参数下当前市价被低估 (具备安全边际)；<span style='color:#ef4444;'>**红色区域**</span> 代表高估；深灰色接近当前市价。",
        
        "lie_title": "[4. 💡 市场情绪测谎仪 (MARKET PSYCHOLOGY / LIE DETECTOR)]",
        "lie_exp": "💡 **通俗解释 (Plain English)：** 测谎仪通过二分法反向推导，看看当前的市场价格到底在幻想这家公司未来每年增长多少。",
        "ai_title": "[5. 🤖 双视角 AI 投资顾问 (DUAL-PERSPECTIVE AI ADVISORY)]",
        "inc_title": "🔸 视角 A：保守派收息策略 (Conservative Income)",
        "cap_title": "🔹 视角 B：进取派资本增值 (Capital Appreciation)",
        "exec_title": "[6. 🎯 最终投资评级与执行摘要 (EXECUTIVE SUMMARY)]",
        "rating_explain": "ℹ️ *学术释疑：‘市场情绪理性’代表投资者没有盲目炒作泡沫，但给出 ‘SELL’ 评级是因为当前市价高于内在公道价（缺乏安全边际）。即：好公司不等于好价格。*",
        
        "plain_title": "[7. 🗣️ 小白通俗翻译器 (PLAIN ENGLISH TRANSLATOR)]",
        "fx_title": "[8. 💱 跨境汇率风险提示 (CROSS-BORDER FX RISK)]",
        "fx_content": "- **提示：** 此乃美元计价资产，请注意美元兑马币 (USD/MYR) 的汇率波动风险。",
        
        "ws_title": "🏛️ [9. 华尔街投行分析师共识与预期差雷达]",
        "ws_mean": "投行平均目标价",
        "ws_range": "目标价区间",
        "ws_rating": "投行综合评级",
        "ws_tag": "投行机构共识",
        "gap_title": "⚡ 华尔街 vs 量化模型：深度预期差雷达 (Expectation Gap Analysis)",
        "gap_line1": "量化内在公允价 (Model Fair Value)",
        "gap_line2": "华尔街平均目标价 (Wall Street Target)",
        "gap_line3": "预期差偏离度 (Divergence Gap)",
        "gap_desc_high": "华尔街目标价比模型估值高出",
        "gap_alert_high": "🚨 **【预期差警示 / 情绪溢价驱动】**：华尔街目标价远高于量化模型底线。当前市价已透支部分未来，长线价值投资者需警惕高估值回撤。",
        "gap_alert_low": "🔥 **【深度价值 / 逆向左侧契机】**：量化模型算出的基本面造血价值高于华尔街卖方预期，属于潜在的“捡烟蒂”布局区。",
        "ws_match": "✅ 模型算出的公道价与华尔街机构预测高度吻合，无重大预期差！",

        "chart_title": "[10. 📈 高级盘面、对数收益、最大回撤 (MDD) 与 Beta 回归分析]",
        "beta_desc": "📊 **Beta 收益率特征线散点分布图说明：**\n* 每个点代表过往某一周的收益率联动。红线斜率即为真实 Beta（Cov/Var）。\n* **$R^2$（拟合优度）补充解析**：点越密集贴近红线，说明该股越受大盘宏观主导（如银行股）；点越分散，说明该股具有极强的个股独立行情（如科技股）。",
        "glossary_title": "[11. 📖 小白通俗金融词典：这些数据代表什么？]",
        
        "g_beta_title": "##### 🎯 Beta (波动敏感度)",
        "g_beta_desc": "衡量这只股票相对于大盘是更活泼还是更稳健。Beta > 1 涨跌比大盘更猛，Beta < 1 走势更抗跌防守。",
        "g_growth_title": "##### 🚀 Growth (预期增长率)",
        "g_growth_desc": "未来公司现金流或盈利预计每年递增的比例。增长越快，股票当前公道身价就越高。",
        "g_wacc_title": "##### 🛡️ WACC / 折现率",
        "g_wacc_desc": "你买入这家公司所要求的最低年化回报门槛。风险越高、借钱越多的公司，要求越高。",
        "g_fv_title": "##### 💎 Fair Value (内在公道价)",
        "g_fv_desc": "剥离市场的短期情绪狂热与恐慌，根据公司真实资产、欠债与赚钱能力算出的厂牌公道价。",
        
        "disclaimer_title": "[12. ⚠️ 重要法律与风险免责声明]",
        "disclaimer_1": "1. **非投资建议**：本系统所呈现的所有估值结果、公道价格、诊断与图表分析，仅供学术研究、个人学习交流与教学参考，不构成任何投资建议、买卖要约或财务建议。",
        "disclaimer_2": "2. **市场风险**：股票市场波动剧烈，历史数据和数学量化模型无法预知未来。公司的实际表现可能受到宏观经济、行业竞争及突发事件的影响。",
        "disclaimer_3": "3. **自主决策**：任何投资决策均应由投资者在独立调查或咨询持牌财务顾问的基础上自行做出。开发者与本系统不对依据本系统数据交易产生的任何盈亏承担法律责任."
    },
    "en": {
        "title": "🌐 Universal Quant & Derivatives Terminal (Flagship V9.7)",
        "subtitle": "Integrating Fading DCF, Kelly Criterion, Max Drawdown, GBM Paths, Cointegration Spread, LBO, Efficient Frontier & Options",
        "quick_tag": "🔥 Quick Select:",
        "input_label": "Enter Stock Ticker (e.g., 1155.KL, NVDA, AAPL):",
        
        "param_title": "⚙️ Step 2: Macro & Valuation Parameters (Defaults Recommended) 👈 (Keep default unless necessary)",
        "param_tip": "💡 **When to adjust manually?**\n* **Terminal Growth (g)**: Adjust if you expect long-term structural inflation or GDP growth to deviate from historical norms.\n* **Equity Risk Premium (ERP)**: Adjust during extreme market cycles (higher ERP during panics, lower during bubbles).",
        "erp_label": "Equity Risk Premium (ERP)",
        "g2_label": "Terminal Growth Rate (g)",
        "esg_caption": "🌿 Sustainable Finance & ESG Sector Risk Premium automatically integrated into discount rate adjustments.",
        
        "macro_title": "[1. DYNAMIC MACRO & COST OF CAPITAL (CAPM)]",
        "macro_exp": "💡 **Plain English Explanation:** Beta measures stock volatility compared to the market (slope of regression). Rf is the benchmark government bond yield. WACC / Discount Rate is your hurdle rate.",
        
        "matrix_header": "[2. Multi-Model Valuation Matrix (DCF + DDM + P/E)]",
        "model_dcf_name": "Two-Stage Fading Growth DCF",
        "model_ddm_name": "Dividend Discount Model (DDM)",
        "model_pe_name": "P/E Multiples Valuation",
        "badge_recommended": "⭐ System Recommended",
        "badge_reference": "📌 Reference",
        "no_data_dcf": "Negative or Missing Cash Flows",
        "no_data_ddm": "Company pays no dividend",
        "no_data_pe": "Company in net loss",
        "vs_market": "vs Market",
        "note_dcf": "Based on linear fading FCF and WACC discount rate.",
        "note_ddm": "Based on historical dividends and terminal growth.",
        "note_pe": "Based on EPS multiplied by benchmark P/E multiples.",
        
        "price": "Current Market Price",
        "fair_val": "Intrinsic Fair Value (Faded)",
        "fair_val_desc": "💡 **Explanation of [Intrinsic Fair Value (Faded)]**: Strips away short-term market hype and panic to reveal true fundamental worth. **'Faded'** means growth rates smoothly decay over time to prevent multi-year compounding errors, making valuation conservative and robust.",
        "safe_buy": "Safe Buy Target (20% MoS)",

        "heat_title": "[3. 🌡️ DCF SENSITIVITY HEATMAP & KELLY CRITERION SIZING]",
        "heat_desc": "💡 **How to read this?** Institutional models do not rely on a single absolute value. The Y-axis represents different **Discount Rates (WACC)**, and the X-axis represents **Terminal Growth (g)**. <br>👉 <span style='color:#10b981;'>**Green zones**</span> indicate the stock is undervalued at those parameters; <span style='color:#ef4444;'>**Red zones**</span> indicate overvalued; Dark grey represents values close to the current market price.",
        
        "lie_title": "[4. 💡 MARKET PSYCHOLOGY (LIE DETECTOR)]",
        "lie_exp": "💡 **Plain English Explanation:** The lie detector uses reverse-engineering to find out what growth rate investors are currently pricing into the stock.",
        "ai_title": "[5. 🤖 DUAL-PERSPECTIVE AI ADVISORY]",
        "inc_title": "🔸 Perspective A: Conservative Income",
        "cap_title": "🔹 Perspective B: Capital Appreciation",
        "exec_title": "[6. 🎯 FINAL EXECUTIVE SUMMARY & RATING]",
        "rating_explain": "ℹ️ *Academic Note: 'Rational Market Sentiment' means investors are not irrationally hyping the stock, but a 'SELL' rating is triggered strictly because the market price exceeds the intrinsic value (Lack of Margin of Safety). Good company ≠ Good price.*",
        
        "plain_title": "[7. 🗣️ PLAIN ENGLISH TRANSLATOR]",
        "fx_title": "[8. 💱 CROSS-BORDER FX RISK ADVISORY]",
        "fx_content": "- **Note:** USD-denominated asset; monitor USD/MYR exchange rate fluctuations.",
        
        "ws_title": "🏛️ [9. Wall Street Analyst Consensus & Expectation Gap Radar]",
        "ws_mean": "Analyst Average Target Price",
        "ws_range": "Target Price Range",
        "ws_rating": "Consensus Rating",
        "ws_tag": "Institutional Consensus",
        "gap_title": "⚡ Wall Street vs. Quant Model: Expectation Gap Analysis",
        "gap_line1": "Model Fair Value",
        "gap_line2": "Wall Street Target Mean",
        "gap_line3": "Divergence Gap",
        "gap_desc_high": "Wall Street target is higher than model value by",
        "gap_alert_high": "🚨 **[Expectation Gap Warning / Sentiment Premium]**: Wall Street targets far exceed the quant model. Current prices have factored in future growth; long-term value investors should remain cautious.",
        "gap_alert_low": "🔥 **[Deep Value / Contrarian Opportunity]**: Quant model fundamental cash flow value exceeds Wall Street sell-side expectations, presenting a potential deep-value entry.",
        "ws_match": "✅ Your Valuation aligns tightly with Wall Street targets with minimal expectation gap!",

        "chart_title": "[10. Advanced Price Action, Log Return, Max Drawdown (MDD) & Beta]",
        "beta_desc": "📊 **Beta Scatter Plot Explanation:** Each dot represents past weekly return correlation. The red line slope represents the true Beta (Cov/Var).\n* **$R^2$ Analysis**: Tight clustering indicates market-driven systemic risk; higher dispersion reflects strong independent trends.",
        "glossary_title": "[11. Beginner's Financial Glossary]",
        
        "g_beta_title": "##### 🎯 Beta (Sensitivity)",
        "g_beta_desc": "Measures stock volatility relative to the market. Beta > 1 means higher aggression, while Beta < 1 indicates defensive characteristics.",
        "g_growth_title": "##### 🚀 Expected Growth Rate",
        "g_growth_desc": "The projected annual growth rate of company cash flows or earnings. Higher growth drives higher fair value.",
        "g_wacc_title": "##### 🛡️ WACC / Discount Rate",
        "g_wacc_desc": "The minimum hurdle rate of return required by investors. Higher risks and debt levels demand a higher WACC.",
        "g_fv_title": "##### 💎 Intrinsic Fair Value",
        "g_fv_desc": "The calculated intrinsic value based on fundamental assets, liabilities, and earning power, stripping away market hype or panic.",
        
        "disclaimer_title": "[12. ⚠️ Important Legal & Risk Disclaimer]",
        "disclaimer_1": "1. **Not Investment Advice**: All valuation results, fair prices, diagnostics, and charts presented herein are for academic research, personal learning, and educational purposes only. They do not constitute investment advice or financial recommendations.",
        "disclaimer_2": "2. **Market Risk**: The stock market is volatile, and historical data or quant models cannot predict the future. Company performance is subject to macroeconomic and unforeseen events.",
        "disclaimer_3": "3. **Independent Decision**: All investment decisions must be made independently by users after thorough research or consultation with licensed advisors. The developer accepts no liability for trading losses."
    }
}

def get_fin_metric(df, keyword, default=0.0):
    if df is None or df.empty: return default
    try:
        matches = df[df.index.str.contains(keyword, case=False, na=False)]
        if not matches.empty:
            val = matches.iloc[0, 0]
            return float(val) if pd.notna(val) else default
    except Exception: pass
    return default

# 🌟 缓存数据读取层：防止 Streamlit Cloud 频繁请求被 Yahoo 封禁 IP
@st.cache_data(ttl=1800, show_spinner=False)
def fetch_cached_ticker_data(ticker_sym):
    stock = yf.Ticker(ticker_sym)
    info = {}
    try:
        info = stock.info or {}
    except Exception:
        info = {}
    
    hist_1y = pd.DataFrame()
    try:
        hist_1y = stock.history(period="1y", interval="1d")
    except Exception:
        pass

    bs, fin, cfs = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    try:
        bs = stock.balance_sheet
        fin = stock.financials
        cfs = stock.cashflow
    except Exception:
        pass

    return info, hist_1y, bs, fin, cfs

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_cached_history(ticker_sym, period="3y", interval="1mo"):
    try:
        return yf.Ticker(ticker_sym).history(period=period, interval=interval)
    except Exception:
        return pd.DataFrame()

# ==============================================================================
# 3. 核心硬核量化引擎 (集成 10 大量化公式、NWC、折旧瀑布流、LBO、Comps、GBM与BSM)
# ==============================================================================
class UltimateHardcoreEngine:
    def __init__(self, ticker):
        self.ticker = ticker.strip().upper()
        self.stock = yf.Ticker(self.ticker)
        
        self.info, self.hist_1y, self.bs, self.fin, self.cfs = fetch_cached_ticker_data(self.ticker)
        
        # 兼容兜底：即使 .info 被限流，只要历史 K 线能拉取到最新价即可继续运行
        self.price = self.info.get('currentPrice', self.info.get('regularMarketPrice', self.info.get('previousClose', 0.0))) or 0.0
        if self.price == 0.0 and not self.hist_1y.empty:
            self.price = float(self.hist_1y['Close'].dropna().iloc[-1])

        if self.price <= 0.0 and 'symbol' not in self.info:
            st.error(f"⚠️ Yahoo Finance data temporarily unavailable for {self.ticker}. Please try again or reboot the app.")
            st.stop()

        self.name = self.info.get('longName', self.info.get('shortName', self.ticker))
        self.sector = self.info.get('sector', 'Technology' if not self.ticker.endswith('.KL') else 'Financial Services')
        self.currency = self.info.get('currency', 'MYR' if self.ticker.endswith('.KL') else 'USD')
        self.is_malaysia = self.ticker.endswith('.KL')

        self.shares = self.info.get('sharesOutstanding', 1000000000) or 1000000000
        self.cash = self.info.get('totalCash') or get_fin_metric(self.bs, 'Cash And Cash Equivalents', 50000000)
        self.debt = self.info.get('totalDebt') or get_fin_metric(self.bs, 'Total Debt', 20000000)
        self.revenue = self.info.get('totalRevenue') or get_fin_metric(self.fin, 'Total Revenue', self.price * self.shares * 0.2)
        
        gross_profit = self.info.get('grossProfits') or get_fin_metric(self.fin, 'Gross Profit', self.revenue * 0.5)
        self.cogs = max(0.0, self.revenue - gross_profit)
        
        self.ebitda = self.info.get('ebitda') or get_fin_metric(self.fin, 'EBITDA', self.revenue * 0.25)
        self.net_income = self.info.get('netIncomeToCommon') or get_fin_metric(self.fin, 'Net Income', self.ebitda * 0.6)
        self.hist_da = get_fin_metric(self.cfs, 'Depreciation And Amortization', self.ebitda * 0.15)
        
        raw_fcf = self.info.get('freeCashflow', 0) or 0
        if raw_fcf <= 0:
            raw_fcf = get_fin_metric(self.cfs, 'Free Cash Flow', 0)
        if raw_fcf <= 0:
            raw_fcf = max(self.net_income * 0.6, self.ebitda * 0.15, 1000000) if self.net_income > 0 else self.revenue * 0.05
        self.cf = raw_fcf

        self.market_cap = self.price * self.shares
        self.ev = self.market_cap + self.debt - self.cash
        self.scatter_data = None 
        self.hardcore_ufcf_proj = []
        self.hardcore_ebitda_y5 = self.ebitda * 1.2

        # 🌟 计算【公式 01：对数收益率 Log Return】与【公式 09：最大回撤 Max Drawdown】
        self.log_return_1y = 0.0
        self.ann_volatility = 0.30
        self.max_drawdown = 0.0
        self.drawdown_series = pd.Series(dtype=float)
        if not self.hist_1y.empty and 'Close' in self.hist_1y.columns:
            closes = self.hist_1y['Close'].dropna()
            if len(closes) > 5:
                log_rets = np.log(closes / closes.shift(1)).dropna()
                self.log_return_1y = float(log_rets.sum())
                self.ann_volatility = float(log_rets.std() * np.sqrt(252))
                rolling_max = closes.cummax()
                dd = 1.0 - (closes / rolling_max)
                self.drawdown_series = -dd * 100.0
                self.max_drawdown = float(dd.max())

    def get_esg_adjustment(self):
        if self.sector in ['Energy', 'Basic Materials', 'Industrials']: return 0.015, "🔴 High ESG Risk (Penalty +1.5%)"
        elif self.sector in ['Technology', 'Healthcare', 'Financial Services']: return -0.005, "🟢 Low ESG Risk (Reward -0.5%)"
        return 0.00, "⚪ Neutral ESG Risk (No Adj)"

    def compute_blume_beta(self):
        fallback = 1.0
        try:
            market_sym = '^KLSE' if self.is_malaysia else '^GSPC'
            s_hist = fetch_cached_history(self.ticker, period='3y', interval='1mo')
            m_hist = fetch_cached_history(market_sym, period='3y', interval='1mo')
            if s_hist.empty or m_hist.empty: return fallback, 'System Default'
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
        self.rf = 0.038 if self.is_malaysia else 0.042
        self.esg_adj, self.esg_tag = self.get_esg_adjustment()
        
        self.ke = self.rf + (self.beta * erp) + self.esg_adj
        self.tax = 0.24 if self.is_malaysia else 0.21
        
        total_cap = self.market_cap + self.debt
        w_e = self.market_cap / total_cap if total_cap > 0 else 1
        w_d = self.debt / total_cap if total_cap > 0 else 0
        
        int_exp = abs(self.info.get('interestExpense', 0) or get_fin_metric(self.fin, 'Interest Expense'))
        kd = min((int_exp / self.debt) if self.debt > 0 else 0.05, 0.10)
        self.wacc = (w_e * self.ke) + (w_d * kd * (1 - self.tax))
        self.wacc = max(self.wacc, terminal_g + 0.02)
        
        self.g1 = min(max(self.info.get('earningsGrowth', 0) or 0.08, 0.03), 0.25)
        self.g2 = terminal_g
        self.horizon = 10 if self.sector in ['Technology', 'Communication Services'] else 5

        self.val_dcf = self.calc_specific_dcf(self.wacc, self.g2)

        div = self.info.get('dividendRate') or self.info.get('trailingAnnualDividendRate') or 0.0
        self.val_ddm = None
        if div > 0:
            g_ddm = min(self.g2, self.ke - 0.01)
            self.val_ddm = (div * (1.0 + g_ddm)) / (self.ke - g_ddm) if self.ke > g_ddm else 0.0

        eps = self.info.get('trailingEps') or self.info.get('forwardEps') or 0.0
        if eps <= 0:
            if self.net_income > 0 and self.shares > 0: eps = self.net_income / self.shares
        self.val_pe = None
        if eps > 0:
            bench_pe = 24.0 if self.sector in ['Technology', 'Communication Services'] else (11.5 if self.sector == 'Financial Services' else 16.0)
            self.val_pe = eps * bench_pe

        if self.sector in ['Financial Services', 'Real Estate', 'Utilities'] and self.val_ddm and self.val_ddm > 0:
            self.model_name = 'Dividend Discount Model (DDM)'
            self.r = self.ke; val = self.val_ddm
        elif self.val_dcf and self.val_dcf > 0:
            self.model_name = 'Discounted Cash Flow (DCF)'
            self.r = self.wacc; val = self.val_dcf
        elif self.val_pe and self.val_pe > 0:
            self.model_name = 'P/E Multiples Valuation'
            self.r = self.wacc; val = self.val_pe
        else:
            self.model_name = 'Discounted Cash Flow (DCF)'
            self.r = self.wacc; val = self.val_dcf if self.val_dcf else 0.0

        return val, self.find_implied_growth()

    def calc_specific_dcf(self, test_wacc, test_g2):
        if self.cf <= 0 or test_wacc <= test_g2: return None
        pv1 = 0
        curr_cf = self.cf
        growth_rates = np.linspace(self.g1, test_g2, self.horizon)
        for y in range(1, self.horizon + 1):
            annual_g = growth_rates[y - 1]
            curr_cf *= (1 + annual_g)
            pv1 += curr_cf / ((1 + test_wacc) ** y)
        pv_tv = (curr_cf * (1 + test_g2)) / (test_wacc - test_g2) / ((1 + test_wacc) ** self.horizon)
        return (pv1 + pv_tv + self.cash - self.debt) / self.shares if self.shares > 0 else 0

    def find_implied_growth(self):
        if self.price <= 0 or self.cf <= 0: return None
        low, high = -0.50, 2.00
        for _ in range(50):
            mid = (low + high) / 2
            pv1, curr_cf = 0, self.cf
            growth_rates = np.linspace(mid, self.g2, self.horizon)
            for y in range(1, self.horizon + 1):
                curr_cf *= (1 + growth_rates[y - 1])
                pv1 += curr_cf / ((1 + self.wacc) ** y)
            pv_tv = (curr_cf * (1 + self.g2)) / (self.wacc - self.g2) / ((1 + self.wacc) ** self.horizon)
            res = (pv1 + pv_tv + self.cash - self.debt) / self.shares
            if res < self.price: low = mid
            else: high = mid
        return mid

    def build_hardcore_3_statement(self, dso, dio, dpo, capex_pct):
        years = ['Year 0 (Current)', 'Year 1', 'Year 2', 'Year 3', 'Year 4', 'Year 5']
        
        rev_0 = self.revenue
        cogs_0 = self.cogs if self.cogs > 0 else rev_0 * 0.5
        ebitda_margin = self.ebitda / self.revenue if self.revenue > 0 else 0.2
        tax_rate = self.tax

        rev = [rev_0]
        cogs = [cogs_0]
        ebitda = [self.ebitda]
        da = [self.hist_da]
        capex = [rev_0 * capex_pct]
        
        ar = [(dso / 365.0) * rev_0]
        inv = [(dio / 365.0) * cogs_0]
        ap = [(dpo / 365.0) * cogs_0]
        nwc = [ar[0] + inv[0] - ap[0]]
        dnwc = [0.0]
        ufcf = [self.cf]

        new_capex_schedule = [] 

        for i in range(1, 6):
            g = self.g1 - (self.g1 - self.g2) * (i / 5)
            r = rev[-1] * (1 + g)
            c = cogs[-1] * (1 + g)
            e = r * ebitda_margin

            rev.append(r)
            cogs.append(c)
            ebitda.append(e)

            cap = r * capex_pct
            capex.append(cap)
            new_capex_schedule.append(cap)

            current_da = self.hist_da * (1 - 0.2 * i) if (1 - 0.2 * i) > 0 else 0
            for j in range(len(new_capex_schedule)):
                current_da += new_capex_schedule[j] * 0.2
            da.append(current_da)

            current_ar = (dso / 365.0) * r
            current_inv = (dio / 365.0) * c
            current_ap = (dpo / 365.0) * c
            current_nwc = current_ar + current_inv - current_ap

            ar.append(current_ar)
            inv.append(current_inv)
            ap.append(current_ap)
            nwc.append(current_nwc)
            dnwc.append(current_nwc - nwc[-2])

            ebit = e - current_da
            nopat = ebit * (1 - tax_rate)
            current_ufcf = nopat + current_da - cap - dnwc[-1]
            ufcf.append(current_ufcf)

        self.hardcore_ufcf_proj = ufcf[1:] 
        self.hardcore_ebitda_y5 = ebitda[-1] # 精确绑定第 5 年 EBITDA 供 LBO 退出使用

        df = pd.DataFrame({
            "Revenue": rev,
            "EBITDA": ebitda,
            "(-) D&A (Waterfall)": [-d for d in da],
            "(=) EBIT": [e - d for e, d in zip(ebitda, da)],
            "NOPAT (EBIT x 1-T)": [(e - d) * (1 - tax_rate) for e, d in zip(ebitda, da)],
            "(-) Capex": [-c for c in capex],
            "(-) Δ NWC (WC Change)": [-d for d in dnwc],
            "(=) Unlevered FCF": ufcf
        }, index=years).T
        return df

    def run_lbo_model(self, ltv_ratio, interest_rate, exit_multiple):
        purchase_price = self.ev
        debt_funding = purchase_price * ltv_ratio
        equity_funding = purchase_price - debt_funding
        
        debt_schedule = [debt_funding]
        
        for fcf in self.hardcore_ufcf_proj:
            interest = debt_schedule[-1] * interest_rate
            cash_sweep = max(0, fcf - interest)
            ending_debt = max(0, debt_schedule[-1] - cash_sweep)
            debt_schedule.append(ending_debt)
            
        y5_ebitda = self.hardcore_ebitda_y5 if self.hardcore_ebitda_y5 > 0 else self.ebitda * ((1 + self.g2) ** 5)
        exit_ev = y5_ebitda * exit_multiple
        exit_equity = max(0.0, exit_ev - debt_schedule[-1])
        
        moic = exit_equity / equity_funding if equity_funding > 0 else 0
        irr = (moic ** (1/5)) - 1 if moic > 0 else 0
        
        return {
            "Entry EV": purchase_price, "Debt": debt_funding, "Equity": equity_funding,
            "Exit EV": exit_ev, "Exit Debt": debt_schedule[-1], "Exit Equity": exit_equity,
            "MOIC": moic, "IRR": irr, "Debt Schedule": debt_schedule
        }

    def get_peer_list(self):
        peer_map = {
            'NVDA': ['AMD', 'INTC', 'TSM', 'QCOM'],
            'AAPL': ['MSFT', 'GOOGL', 'AMZN', 'META'],
            'TSLA': ['RIVN', 'F', 'GM', 'TM'],
            '1155.KL': ['1023.KL', '1295.KL', '1188.KL', '5819.KL'],
            '1295.KL': ['1155.KL', '1023.KL', '1188.KL', '5819.KL'],
            '1023.KL': ['1155.KL', '1295.KL', '5819.KL'],
            '5347.KL': ['5264.KL', '1155.KL', '1023.KL'],
            '5264.KL': ['5347.KL', '1155.KL', '1023.KL']
        }
        if self.ticker in peer_map:
            peers = list(peer_map[self.ticker])
        elif self.is_malaysia:
            peers = ['1155.KL', '1023.KL', '1295.KL', '5347.KL']
        else:
            peers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN']
        if self.ticker in peers: peers.remove(self.ticker)
        return peers

    def run_comps_analysis(self):
        peers = self.get_peer_list()
        comp_data = [{
            "Ticker": self.ticker, "Name": self.name[:12],
            "Market Cap ($B)": round(self.market_cap / 1e9, 2),
            "EV/EBITDA": round(self.ev / self.ebitda, 2) if self.ebitda > 0 else 0,
            "P/E": round(self.info.get('trailingPE', 0) or 0, 2),
            "Gross Margin %": round((self.info.get('grossMargins', 0) or 0) * 100, 1)
        }]
        
        for p in peers:
            try:
                pi, _, _, _, _ = fetch_cached_ticker_data(p)
                pmcap = pi.get('marketCap', 1e9) or 1e9
                pebitda = pi.get('ebitda', 1e6) or 1e6
                pe_ratio = pi.get('trailingPE', 0) or 0
                gm = (pi.get('grossMargins', 0) or 0) * 100
                pev = pmcap + (pi.get('totalDebt', 0) or 0) - (pi.get('totalCash', 0) or 0)
                comp_data.append({
                    "Ticker": p, "Name": pi.get('shortName', p)[:12],
                    "Market Cap ($B)": round(pmcap / 1e9, 2),
                    "EV/EBITDA": round(pev / pebitda, 2) if pebitda > 0 else 0,
                    "P/E": round(pe_ratio, 2), "Gross Margin %": round(gm, 1)
                })
            except Exception: pass
        return pd.DataFrame(comp_data)

    def run_monte_carlo(self, sims=2000):
        if self.cf <= 0: return []
        results = []
        np.random.seed(42)
        sim_waccs = np.random.normal(self.wacc, 0.015, sims)
        sim_gs = np.random.normal(self.g2, 0.005, sims)
        
        for w, g in zip(sim_waccs, sim_gs):
            if w <= g + 0.005: continue
            val = self.calc_specific_dcf(w, g)
            if val and val > 0: results.append(val)
        return results

    # 🌟 新增【公式 07：几何布朗运动 GBM】dS_t = \mu S_t dt + \sigma S_t dW_t
    def simulate_gbm_paths(self, days=252, paths=40):
        np.random.seed(42)
        dt = 1.0 / 252.0
        mu = self.ke
        sigma = max(0.15, min(self.ann_volatility, 0.85))
        price_paths = np.zeros((days, paths))
        price_paths[0] = self.price
        for t in range(1, days):
            z = np.random.standard_normal(paths)
            price_paths[t] = price_paths[t - 1] * np.exp((mu - 0.5 * sigma ** 2) * dt + sigma * np.sqrt(dt) * z)
        return price_paths

    # 🌟 融合版最强 B-S 引擎 (公式 04：支持双向、希腊字母全解及股息率)
    def black_scholes_pricing(self, S, K, T, r, sigma, q=0.0):
        if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
            return {"Call": 0.0, "Put": 0.0, "Delta_C": 0.0, "Delta_P": 0.0, "Gamma": 0.0, "Theta_C": 0.0, "Theta_P": 0.0, "Vega": 0.0, "Rho_C": 0.0, "Rho_P": 0.0}
        
        d1 = (np.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        call = S * np.exp(-q * T) * stats.norm.cdf(d1) - K * np.exp(-r * T) * stats.norm.cdf(d2)
        put = K * np.exp(-r * T) * stats.norm.cdf(-d2) - S * np.exp(-q * T) * stats.norm.cdf(-d1)
        
        delta_c = np.exp(-q * T) * stats.norm.cdf(d1)
        delta_p = -np.exp(-q * T) * stats.norm.cdf(-d1)
        gamma = (np.exp(-q * T) * stats.norm.pdf(d1)) / (S * sigma * np.sqrt(T))
        vega = S * np.exp(-q * T) * stats.norm.pdf(d1) * np.sqrt(T) / 100.0
        
        theta_c = (- (S * sigma * np.exp(-q * T) * stats.norm.pdf(d1)) / (2 * np.sqrt(T)) - r * K * np.exp(-r * T) * stats.norm.cdf(d2) + q * S * np.exp(-q * T) * stats.norm.cdf(d1)) / 365.0
        theta_p = (- (S * sigma * np.exp(-q * T) * stats.norm.pdf(d1)) / (2 * np.sqrt(T)) + r * K * np.exp(-r * T) * stats.norm.cdf(-d2) - q * S * np.exp(-q * T) * stats.norm.cdf(-d1)) / 365.0
        
        rho_c = K * T * np.exp(-r * T) * stats.norm.cdf(d2) / 100.0
        rho_p = -K * T * np.exp(-r * T) * stats.norm.cdf(-d2) / 100.0
        
        return {
            "Call": call, "Put": put, "Delta_C": delta_c, "Delta_P": delta_p,
            "Gamma": gamma, "Vega": vega, "Theta_C": theta_c, "Theta_P": theta_p,
            "Rho_C": rho_c, "Rho_P": rho_p
        }

# ==============================================================================
# 4. 图表生成 (热力图 + 凯利公式 + K线 + Beta + 协整价差)
# ==============================================================================
def draw_sensitivity_heatmap(engine):
    if engine.cf <= 0: return None, None
    w_steps, g_steps = np.array([-0.02, -0.01, 0.0, 0.01, 0.02]), np.array([-0.01, -0.005, 0.0, 0.005, 0.01])
    wacc_vals, g2_vals = engine.wacc + w_steps, engine.g2 + g_steps
    z_vals, hover_text = [], []
    for w in wacc_vals:
        row, text_row = [], []
        for g in g2_vals:
            val = engine.calc_specific_dcf(w, g)
            if val and val > 0:
                row.append(val); text_row.append(f"WACC: {w*100:.1f}%<br>Tg: {g*100:.1f}%<br>Fair Value: {engine.currency} {val:.2f}<br>vs Price: {((val - engine.price) / engine.price) * 100:+.1f}%")
            else:
                row.append(np.nan); text_row.append("N/A")
        z_vals.append(row); hover_text.append(text_row)

    valid_z = [v for row in z_vals for v in row if pd.notna(v)]
    if valid_z:
        max_val, min_val = max(valid_z), min(valid_z)
        max_diff = max(abs(max_val - engine.price), abs(min_val - engine.price)) if max(abs(max_val - engine.price), abs(min_val - engine.price)) > 0 else 1.0 
        c_min, c_max = engine.price - max_diff, engine.price + max_diff
        win_rate = sum(1 for v in valid_z if v >= engine.price) / len(valid_z)
        
        # 🌟 计算【公式 06：凯利公式 Kelly Criterion】f* = (bp - q) / b
        upside = max(0.05, (max_val - engine.price) / engine.price)
        downside = max(0.05, (engine.price - min_val) / engine.price)
        b_odds = upside / downside
        kelly_f = max(0.0, (b_odds * win_rate - (1.0 - win_rate)) / b_odds)
        
        stats_dict = {
            'best': max_val, 'worst': min_val,
            'green_count': sum(1 for v in valid_z if v >= engine.price),
            'total': len(valid_z), 'win_rate': win_rate,
            'kelly_full': kelly_f, 'kelly_half': kelly_f * 0.5
        }
    else:
        c_min, c_max, stats_dict = 0, 1, None

    fig = go.Figure(data=go.Heatmap(z=z_vals, x=[f"{g*100:.1f}%" for g in g2_vals], y=[f"{w*100:.1f}%" for w in wacc_vals], text=np.array(z_vals), texttemplate="%{text:.2f}", hoverinfo="text", hovertext=hover_text, colorscale=[[0.0, '#ef4444'], [0.5, '#1e293b'], [1.0, '#10b981']], zmin=c_min, zmax=c_max, showscale=False))
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=320, xaxis_title="Terminal Growth Rate (g) ➡️", yaxis_title="WACC (Discount Rate) ⬇️", yaxis=dict(autorange='reversed', showgrid=False, zeroline=False), xaxis=dict(showgrid=False, zeroline=False), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#94a3b8'))
    return fig, stats_dict

def draw_pro_candlestick(engine):
    hist = engine.hist_1y.copy()
    if hist.empty: return None
    hist['MA20'], hist['MA50'] = hist['Close'].rolling(20).mean(), hist['Close'].rolling(50).mean()
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], name='Price'))
    fig.add_trace(go.Scatter(x=hist.index, y=hist['MA20'], line=dict(color='#f59e0b', width=1.5), name='20-Day SMA'))
    fig.add_trace(go.Scatter(x=hist.index, y=hist['MA50'], line=dict(color='#3b82f6', width=1.5), name='50-Day SMA'))
    fig.update_layout(xaxis_rangeslider_visible=False, height=350, margin=dict(l=0, r=0, t=10, b=0), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#94a3b8'), xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'), yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'), legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01))
    return fig

def draw_beta_scatter(engine):
    if engine.scatter_data is None: return None
    stock_ret, market_ret = engine.scatter_data.iloc[:, 0], engine.scatter_data.iloc[:, 1]
    r_squared = np.corrcoef(stock_ret, market_ret)[0, 1] ** 2 if not np.isnan(np.corrcoef(stock_ret, market_ret)[0, 1]) else 0.0
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=market_ret, y=stock_ret, mode='markers', marker=dict(color='#38bdf8', size=7, opacity=0.8), name='Returns'))
    x_range = np.linspace(market_ret.min(), market_ret.max(), 100)
    fig.add_trace(go.Scatter(x=x_range, y=engine.beta * x_range, mode='lines', line=dict(color='#ef4444', width=2), name='Beta Regression'))
    fig.update_layout(title=dict(text=f"Beta Regression (Beta = {engine.beta:.2f} | R² = {r_squared:.2f})", font=dict(color='#ffffff')), xaxis_title="Market Benchmark", yaxis_title="Stock Return (%)", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#94a3b8'), xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'), yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'), showlegend=False, height=330, margin=dict(l=0, r=0, t=35, b=0))
    return fig

# ==============================================================================
# 5. 主程序与 Tabs 渲染
# ==============================================================================
def main():
    col_title, col_lang = st.columns([3, 1.2])
    with col_lang:
        selected_lang = st.selectbox("🌐 Language / 语言", options=["中文", "English"], index=0)
        lang_key = "zh" if selected_lang == "中文" else "en"
        T = TEXTS[lang_key]

    with col_title:
        st.markdown(f"<h1 style='color: #ffffff; font-weight: 800; font-size: 2rem;'>{T['title']}</h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: #38bdf8; font-weight: 600; font-size: 14px; margin-top: -5px;'>{T['subtitle']}</p>", unsafe_allow_html=True)

    st.write("---")

    with st.container(border=True):
        if "ticker_input" not in st.session_state: st.session_state.ticker_input = "NVDA"
        def set_ticker(t): st.session_state.ticker_input = t
        
        st.write(T['quick_tag'])
        q1, q2, q3, q4 = st.columns(4)
        q1.button("🇺🇸 NVDA", on_click=set_ticker, args=("NVDA",), use_container_width=True)
        q2.button("🇺🇸 AAPL", on_click=set_ticker, args=("AAPL",), use_container_width=True)
        q3.button("🇲🇾 MAYBANK (1155.KL)", on_click=set_ticker, args=("1155.KL",), use_container_width=True)
        q4.button("🇲🇾 TENAGA (5347.KL)", on_click=set_ticker, args=("5347.KL",), use_container_width=True)
        
        col_in1, col_in2 = st.columns([2, 2])
        with col_in1:
            ticker_input = st.text_input(T['input_label'], key="ticker_input")
        
        with st.expander(T['param_title'], expanded=False):
            st.info(T['param_tip'])
            c_erp, c_g2 = st.columns(2)
            custom_erp = c_erp.slider(T['erp_label'], 4.0, 7.0, 5.0, 0.1) / 100
            custom_g2 = c_g2.slider(T['g2_label'], 1.0, 3.5, 2.0, 0.1) / 100
        
        st.caption(T['esg_caption'])

    if ticker_input:
        with st.spinner("Compiling Hardcore Institutional Engine..." if lang_key == 'en' else "正在拉取华尔街核心引擎数据..."):
            engine = UltimateHardcoreEngine(ticker_input)
            val, implied_g = engine.run_valuation(custom_erp, custom_g2)

            st.markdown(f"<h3 style='margin-top: 25px;'>🏢 {engine.name} ({engine.ticker}) <span style='font-size:14px; color:#94a3b8;'>| Sector: {engine.sector}</span></h3>", unsafe_allow_html=True)

            tabs_names = [
                "📊 [1] Quant Valuation Dashboard (量化估值终端)" if lang_key == "zh" else "📊 [1] Quant Valuation Dashboard",
                "⚙️ [2] Hardcore 3-Statement & NWC (硬核财报排程)" if lang_key == "zh" else "⚙️ [2] Hardcore 3-Statement & NWC",
                "🏛️ [3] Dynamic LBO & Debt Schedule (动态收购沙盘)" if lang_key == "zh" else "🏛️ [3] Dynamic LBO & Debt Schedule",
                "🏢 [4] Comps & Cointegration (同业与协整配对)" if lang_key == "zh" else "🏢 [4] Comps & Cointegration",
                "🎲 [5] Monte Carlo & GBM (蒙特卡洛与随机路径)" if lang_key == "zh" else "🎲 [5] Monte Carlo & GBM Paths",
                "📈 [6] Efficient Frontier (有效前沿资产配置)" if lang_key == "zh" else "📈 [6] Efficient Frontier",
                "📉 [7] Options & AI Strategist (期权与智能策略)" if lang_key == "zh" else "📉 [7] Options & AI Strategist"
            ]
            
            tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(tabs_names)

            # ==========================================
            # TAB 1: 估值面板 (含凯利公式、对数收益、最大回撤)
            # ==========================================
            with tab1:
                with st.container(border=True):
                    st.markdown(f"**{T['macro_title']}**")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Beta Risk (Cov/Var)", f"{engine.beta:.2f}", delta=engine.beta_type, delta_color="off")
                    c2.metric("Rf Rate", f"{engine.rf * 100:.2f}%")
                    c3.metric("WACC / CAPM Hurdle", f"{engine.r * 100:.2f}%", engine.esg_tag)
                    st.caption(T['macro_exp'])

                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

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
                        status_html = f"<div style='color: {pill_color}; font-weight: 700; font-size: 13px;'>{diff_sign}{diff:.1f}% {T['vs_market']}</div>"
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
                    st.markdown(render_matrix_card(T["model_dcf_name"], engine.val_dcf, engine.price, engine.model_name == 'Discounted Cash Flow (DCF)', engine.currency, T["note_dcf"], T["no_data_dcf"]), unsafe_allow_html=True)
                with m_col2:
                    st.markdown(render_matrix_card(T["model_ddm_name"], engine.val_ddm, engine.price, engine.model_name == 'Dividend Discount Model (DDM)', engine.currency, T["note_ddm"], T["no_data_ddm"]), unsafe_allow_html=True)
                with m_col3:
                    st.markdown(render_matrix_card(T["model_pe_name"], engine.val_pe, engine.price, engine.model_name == 'P/E Multiples Valuation', engine.currency, T["note_pe"], T["no_data_pe"]), unsafe_allow_html=True)

                st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)

                p1, p2, p3 = st.columns(3)
                p1.metric(T['price'], f"{engine.currency} {engine.price:.2f}")
                p2.metric(T['fair_val'], f"{engine.currency} {val:.2f}")
                p3.metric(T['safe_buy'], f"{engine.currency} {(val * 0.8):.2f}", "20% Margin of Safety")
                
                st.info(T['fair_val_desc'])

                if val > 0 and engine.price > 0:
                    price_to_val = engine.price / val

                    if engine.val_dcf and engine.val_dcf > 0:
                        st.markdown(f"### {T['heat_title']}")
                        with st.container(border=True):
                            st.markdown(T['heat_desc'], unsafe_allow_html=True)
                            fig_heat, heat_stats = draw_sensitivity_heatmap(engine)
                            if fig_heat and heat_stats:
                                st.plotly_chart(fig_heat, use_container_width=True)
                                
                                wr = heat_stats['win_rate']
                                if wr >= 0.70:
                                    ai_insight = f"🟢 <b>高胜率 / 低估 (High Margin of Safety):</b> 无论宏观折现率如何波动，绝大多数预测情景（{heat_stats['green_count']}/{heat_stats['total']}）都显示该公司当前市价被严重低估，具备极厚的安全垫。" if lang_key == "zh" else f"🟢 <b>High Margin of Safety:</b> Across fluctuating discount rates, the majority of scenarios ({heat_stats['green_count']}/{heat_stats['total']}) show the stock is severely undervalued with a deep safety cushion."
                                elif wr <= 0.30:
                                    ai_insight = f"🔴 <b>高风险 / 高估 (Overvalued & Fragile):</b> 当前市价已透支未来。除非公司能在极低利率下保持疯狂增长，否则面临估值杀跌风险。" if lang_key == "zh" else f"🔴 <b>Overvalued & Fragile:</b> The current price has front-run its future. Unless it sustains hyper-growth in a zero-interest environment, it faces severe multiple contraction risk."
                                else:
                                    ai_insight = "🟡 <b>高度敏感 / 合理偏高 (Highly Sensitive):</b> 估值处于微妙的平衡点。当前价格对宏观利率(WACC)极为敏感，没有单边套利空间，属于“买定离手”的博弈区。" if lang_key == "zh" else "🟡 <b>Highly Sensitive:</b> Valuation is at a delicate equilibrium. The current price is extremely sensitive to macro rates (WACC), offering no clear margin of safety. It's a speculative play."

                                win_str = "胜率测算:" if lang_key == "zh" else "Win Rate:"
                                worst_str = "最悲观底线:" if lang_key == "zh" else "Pessimistic Floor:"
                                best_str = "最乐观上限:" if lang_key == "zh" else "Optimistic Ceiling:"
                                kelly_str = "凯利公式最优仓位 (Half-Kelly):" if lang_key == "zh" else "Kelly Optimal Sizing (Half-Kelly):"
                                ai_header = "🤖 AI 矩阵智能解析 & 凯利公式仓位管理 (Sensitivity & Kelly Sizing)" if lang_key == "zh" else "🤖 AI Sensitivity Matrix & Kelly Criterion Sizing"

                                st.markdown(f"""
                                <div style="background: rgba(15, 23, 42, 0.6); border-left: 4px solid #38bdf8; padding: 16px; border-radius: 6px; margin-top: 10px;">
                                    <div style="color: #38bdf8; font-weight: 800; font-size: 15px; margin-bottom: 8px;">
                                        {ai_header}
                                    </div>
                                    <div style="color: #e2e8f0; font-size: 14px; margin-bottom: 12px; line-height: 1.6;">
                                        {ai_insight}
                                    </div>
                                    <div style="display: flex; flex-wrap: wrap; gap: 20px; color: #94a3b8; font-size: 12.5px; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 10px;">
                                        <div>⚡ <b>{win_str}</b> <span style="color:#10b981; font-weight:bold;">{heat_stats['green_count']}/{heat_stats['total']} ({wr*100:.0f}%)</span></div>
                                        <div>📉 <b>
