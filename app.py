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
st.set_page_config(page_title="Ultimate Quant & PE Terminal V9.6", page_icon="💹", layout="wide", initial_sidebar_state="collapsed")

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

@st.cache_resource
def get_yf_session():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    })
    return session

# ==============================================================================
# 2. 国际化多语言字典
# ==============================================================================
TEXTS = {
    "zh": {
        "title": "🌐 智能量化与衍生品金融终端 (V9.6 旗舰全功能版)",
        "subtitle": "完美融合 线性衰减DCF、热力图、动态NWC与折旧瀑布流、LBO、同业Comps、有效前沿与智能期权顾问",
        "quick_tag": "🔥 热门快捷测评：",
        "input_label": "输入股票代码 (如 1155.KL, NVDA, AAPL)：",
        
        "param_title": "⚙️ 步骤 2：估值核心参数设定 (可保持默认) 👈 (小白用户建议直接保持默认，无需改动)",
        "param_tip": "💡 **何时建议手动调整？**\n* **永续增长率 (g)**：当您预期该行业未来长期通胀或名义GDP增速显著高于/低于历史常态时可微调。\n* **风险溢价 (ERP)**：当市场处于极端恐慌（调高ERP）或极度狂热（调低ERP）周期时可手动修正。",
        "erp_label": "股市风险溢价要求 (Equity Risk Premium)",
        "g2_label": "长期永续通胀增长率 (Terminal Growth Rate)",
        "esg_caption": "🌿 本系统已自动结合可持续金融 (Sustainable Finance) 与 ESG 行业风险溢价进行折现率修正。",
        
        "macro_title": "[1. 动态宏观与资本成本 (DYNAMIC MACRO & COST OF CAPITAL)]",
        "macro_exp": "💡 **通俗解释 (Plain English)：** Beta 衡量股票相对于大盘的波动率。Rf 是无风险国债利率。WACC / 折现率是你作为投资者要求的最低及格线回报率。",
        
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

        "heat_title": "[3. 🌡️ 核心参数敏感性分析矩阵 (DCF SENSITIVITY HEATMAP)]",
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

        "chart_title": "[10. 📈 高级盘面与波动率回归分析]",
        "beta_desc": "📊 **Beta 收益率特征线散点分布图说明：**\n* 每个点代表过往某一周的收益率联动。红线斜率即为真实 Beta（马股对标 MSCI Malaysia ETF，美股对标 S&P 500）。\n* **$R^2$（拟合优度）补充解析**：点越密集贴近红线，说明该股越受大盘宏观主导（如银行股）；点越分散，说明该股具有极强的个股独立行情（如科技股）。",
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
        "title": "🌐 Universal Quant & Derivatives Terminal (Flagship V9.6)",
        "subtitle": "Integrating Fading Growth DCF, Capex Waterfall, Dynamic NWC, LBO, Comps, Monte Carlo, Efficient Frontier & AI Options Strategist",
        "quick_tag": "🔥 Quick Select:",
        "input_label": "Enter Stock Ticker (e.g., 1155.KL, NVDA, AAPL):",
        
        "param_title": "⚙️ Step 2: Macro & Valuation Parameters (Defaults Recommended) 👈 (Keep default unless necessary)",
        "param_tip": "💡 **When to adjust manually?**\n* **Terminal Growth (g)**: Adjust if you expect long-term structural inflation or GDP growth to deviate from historical norms.\n* **Equity Risk Premium (ERP)**: Adjust during extreme market cycles (higher ERP during panics, lower during bubbles).",
        "erp_label": "Equity Risk Premium (ERP)",
        "g2_label": "Terminal Growth Rate (g)",
        "esg_caption": "🌿 Sustainable Finance & ESG Sector Risk Premium automatically integrated into discount rate adjustments.",
        
        "macro_title": "[1. DYNAMIC MACRO & COST OF CAPITAL]",
        "macro_exp": "💡 **Plain English Explanation:** Beta measures stock volatility compared to the market. Rf is the benchmark government bond yield. WACC / Discount Rate is your hurdle rate / minimum required rate of return.",
        
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

        "heat_title": "[3. 🌡️ DCF SENSITIVITY HEATMAP]",
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

        "chart_title": "[10. Advanced Price Action & Regression Analysis]",
        "beta_desc": "📊 **Beta Scatter Plot Explanation:** Each dot represents past weekly return correlation. The red line slope represents the true Beta (Bursa benchmarks against MSCI Malaysia ETF, US equities against S&P 500).\n* **$R^2$ Analysis**: Tight clustering indicates market-driven systemic risk; higher dispersion reflects strong independent trends.",
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

# ==============================================================================
# 3. 核心硬核量化引擎 (集成 NWC、折旧瀑布流、LBO、Comps、蒙特卡洛与 Black-Scholes)
# ==============================================================================
class UltimateHardcoreEngine:
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
        self.currency = self.info.get('currency', 'MYR' if self.ticker.endswith('.KL') else 'USD')
        self.is_malaysia = self.ticker.endswith('.KL')
        
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
        self.revenue = self.info.get('totalRevenue') or get_fin_metric(self.fin, 'Total Revenue', 1000000)
        
        gross_profit = self.info.get('grossProfits') or get_fin_metric(self.fin, 'Gross Profit', self.revenue * 0.5)
        self.cogs = self.revenue - gross_profit
        
        self.ebitda = self.info.get('ebitda') or get_fin_metric(self.fin, 'EBITDA', self.revenue * 0.2)
        self.net_income = self.info.get('netIncomeToCommon') or get_fin_metric(self.fin, 'Net Income', self.ebitda * 0.5)
        self.hist_da = get_fin_metric(self.cfs, 'Depreciation And Amortization', self.ebitda * 0.2)
        
        # 🌟 智能自由现金流鲁棒性兜底：若雅虎无 FCF 或为负/零（马股常见），自动以代理现金流（净利润60%或营收5%）填充，确保 DCF/蒙特卡洛全线通畅
        raw_fcf = self.info.get('freeCashflow', 0)
        if raw_fcf <= 0:
            raw_fcf = get_fin_metric(self.cfs, 'Free Cash Flow', 0)
        if raw_fcf <= 0:
            raw_fcf = max(self.net_income * 0.6, self.ebitda * 0.15, 1000000) if self.net_income > 0 else self.revenue * 0.05
        self.cf = raw_fcf

        self.market_cap = self.price * self.shares
        self.ev = self.market_cap + self.debt - self.cash
        self.scatter_data = None 
        self.hardcore_ufcf_proj = []

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
            
        y5_ebitda = self.ebitda * ((self.revenue / self.ebitda) if self.ebitda>0 else 1) 
        exit_ev = y5_ebitda * exit_multiple
        exit_equity = exit_ev - debt_schedule[-1]
        
        moic = exit_equity / equity_funding if equity_funding > 0 else 0
        irr = (moic ** (1/5)) - 1 if moic > 0 else 0
        
        return {
            "Entry EV": purchase_price, "Debt": debt_funding, "Equity": equity_funding,
            "Exit EV": exit_ev, "Exit Debt": debt_schedule[-1], "Exit Equity": exit_equity,
            "MOIC": moic, "IRR": irr, "Debt Schedule": debt_schedule
        }

    def run_comps_analysis(self):
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
        
        # 🌟 智能同业匹配：若在 map 中直接取，若为马股其他代码则自动分配马股本地蓝筹，杜绝误跳美股
        if self.ticker in peer_map:
            peers = peer_map[self.ticker]
        elif self.is_malaysia:
            peers = ['1155.KL', '1023.KL', '1295.KL', '5347.KL']
        else:
            peers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN']
            
        if self.ticker in peers: peers.remove(self.ticker)
        
        comp_data = []
        comp_data.append({
            "Ticker": self.ticker, "Name": self.name[:12],
            "Market Cap ($B)": round(self.market_cap / 1e9, 2),
            "EV/EBITDA": round(self.ev / self.ebitda, 2) if self.ebitda > 0 else 0,
            "P/E": round(self.info.get('trailingPE', 0), 2),
            "Gross Margin %": round(self.info.get('grossMargins', 0) * 100, 1)
        })
        
        for p in peers:
            try:
                pt = yf.Ticker(p, session=self.session)
                pi = pt.info
                pmcap = pi.get('marketCap', 1e9)
                pebitda = pi.get('ebitda', 1e6)
                pe_ratio = pi.get('trailingPE', 0)
                gm = pi.get('grossMargins', 0) * 100
                pev = pmcap + pi.get('totalDebt', 0) - pi.get('totalCash', 0)
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

    # 🌟 融合版最强 B-S 引擎 (支持双向、希腊字母全解及股息率)
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
# 4. 图表生成 (热力图 + K线 + Beta)
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
        stats = {'best': max_val, 'worst': min_val, 'green_count': sum(1 for v in valid_z if v >= engine.price), 'total': len(valid_z), 'win_rate': sum(1 for v in valid_z if v >= engine.price) / len(valid_z)}
    else:
        c_min, c_max, stats = 0, 1, None

    fig = go.Figure(data=go.Heatmap(z=z_vals, x=[f"{g*100:.1f}%" for g in g2_vals], y=[f"{w*100:.1f}%" for w in wacc_vals], text=np.array(z_vals), texttemplate="%{text:.2f}", hoverinfo="text", hovertext=hover_text, colorscale=[[0.0, '#ef4444'], [0.5, '#1e293b'], [1.0, '#10b981']], zmin=c_min, zmax=c_max, showscale=False))
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=320, xaxis_title="Terminal Growth Rate (g) ➡️", yaxis_title="WACC (Discount Rate) ⬇️", yaxis=dict(autorange='reversed', showgrid=False, zeroline=False), xaxis=dict(showgrid=False, zeroline=False), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#94a3b8'))
    return fig, stats

def draw_pro_candlestick(ticker, session):
    hist = yf.Ticker(ticker, session=session).history(period="1y", interval="1d")
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
                "🏛️ [3] Dynamic LBO & Debt Schedule (动态收购沙盘)" if lang_key == "zh" else "🏛️️ [3] Dynamic LBO & Debt Schedule",
                "🏢 [4] Comps Matrix (同业可比公司矩阵)" if lang_key == "zh" else "🏢 [4] Comps Matrix",
                "🎲 [5] Monte Carlo (蒙特卡洛模拟)" if lang_key == "zh" else "🎲 [5] Monte Carlo Simulation",
                "📈 [6] Efficient Frontier (有效前沿资产配置)" if lang_key == "zh" else "📈 [6] Efficient Frontier",
                "📉 [7] Options & AI Strategist (期权与智能策略)" if lang_key == "zh" else "📉 [7] Options & AI Strategist"
            ]
            
            tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(tabs_names)

            # ==========================================
            # TAB 1: 估值面板
            # ==========================================
            with tab1:
                with st.container(border=True):
                    st.markdown(f"**{T['macro_title']}**")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Beta Risk", f"{engine.beta:.2f}", delta=engine.beta_type, delta_color="off")
                    c2.metric("Rf Rate", f"{engine.rf * 100:.2f}%")
                    c3.metric("WACC", f"{engine.r * 100:.2f}%", engine.esg_tag)
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

                                win_str = "胜率测算:" if lang_key == "zh" else "Win Rate Estimate:"
                                in_str = "在" if lang_key == "zh" else "In"
                                sc_str = "种宏观情景中，有" if lang_key == "zh" else "macro scenarios,"
                                safe_str = "种具备安全边际。" if lang_key == "zh" else "offer a solid margin of safety."
                                worst_str = "最悲观底线:" if lang_key == "zh" else "Pessimistic Floor:"
                                best_str = "最乐观上限:" if lang_key == "zh" else "Optimistic Ceiling:"
                                ai_header = "🤖 AI 矩阵智能解析 (Sensitivity Summary)" if lang_key == "zh" else "🤖 AI Sensitivity Summary Matrix"

                                st.markdown(f"""
                                <div style="background: rgba(15, 23, 42, 0.6); border-left: 4px solid #38bdf8; padding: 16px; border-radius: 6px; margin-top: 10px;">
                                    <div style="color: #38bdf8; font-weight: 800; font-size: 15px; margin-bottom: 8px;">
                                        {ai_header}
                                    </div>
                                    <div style="color: #e2e8f0; font-size: 14px; margin-bottom: 12px; line-height: 1.6;">
                                        {ai_insight}
                                    </div>
                                    <div style="display: flex; gap: 20px; color: #94a3b8; font-size: 12.5px; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 10px;">
                                        <div>⚡ <b>{win_str}</b> {in_str} {heat_stats['total']} {sc_str} <span style="color:#10b981; font-weight:bold;">{heat_stats['green_count']}</span> {safe_str}</div>
                                        <div>📉 <b>{worst_str}</b> {engine.currency} {heat_stats['worst']:.2f}</div>
                                        <div>🚀 <b>{best_str}</b> {engine.currency} {heat_stats['best']:.2f}</div>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)

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
                            st.markdown(f"**{T['ai_title']}**")
                            div_rate = engine.info.get('dividendRate') or engine.info.get('trailingAnnualDividendRate') or 0
                            div_yield = (div_rate / engine.price) * 100 if engine.price > 0 else 0

                            st.markdown(T['inc_title'])
                            st.write(f"- Dividend Yield: {div_yield:.2f}% | Beta Risk: {engine.beta:.2f}")
                            if engine.sector in ['Financial Services', 'Utilities', 'Real Estate'] and div_yield > 3.0:
                                st.success("-> **Verdict:** 🟢 SUITABLE FOR INCOME." if lang_key == "en" else "-> **结论:** 🟢 适合保守收息策略。")
                            else:
                                st.error("-> **Verdict:** 🔴 NOT IDEAL FOR INCOME." if lang_key == "en" else "-> **结论:** 🔴 不适合收息。")
                            
                            st.markdown(T['cap_title'])
                            st.write(f"- Implied Growth: {implied_g_str} | Model Valuation: {val:.2f}")
                            if implied_g is not None and implied_g < 0.0 and engine.price < val:
                                st.success("-> **Verdict:** 🟢 MULTI-BAGGER POTENTIAL." if lang_key == "en" else "-> **结论:** 🟢 具备翻倍潜力。")
                            elif implied_g is not None and implied_g > 0.40:
                                st.error("-> **Verdict:** 🔴 HIGH SPECULATION RISK." if lang_key == "en" else "-> **结论:** 🔴 极度投机风险。")
                            else:
                                st.info("-> **Verdict:** 🟢 / 🟡 FAIRLY PRICED." if lang_key == "en" else "-> **结论:** 🟢 / 🟡 估值适中。")

                    st.markdown(f"### {T['exec_title']}")
                    if price_to_val <= 0.70 and (implied_g is not None and implied_g < 0.0):
                        rating, reason = '🟢 STRONG BUY', f"Extreme pessimism creates massive margin of safety. Price ({engine.price:.2f}) heavily discounted vs intrinsic value ({val:.2f})." if lang_key == "en" else f"极端悲观情绪砸出了巨大的安全垫。现价 ({engine.price:.2f}) 远低于内在公允价 ({val:.2f})。"
                    elif price_to_val <= 0.85:
                        rating, reason = '🟢 BUY', f"Solid value mispricing. Price ({engine.price:.2f}) meets 20% margin of safety." if lang_key == "en" else f"优秀的价值错配。现价 ({engine.price:.2f}) 满足20%安全边际要求。"
                    elif 0.85 < price_to_val <= 1.15:
                        rating, reason = '🟡 HOLD', f"Fairly valued. Price ({engine.price:.2f}) aligns with intrinsic value ({val:.2f})." if lang_key == "en" else f"估值合理。现价 ({engine.price:.2f}) 与其真实基本面价值 ({val:.2f}) 相符。"
                    elif 1.15 < price_to_val <= 1.40:
                        rating, reason = '🔴 SELL', f"Overvalued. Price ({engine.price:.2f}) exceeds intrinsic value ({val:.2f})." if lang_key == "en" else f"估值偏高。现价 ({engine.price:.2f}) 已透支未来，缺乏安全边际。"
                    else:
                        rating, reason = '🔴 STRONG SELL', f"Severe bubble risk. Implied growth is priced for perfection." if lang_key == "en" else f"严重的泡沫风险。市场对未来增长的定价过于完美且不切实际。"

                    with st.container(border=True):
                        st.markdown(f"- **Final Investment Rating : {rating}**")
                        st.markdown(f"- **Core Justification : {reason}**")
                        st.markdown("")
                        st.caption(T['rating_explain'])

                    col_t1, col_t2 = st.columns(2)
                    with col_t1:
                        with st.container(border=True):
                            st.markdown(f"**{T['plain_title']}**")
                            st.markdown(f"- **Required Hurdle Rate / Discount Rate:** {engine.r * 100:.2f}%")
                            st.markdown("  👉 Minimum required return." if lang_key == "en" else "  👉 您买入这家公司应当要求的最低回报门槛。")
                            if implied_g is not None:
                                st.markdown(f"- **Market Sentiment / Implied Growth:** {implied_g * 100:.2f}%")
                                if implied_g > 0.35: st.markdown("  👉 **【⚠️ SEVERE BUBBLE WARNING】**" if lang_key == "en" else "  👉 **【⚠️ 严重泡沫警示】市场极度狂热**")
                                elif implied_g < 0.0: st.markdown("  👉 **【🔥 EXTREME PESSIMISM / DEEP VALUE】**" if lang_key == "en" else "  👉 **【🔥 极度悲观 / 深度价值】情绪错杀**")
                                else: st.markdown("  👉 **【⚖️ BALANCED & RATIONAL】**" if lang_key == "en" else "  👉 **【⚖ 平衡理性】无盲目炒作**")
                    
                    with col_t2:
                        with st.container(border=True):
                            st.markdown(f"**{T['fx_title']}**")
                            if not engine.is_malaysia:
                                st.warning(T['fx_content'])
                            else:
                                st.warning("- 🇲🇾 本地资产计价 (MYR)，无直接跨境外汇风险暴露。" if lang_key == "zh" else "- 🇲🇾 Local asset (MYR), no direct cross-border FX exposure.")

                    if not engine.is_malaysia:
                        target_mean = engine.info.get('targetMeanPrice')
                        target_high = engine.info.get('targetHighPrice')
                        target_low = engine.info.get('targetLowPrice')
                        num_analysts = engine.info.get('numberOfAnalystOpinions', 0)
                        rec_key = str(engine.info.get('recommendationKey', 'N/A')).upper()

                        if target_mean and num_analysts > 0:
                            st.markdown(f"<br><h3>{T['ws_title']}</h3>", unsafe_allow_html=True)
                            ws_col1, ws_col2, ws_col3 = st.columns(3)
                            
                            with ws_col1:
                                with st.container(border=True):
                                    st.markdown(f"<div style='color:#94a3b8; font-size:13px; font-weight:600; text-align:center;'>{T['ws_mean']}</div>", unsafe_allow_html=True)
                                    st.markdown(f"<div style='font-size:30px; font-weight:800; font-family:JetBrains Mono; text-align:center; color:#ffffff; margin: 10px 0;'>${target_mean:.2f}</div>", unsafe_allow_html=True)
                                    st.markdown(f"<div style='color:#38bdf8; font-size:12.5px; text-align:center;'>👥 {num_analysts} Analysts</div>", unsafe_allow_html=True)
                                    
                            with ws_col2:
                                with st.container(border=True):
                                    st.markdown(f"<div style='color:#94a3b8; font-size:13px; font-weight:600; text-align:center;'>{T['ws_range']}</div>", unsafe_allow_html=True)
                                    low_str = f"${target_low:.2f}" if target_low else "N/A"
                                    high_str = f"${target_high:.2f}" if target_high else "N/A"
                                    st.markdown(f"<div style='font-size:24px; font-weight:800; font-family:JetBrains Mono; text-align:center; color:#ffffff; margin: 12px 0;'>{low_str} ~ {high_str}</div>", unsafe_allow_html=True)
                                    st.markdown(f"<div style='color:#cbd5e1; font-size:12px; text-align:center;'>Low / High Target</div>", unsafe_allow_html=True)

                            with ws_col3:
                                with st.container(border=True):
                                    st.markdown(f"<div style='color:#94a3b8; font-size:13px; font-weight:600; text-align:center;'>{T['ws_rating']}</div>", unsafe_allow_html=True)
                                    st.markdown(f"<div style='font-size:28px; font-weight:800; font-family:JetBrains Mono; text-align:center; color:#38bdf8; margin: 10px 0;'>{rec_key}</div>", unsafe_allow_html=True)
                                    st.markdown(f"<div style='color:#4ade80; font-size:12px; text-align:center;'>🏛️ {T['ws_tag']}</div>", unsafe_allow_html=True)

                            with st.container(border=True):
                                st.markdown(f"**{T['gap_title']}**")
                                gap_pct = ((target_mean - val) / val) * 100.0
                                st.write(f"- **{T['gap_line1']}:** `${val:.2f}` | **{T['gap_line2']}:** `${target_mean:.2f}`")
                                st.write(f"- **{T['gap_line3']}:** `+{gap_pct:.1f}%` ({T['gap_desc_high']} {gap_pct:.1f}%)")
                                
                                if gap_pct > 25.0 and rec_key in ["BUY", "STRONG_BUY"]:
                                    st.error(T['gap_alert_high'])
                                elif abs(gap_pct) <= 15.0:
                                    st.success(T['ws_match'])
                                elif gap_pct < -15.0:
                                    st.info(T['gap_alert_low'])

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

            # ==========================================
            # TAB 2: 硬核财报排程 (集成双语指南)
            # ==========================================
            with tab2:
                st.markdown("#### ⚙️ Hardcore 3-Statement Forecast (NWC & Depreciation Engine)")
                
                tab2_desc = "调整下方营运资本 (DSO/DIO/DPO) 和资本开支，以动态改变自由现金流。" if lang_key == "zh" else "Adjust the Working Capital (DSO/DIO/DPO) and Capex drivers below to dynamically alter the Free Cash Flow (FCF) generation."
                st.caption(tab2_desc)
                
                exp_title_t2 = "📖 【新手必读 / 核心参数调整指南】营运资本与资本开支 (点击展开)" if lang_key == "zh" else "📖 [Beginner's Guide] Working Capital & Capex Drivers (Click to Expand)"
                
                guide_t2_zh = """
                * **DSO (应收账款天数 - Days Sales Outstanding)**
                  * **用途是什么**：衡量公司卖出产品后，客户平均需要多少天把现金付清。
                  * **默认值建议**：系统自动根据历史数据适配（通常为 45 天左右），**小白用户直接保持默认即可**。
                  * **什么情况下调整**：当分析客户拖账严重的行业（如建筑贸易，可调高至 90 天）或收钱极快的行业（如零售、软件，可调低至 15 天以内）。
                  * **如何调整**：若预计产业链资金变紧、客户赖账增多，可**调大**该值（现金流会变差）。
                * **DIO (存货天数 - Days Inventory Outstanding)**
                  * **用途是什么**：衡量货物从生产出来到最终卖掉，平均要在仓库里躺几天。
                  * **默认值建议**：系统默认一般在 30 天左右。
                  * **什么情况下调整**：重工业、汽车制造或芯片行业（库存积压严重，通常要调高）；生鲜或数字软件（库存几乎为 0，需调低）。
                  * **如何调整**：当行业出现滞销、供应链堵塞时，**调大**该值。
                * **DPO (应付账款天数 - Days Payable Outstanding)**
                  * **用途是什么**：公司平均多少天付钱给上游供应商（即公司“欠供应商钱”的时间）。
                  * **默认值建议**：系统默认通常在 60 天左右。
                  * **什么情况下调整**：当公司对上游供应链话语权强、可以长达几个月不付款时（如大超市、巨头企业）。
                  * **如何调整**：若想测试公司“空手套白狼”的极限现金流能力，**调大**该值会让短期自由现金流变好。
                * **Capex % of Revenue (资本开支占营收比例)**
                  * **用途是什么**：公司每年拿多少比例的收入去买厂房、机器、服务器等固定资产。
                  * **默认值建议**：系统根据行业自动适配（科技轻资产约 3-5%, 重资产制造可达 10-15%）。
                  * **什么情况下调整**：当公司正处于疯狂砸钱扩产的周期（如建新厂、买大批 AI 服务器），或者已经轻资产化运营。
                  * **如何调整**：扩产期**调高**（现金流流出会变多），维护期**调低**。
                """

                guide_t2_en = """
                * **DSO (Days Sales Outstanding)**
                  * **Purpose**: Measures how many days it takes for customers to pay their bills after a sale.
                  * **Default**: System adapts to historical norms (around 45 days). **Beginners can keep the default**.
                  * **When to adjust**: Increase for industries with heavy delayed payments (e.g., construction). Decrease for fast cash businesses (e.g., retail, SaaS).
                  * **How to adjust**: **Increase** if macro credit is tight and clients delay payments (worsens cash flow).
                * **DIO (Days Inventory Outstanding)**
                  * **Purpose**: Measures how long inventory sits in the warehouse before being sold.
                  * **Default**: Typically around 30 days.
                  * **When to adjust**: Adjust higher for heavy manufacturing or auto sectors. Adjust lower for perishable goods or digital software.
                  * **How to adjust**: **Increase** if you expect supply chain blockages or unsold stock buildup.
                * **DPO (Days Payable Outstanding)**
                  * **Purpose**: Measures how long the company takes to pay its suppliers.
                  * **Default**: Usually around 60 days.
                  * **When to adjust**: When testing companies with massive supply-chain pricing power (e.g., Walmart, Apple) who can delay supplier payments for months.
                  * **How to adjust**: **Increase** this to test the company's ability to artificially boost short-term FCF.
                * **Capex % of Revenue**
                  * **Purpose**: The percentage of annual revenue spent on buying physical assets (factories, servers, equipment).
                  * **Default**: System adapts (Tech ~3-5%, Heavy Manufacturing ~10-15%).
                  * **When to adjust**: Adjust during massive expansion phases (e.g., buying AI data centers) or transitioning to asset-light.
                  * **How to adjust**: **Increase** during growth phases (reduces FCF), **decrease** during maintenance phases.
                """

                with st.expander(exp_title_t2, expanded=False):
                    st.markdown(guide_t2_zh if lang_key == "zh" else guide_t2_en)

                with st.container(border=True):
                    st.markdown("**🔧 Operating Assumptions (NWC & Capex Drivers)**")
                    o_col1, o_col2, o_col3, o_col4 = st.columns(4)
                    dso = o_col1.number_input("Days Sales Outstanding (DSO)", value=45)
                    dio = o_col2.number_input("Days Inventory Outstanding (DIO)", value=30)
                    dpo = o_col3.number_input("Days Payable Outstanding (DPO)", value=60)
                    capex_pct = o_col4.number_input("Capex as % of Revenue", value=5.0) / 100.0

                df_is = engine.build_hardcore_3_statement(dso, dio, dpo, capex_pct)
                styled_df = df_is.copy()
                for col in styled_df.columns:
                    styled_df[col] = styled_df[col].apply(lambda x: f"{x:,.0f}" if isinstance(x, (int, float)) else x)
                
                st.dataframe(styled_df, use_container_width=True, height=320)

            # ==========================================
            # TAB 3: LBO (集成双语指南)
            # ==========================================
            with tab3:
                st.markdown("#### 🏛️ Dynamic LBO Model & Cash Sweep Schedule")
                
                tab3_desc = "此 LBO 沙盘已与 Tab 2 中的硬核无杠杆现金流 (UFCF) 完美联动。" if lang_key == "zh" else "This LBO is perfectly linked to the Hardcore UFCF generated in Tab 2."
                st.caption(tab3_desc)
                
                exp_title_t3 = "📖 【新手必读 / 核心参数调整指南】杠杆收购 (LBO) 模型参数 (点击展开)" if lang_key == "zh" else "📖 [Beginner's Guide] LBO Model Parameters (Click to Expand)"
                
                guide_t3_zh = """
                * **Debt Leverage (LTV % / 债务杠杆比例)**
                  * **用途是什么**：决定收购时向银行借多少钱，占总收购价的百分比。
                  * **默认值建议**：行业经典默认值为 **60%**，**新手建议直接使用默认值**。
                  * **什么情况下调整**：金融市场银根紧缩、银行不愿放贷时（**调低**至 30-40%）；资金面极度宽松、流行高杠杆时（**调高**至 70-80%）。
                  * **如何调整**：通过滑块拖动。比例越高，若公司赚钱，自有资金的翻倍速度（MOIC）越快，但破产风险也同步飙升。
                * **Debt Interest Rate (%) / 债务年化利率**
                  * **用途是什么**：向银行借钱的年利息成本。
                  * **默认值建议**：系统根据当前宏观环境默认合理的基准值（如 8.0%）。
                  * **什么情况下调整**：处于高息加息周期（需手动调高至 9-10% 以上）或低息宽松期。
                  * **如何调整**：根据当下的真实市场贷款利率手动对齐。
                * **Exit EV/EBITDA Multiple / 退出估值倍数**
                  * **用途是什么**：预测 5 年后把公司卖掉时，市场愿意给它的估值倍数。
                  * **默认值建议**：系统默认带入该公司当前的初始估值倍数。
                  * **什么情况下调整**：若认为 5 年后行业会遭遇泡沫破裂（估值杀跌，需**调低**倍数）或者景气度极高（估值溢价，需**调高**倍数）。
                  * **如何调整**：根据对未来市场宏观景气周期的预期来手动增减。
                """

                guide_t3_en = """
                * **Debt Leverage (LTV %)**
                  * **Purpose**: Determines the percentage of the acquisition funded by bank debt.
                  * **Default**: Industry standard is **60%**. **Beginners can keep the default**.
                  * **When to adjust**: **Lower** it (30-40%) during credit crunches when banks are unwilling to lend. **Raise** it (70-80%) during quantitative easing.
                  * **How to adjust**: Use the slider. Higher leverage juices equity returns (MOIC) if cash flow is strong, but skyrockets bankruptcy risk.
                * **Debt Interest Rate (%)**
                  * **Purpose**: The annual interest cost of the leveraged debt.
                  * **Default**: Sensible baseline (around 8.0%).
                  * **When to adjust**: Adjust based on the macroeconomic interest rate cycle (hikes vs. cuts).
                  * **How to adjust**: Align with current real-world syndicated loan rates.
                * **Exit EV/EBITDA Multiple**
                  * **Purpose**: The valuation multiple at which you expect to sell the company in Year 5.
                  * **Default**: System pulls the company's current entry multiple.
                  * **When to adjust**: **Lower** it if you expect a future market crash/multiple contraction. **Raise** it if you expect massive sector hype in 5 years.
                  * **How to adjust**: Adjust based on your macro thesis for the exit year.
                """

                with st.expander(exp_title_t3, expanded=False):
                    st.markdown(guide_t3_zh if lang_key == "zh" else guide_t3_en)

                col_l1, col_l2, col_l3 = st.columns(3)
                ltv = col_l1.slider("Debt Leverage (LTV %)", 30, 80, 60, 5) / 100
                int_rate = col_l2.slider("Debt Interest Rate (%)", 5.0, 15.0, 8.0, 0.5) / 100
                exit_mult = col_l3.slider("Exit EV/EBITDA Multiple", 5.0, 25.0, max(5.0, (engine.ev/engine.ebitda if engine.ebitda>0 else 10.0)), 0.5)

                lbo_res = engine.run_lbo_model(ltv, int_rate, exit_mult)
                
                c_res1, c_res2, c_res3 = st.columns(3)
                c_res1.metric("Sponsor IRR (5-Year)", f"{lbo_res['IRR']*100:.1f}%")
                c_res2.metric("MOIC (Cash-on-Cash)", f"{lbo_res['MOIC']:.2f}x")
                c_res3.metric("Total Debt Paid Down", f"{engine.currency} {(lbo_res['Debt'] - lbo_res['Exit Debt'])/1e9:.2f}B")

                st.markdown("**Sources & Uses (Entry)**")
                su_df = pd.DataFrame({
                    "Sources": ["Sponsor Equity", "Senior Debt", "Total Sources"],
                    "Amount": [lbo_res['Equity'], lbo_res['Debt'], lbo_res['Entry EV']],
                    "%": [f"{(1-ltv)*100:.1f}%", f"{ltv*100:.1f}%", "100.0%"]
                })
                su_df['Amount'] = su_df['Amount'].apply(lambda x: f"{x:,.0f}" if isinstance(x, (int, float)) else x)
                st.table(su_df)

                st.markdown("**Debt Schedule & Cash Sweep**")
                debt_df = pd.DataFrame({"Year": ["0 (Entry)", "1", "2", "3", "4", "5"], "Ending Debt Balance": lbo_res['Debt Schedule']})
                debt_df['Ending Debt Balance'] = debt_df['Ending Debt Balance'].apply(lambda x: f"{x:,.0f}" if isinstance(x, (int, float)) else x)
                st.table(debt_df.set_index('Year').T)

            # ==========================================
            # TAB 4, 5, 6
            # ==========================================
            with tab4:
                comp_title = "#### 🏢 相对估值矩阵 (同业可比公司)" if lang_key == "zh" else "#### 🏢 Comparable Company Analysis (Peer Valuation Matrix)"
                st.markdown(comp_title)
                st.dataframe(engine.run_comps_analysis(), use_container_width=True)

            with tab5:
                mc_title = "#### 🎲 蒙特卡洛估值模拟 (2,000次随机漫步)" if lang_key == "zh" else "#### 🎲 Monte Carlo Valuation Simulation (2,000 Iterations)"
                st.markdown(mc_title)
                mc_results = engine.run_monte_carlo(2000)
                if mc_results:
                    mc_mean = np.mean(mc_results)
                    mc_p10, mc_p90 = np.percentile(mc_results, 10), np.percentile(mc_results, 90)
                    mc1, mc2, mc3 = st.columns(3)
                    
                    mc1.metric("Monte Carlo Mean Value" if lang_key == "en" else "蒙特卡洛均值公道价", f"{engine.currency} {mc_mean:.2f}")
                    mc2.metric("10% Bear Case (Floor)" if lang_key == "en" else "10% 最差情况底线", f"{engine.currency} {mc_p10:.2f}")
                    mc3.metric("90% Bull Case (Ceiling)" if lang_key == "en" else "90% 极佳情况上限", f"{engine.currency} {mc_p90:.2f}")
                    
                    fig_mc = px.histogram(x=mc_results, nbins=50, title="Intrinsic Value Probability Distribution" if lang_key == "en" else "内在价值概率分布图", labels={'x': 'Fair Value', 'y': 'Frequency'})
                    fig_mc.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#94a3b8'))
                    st.plotly_chart(fig_mc, use_container_width=True)

            with tab6:
                st.markdown("#### 📈 Markowitz Efficient Frontier & Portfolio Optimization")
                
                exp_title_t6 = "📖 【新手必读 / 使用指南】马科维茨有效前沿资产配置 (点击展开)" if lang_key == "zh" else "📖 [Beginner's Guide] Markowitz Efficient Frontier (Click to Expand)"
                
                guide_t6_zh = """
                * **用途是什么**：根据现代资产组合理论，把几只股票放在一起进行数学优化，算出怎么分配资金才能做到“风险最低、收益最高”。
                * **默认值建议**：系统自带一组精选跨国科技巨头（美股：`NVDA, AAPL, MSFT, GOOGL, AMZN`）或马股银行组合，**可以直接点击运行测试**。
                * **什么情况下调整**：当你拥有自己的一篮子自选股，想知道每只股票具体该买多少比例资金时。
                * **如何调整**：直接在输入框中用**英文逗号**隔开输入你想要的股票代码（例如 `TSLA, AAPL, AMD`），然后点击下方的 **Run Portfolio Optimization** 运行按钮即可。
                """

                guide_t6_en = """
                * **Purpose**: Based on Modern Portfolio Theory, it mathematically optimizes an asset basket to find the exact capital allocation that yields the highest return for the lowest risk.
                * **Default**: The system provides a preset basket of tech giants (`NVDA, AAPL, MSFT, GOOGL, AMZN`) or local bank blue-chips. **You can directly click Run to test it.**
                * **When to adjust**: When you have your own personal watchlist and want to know exactly what percentage of cash to allocate to each stock.
                * **How to adjust**: Enter your desired tickers separated by a **comma** (e.g., `TSLA, AAPL, AMD`), then click the **Run Portfolio Optimization** button below.
                """

                with st.expander(exp_title_t6, expanded=False):
                    st.markdown(guide_t6_zh if lang_key == "zh" else guide_t6_en)

                basket_input = st.text_input("Asset Basket Tickers (Comma-separated)", value="NVDA, AAPL, MSFT, GOOGL, AMZN" if not engine.is_malaysia else "1155.KL, 1023.KL, 1295.KL, 5819.KL")
                tickers_list = [t.strip().upper() for t in basket_input.split(",") if t.strip()]
                
                if st.button("🚀 Run Portfolio Optimization" if lang_key == "en" else "🚀 运行资产组合最优化计算"):
                    with st.spinner("Simulating portfolios..." if lang_key == "en" else "正在进行蒙特卡洛组合演练..."):
                        try:
                            data = yf.download(tickers_list, period="1y", interval="1d", session=engine.session)['Close']
                            if isinstance(data, pd.Series): data = data.to_frame()
                            returns = data.pct_change().dropna()
                            num_portfolios = 3000
                            results_matrix = np.zeros((3 + len(tickers_list), num_portfolios))
                            mean_returns, cov_matrix = returns.mean() * 252, returns.cov() * 252
                            
                            for p in range(num_portfolios):
                                weights = np.random.random(len(tickers_list))
                                weights /= np.sum(weights)
                                p_ret = np.sum(mean_returns * weights)
                                p_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
                                results_matrix[0, p], results_matrix[1, p], results_matrix[2, p] = p_ret, p_vol, (p_ret - 0.03) / p_vol 
                                for i, w in enumerate(weights): results_matrix[3 + i, p] = w
                                
                            max_sharpe_idx = np.argmax(results_matrix[2])
                            opt_weights = results_matrix[3:, max_sharpe_idx]
                            
                            opt1, opt2 = st.columns(2)
                            opt1.metric("Optimal Portfolio Return", f"{results_matrix[0, max_sharpe_idx]*100:.2f}%")
                            opt2.metric("Optimal Portfolio Volatility", f"{results_matrix[1, max_sharpe_idx]*100:.2f}%")
                            
                            weight_df = pd.DataFrame({"Asset": tickers_list, "Weight (%)": [f"{w*100:.1f}%" for w in opt_weights]})
                            st.table(weight_df.set_index('Asset').T)
                            
                            fig_ef = px.scatter(x=results_matrix[1], y=results_matrix[0], color=results_matrix[2], labels={'x': 'Volatility (Risk)', 'y': 'Expected Return', 'color': 'Sharpe Ratio'}, title="Markowitz Efficient Frontier")
                            fig_ef.add_trace(go.Scatter(x=[results_matrix[1, max_sharpe_idx]], y=[results_matrix[0, max_sharpe_idx]], mode='markers', marker=dict(color='yellow', size=15, symbol='star'), name='Max Sharpe Portfolio'))
                            fig_ef.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#94a3b8'))
                            st.plotly_chart(fig_ef, use_container_width=True)
                        except Exception as e:
                            st.error(f"Error fetching basket data: {e}")

            # ==========================================
            # TAB 7: 期权与智能策略 (完整中英切换指南)
            # ==========================================
            with tab7:
                st.markdown("#### 📉 Options Chain, Volatility Smile & AI Strategist")
                tab7_cap = "综合期权定价、隐含波动率斜面分析，以及针对持股者与投机者的智能策略推荐。" if lang_key == "zh" else "Comprehensive option pricing, volatility skew analysis, and AI strategy recommendations for hedgers and speculators."
                st.caption(tab7_cap)
                
                if engine.is_malaysia:
                    mal_warn = "⚠️ 马股（Bursa Malaysia）期权数据在 Yahoo Finance 上极度稀疏。建议切换至美股代码（如 NVDA, AAPL, TSLA）体验完整的期权与波动率微笑分析！" if lang_key == "zh" else "⚠️ Bursa Malaysia options data is highly sparse on Yahoo Finance. Test US equities (e.g. NVDA, AAPL) for full volatility smile functionality."
                    st.warning(mal_warn)
                
                try:
                    exp_dates = engine.stock.options
                    if exp_dates:
                        selected_expiry = st.selectbox("📅 选择期权到期日 (Select Expiration Date)" if lang_key == "zh" else "📅 Select Expiration Date", options=exp_dates)
                        opt_chain = engine.stock.option_chain(selected_expiry)
                        calls = opt_chain.calls
                        puts = opt_chain.puts
                        
                        exp_dt = datetime.datetime.strptime(selected_expiry, "%Y-%m-%d")
                        T_days = (exp_dt - datetime.datetime.now()).days
                        T_years = max(T_days / 365.0, 0.01)
                        r = engine.rf
                        S = engine.price

                        opt_tab1, opt_tab2, opt_tab3, opt_tab4 = st.tabs([
                            "📈 隐含波动率微笑 (Volatility Smile)" if lang_key == "zh" else "📈 Volatility Smile / Skew", 
                            "🛡️ 实时期权链与希腊字母矩阵" if lang_key == "zh" else "🛡️ Live Option Chain & Greeks", 
                            "🧮 独立 B-S 仿真沙盘 (Interactive Sandbox)" if lang_key == "zh" else "🧮 BS Interactive Sandbox",
                            "💡 AI 智能期权策略顾问 (AI Strategist) ⭐" if lang_key == "zh" else "💡 AI Options Strategist ⭐"
                        ])
                        
                        with opt_tab1:
                            st.markdown(f"**Volatility Smile / Skew for Expiry: {selected_expiry} (Days to maturity: {T_days})**")
                            fig_smile = go.Figure()
                            
                            if not calls.empty and 'impliedVolatility' in calls.columns:
                                valid_calls = calls[(calls['impliedVolatility'] > 0.01) & (calls['impliedVolatility'] < 3.0)]
                                fig_smile.add_trace(go.Scatter(x=valid_calls['strike'], y=valid_calls['impliedVolatility']*100, mode='markers+lines', name='Calls IV (%)', marker=dict(color='#38bdf8', size=6)))
                            
                            if not puts.empty and 'impliedVolatility' in puts.columns:
                                valid_puts = puts[(puts['impliedVolatility'] > 0.01) & (puts['impliedVolatility'] < 3.0)]
                                fig_smile.add_trace(go.Scatter(x=valid_puts['strike'], y=valid_puts['impliedVolatility']*100, mode='markers+lines', name='Puts IV (%)', marker=dict(color='#ef4444', size=6)))
                            
                            fig_smile.add_vline(x=S, line_dash="dash", line_color="yellow", annotation_text=f"Spot Price: ${S:.2f}")
                            fig_smile.update_layout(xaxis_title="Strike Price ($) ➡️", yaxis_title="Implied Volatility (%) ⬇️", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#94a3b8'), height=400)
                            st.plotly_chart(fig_smile, use_container_width=True)
                            
                            smile_insight = """
                            💡 **机构级波动率微笑与斜面（Volatility Smile / Skew）专业解读：**
                            * **现价对标 (Spot Price)**：图中黄色虚线代表当前股票市价。虚线左侧为价内看涨/价外看跌，右侧反之。
                            * **下行避险溢价 (Downside Skew)**：在实际市场中，虚值看跌期权 (OTM Puts，位于黄线左侧) 的隐含波动率往往远高于平值或看涨期权，形成向左上倾斜的‘微笑曲线’。这反映了机构对**尾部黑天鹅暴跌风险**极其忌惮，愿意支付高昂的溢价来购买防跌保险。
                            """ if lang_key == "zh" else """
                            💡 **Institutional Volatility Smile / Skew Insights:**
                            * **Spot Price**: The yellow dashed line represents the current stock price.
                            * **Downside Skew**: Out-Of-The-Money (OTM) Puts (left of the yellow line) generally command much higher implied volatility than Calls. This upward slope to the left reflects institutional panic pricing—investors are willing to overpay massive premiums to buy insurance against black swan tail risks.
                            """
                            st.info(smile_insight)

                        with opt_tab2:
                            st.markdown("**Live Call Option Chain with Black-Scholes Theoretical Pricing & Greeks**")
                            if not calls.empty:
                                sample_calls = calls.head(15).copy()
                                bs_results = []
                                for _, row in sample_calls.iterrows():
                                    K = row['strike']
                                    iv = row['impliedVolatility'] if row['impliedVolatility'] > 0 else 0.30
                                    greeks = engine.black_scholes_pricing(S, K, T_years, r, iv, q=0.0)
                                    bs_results.append({
                                        "Strike": K, "Market Price": row['lastPrice'], "BS Fair Price": round(greeks['Call'], 2),
                                        "IV (%)": round(iv * 100, 1), "Delta": round(greeks['Delta_C'], 2), "Gamma": round(greeks['Gamma'], 3),
                                        "Theta": round(greeks['Theta_C'], 2), "Vega": round(greeks['Vega'], 2)
                                    })
                                bs_df = pd.DataFrame(bs_results)
                                st.dataframe(bs_df, use_container_width=True)
                                
                                # 🌟 新增的希腊字母解释展开项 (Greeks Expander)
                                exp_title_greeks = "📖 【新手必读 / 希腊字母百科】这些期权参数代表什么风险？ (点击展开)" if lang_key == "zh" else "📖 [Beginner's Guide] Understanding Options Greeks (Click to Expand)"
                                
                                guide_greeks_zh = """
                                * **Delta (Δ - 方向与概率)**:
                                  * **含义**: 衡量股价每涨跌 1$，期权价格理论上跟着变动多少。
                                  * **实战**: Delta = 0.5 代表股票涨 1 块，期权理论涨 0.5 块。它也常被华尔街用来粗估期权到期时变成价内 (ITM) 的概率（例如 Delta 0.30 约等于只有 30% 胜率）。
                                * **Gamma (Γ - 爆发力与加速度)**:
                                  * **含义**: 衡量 Delta 的变化速度（即 Delta 的加速度）。
                                  * **实战**: Gamma 越高，期权价格随股价波动的幅度越剧烈。平值期权 (ATM) 临近到期时 Gamma 达到最大，俗称“末日轮”的疯狂翻倍或瞬间归零，就是极高的 Gamma 导致的。
                                * **Theta (Θ - 时间损耗)**:
                                  * **含义**: 距离到期日每过去一天，你的期权会自动蒸发多少价值。
                                  * **实战**: 期权买方的“死神”，卖方的“提款机”。临近到期时，时间价值流失会疯狂加速（Theta 绝对值变大）。
                                * **Vega (ν - 恐慌与波动率)**:
                                  * **含义**: 市场隐含波动率 (IV) 每上升 1%，期权会变贵多少。
                                  * **实战**: 财报前大家恐慌买保险，IV 暴涨，期权也随之变贵。财报后 IV 瞬间暴跌（IV Crush），买方往往会遭遇“哪怕股价方向看对了，但期权还是亏钱”的惨剧。
                                """

                                guide_greeks_en = """
                                * **Delta (Δ - Direction & Probability)**:
                                  * **Meaning**: How much the option premium changes for a $1 move in the underlying stock.
                                  * **Practical**: A 0.50 Delta means the option gains $0.50 for every $1 stock rise. It is also widely used as a proxy for the probability of expiring In-The-Money (ITM).
                                * **Gamma (Γ - Acceleration & Convexity)**:
                                  * **Meaning**: The rate of change of Delta.
                                  * **Practical**: High Gamma means the option's sensitivity changes rapidly. At-The-Money (ATM) options close to expiration have the highest Gamma, creating explosive, lottery-like price swings.
                                * **Theta (Θ - Time Decay)**:
                                  * **Meaning**: How much value the option loses each passing day.
                                  * **Practical**: The enemy of option buyers, the best friend of sellers. Time decay accelerates aggressively as expiration approaches.
                                * **Vega (ν - Volatility & Panic)**:
                                  * **Meaning**: How much the option price changes for a 1% shift in Implied Volatility (IV).
                                  * **Practical**: Options get extremely expensive before Earnings due to surging Vega. After Earnings, IV collapses (IV Crush), which can cause buyers to lose money even if they guessed the stock direction correctly.
                                """

                                with st.expander(exp_title_greeks, expanded=False):
                                    st.markdown(guide_greeks_zh if lang_key == "zh" else guide_greeks_en)

                                greeks_note = "✨ *简明注：Delta 测方向；Gamma 测爆发力；Theta 测时间流失；Vega 测波动率影响。*" if lang_key == "zh" else "✨ *TL;DR: Delta = Direction; Gamma = Acceleration; Theta = Time Decay; Vega = Volatility.*"
                                st.caption(greeks_note)

                        with opt_tab3:
                            sandbox_title = "##### 🧮 交互式 Black-Scholes 期权定价器 (支持股息率)" if lang_key == "zh" else "##### 🧮 Interactive Black-Scholes Pricer (Dividend Supported)"
                            sandbox_cap = "手动调整各项因子，观察期权理论价格与希腊字母的敏感度变化。" if lang_key == "zh" else "Manually adjust pricing factors to observe theoretical changes in premiums and Greeks."
                            st.markdown(sandbox_title)
                            st.caption(sandbox_cap)
                            
                            exp_title_t7 = "📖 【新手必读 / 参数详解】Black-Scholes 仿真沙盘调节指南 (点击展开)" if lang_key == "zh" else "📖 [Beginner's Guide] BS Pricer Parameters (Click to Expand)"
                            
                            guide_t7_zh = """
                            * **行权价设定 (%) / 行权价 (K)**
                              * **用途是什么**：决定你想计算或模拟哪个价格的看涨/看跌期权。
                              * **默认值建议**：系统默认 **100%**（即平值期权 At-the-Money，行权价正好等于当前股价），**新手强烈建议从 100% 开始**。
                              * **什么情况下调整**：想测试深度价外（更便宜、以小博大的彩票期权）或者价内期权时调整。
                              * **如何调整**：通过滑动条或直接输入具体金额。
                            * **剩余到期天数 (Days to Maturity)**
                              * **用途是什么**：离这份期权合约失效还有多少天。
                              * **默认值建议**：系统默认 **30 天**（标准的月度期权）。
                              * **什么情况下调整**：想看周权（如 7 天，时间价值损耗极快）或者长线期权（LEAPS，如 365 天）的价格。
                              * **如何调整**：根据你想模拟的合约期限直接修改天数。
                            * **波动率 (Volatility σ %)**
                              * **用途是什么**：市场对该股票未来剧烈震荡的预期。波动率越高，期权越贵（因为暴涨暴跌概率大）。
                              * **默认值建议**：系统默认提取合理的初始值（如 35%）。
                              * **什么情况下调整**：当公司即将发布财报（财报前波动率会暴增，可调高至 60-80%）；或者大盘风平浪静、股价死水一潭时（可调低至 15-20%）。
                              * **如何调整**：预期有大事件（如大选、财报）时**调高**；风平浪静时**调低**。
                            * **无风险利率 (Risk-Free Rate r %) & 股息率 (Dividend Yield q %)**
                              * **用途是什么**：折现因子与分红对期权定价的微调影响。
                              * **默认值建议**：**小白用户强烈建议直接保持默认**，不需要频繁手动更改。
                            """

                            guide_t7_en = """
                            * **Strike Price Setting (%) / Strike (K)**
                              * **Purpose**: Determines the strike price for the simulated option.
                              * **Default**: System defaults to **100%** (At-the-Money, strike equals spot price). **Beginners should stick to 100%**.
                              * **When to adjust**: To simulate deep Out-of-the-Money (lottery-ticket cheap options) or In-the-Money options.
                            * **Days to Maturity**
                              * **Purpose**: Time left until the contract expires.
                              * **Default**: Defaults to **30 days**.
                              * **When to adjust**: Decrease to 7 days for weekly options (high Theta decay), or increase to 365 days for LEAPS.
                            * **Volatility (Volatility σ %)**
                              * **Purpose**: Market's expectation of future turbulence. Higher IV = More expensive options.
                              * **Default**: Realistic baseline (around 35%).
                              * **When to adjust**: **Increase** drastically (60-80%) right before Earnings or major events. **Decrease** during calm, sideways markets.
                            * **Risk-Free Rate (r %) & Dividend Yield (q %)**
                              * **Purpose**: Discounting and dividend adjustments for European pricing models.
                              * **Default**: **Keep defaults unless you are doing advanced arbitrage calculations.**
                            """

                            with st.expander(exp_title_t7, expanded=False):
                                st.markdown(guide_t7_zh if lang_key == "zh" else guide_t7_en)

                            op_col1, op_col2, op_col3 = st.columns(3)
                            strike_pct = op_col1.slider("行权价设定 (% 相对现价)" if lang_key == "zh" else "Strike Price Setting (%)", 80, 120, 100, 1) / 100
                            K_default = engine.price * strike_pct
                            custom_K = op_col2.number_input("行权价 (Strike K)" if lang_key == "zh" else "Strike (K)", value=float(K_default), format="%.2f")
                            custom_T_days = op_col3.number_input("剩余到期天数 (Days to Maturity)" if lang_key == "zh" else "Days to Maturity", value=30, min_value=1, max_value=730)
                            custom_T_years = custom_T_days / 365.0

                            op_col4, op_col5, op_col6 = st.columns(3)
                            custom_vol = op_col4.slider("波动率 (Volatility σ %)" if lang_key == "zh" else "Volatility (IV σ %)", 10.0, 150.0, 35.0, 1.0) / 100.0
                            custom_r_rate = op_col5.slider("无风险利率 (Risk-Free Rate r %)" if lang_key == "zh" else "Risk-Free Rate (r %)", 1.0, 10.0, float(engine.rf * 100), 0.1) / 100.0
                            custom_div_yield = op_col6.slider("股息率 (Dividend Yield q %)" if lang_key == "zh" else "Dividend Yield (q %)", 0.0, 10.0, 1.5, 0.1) / 100.0

                            custom_greeks = engine.black_scholes_pricing(engine.price, custom_K, custom_T_years, custom_r_rate, custom_vol, custom_div_yield)

                            st.markdown("##### 💎 B-S 公允估值结果" if lang_key == "zh" else "##### 💎 B-S Fair Value Results")
                            res_c1, res_c2 = st.columns(2)
                            res_c1.metric("European Call (看涨公道价)" if lang_key == "zh" else "European Call Premium", f"{engine.currency} {custom_greeks['Call']:.4f}")
                            res_c2.metric("European Put (看跌公道价)" if lang_key == "zh" else "European Put Premium", f"{engine.currency} {custom_greeks['Put']:.4f}")

                        with opt_tab4:
                            ai_opt_title = "### 🤖 智能期权策略顾问 (AI Options Strategist)" if lang_key == "zh" else "### 🤖 AI Options Strategist playbook"
                            ai_opt_desc = f"针对 **{engine.ticker}** (当前市价 ${engine.price:.2f})，根据您的持仓状态与对未来走势的判断，推荐以下经典策略：" if lang_key == "zh" else f"Strategy playbook for **{engine.ticker}** (Spot: ${engine.price:.2f}). Recommendations based on position and conviction:"
                            
                            st.markdown(ai_opt_title)
                            st.caption(ai_opt_desc)

                            strategy_col1, strategy_col2 = st.columns(2)

                            # AI Strategist Language Parsing Logic
                            if lang_key == "zh":
                                h_title = "#### 🛡️ 持股防御与收息派 (Hedging & Income)"
                                s_title = "#### ⚔️ 纯投机与波动率派 (Speculation & Volatility)"
                                
                                # Strategy 1
                                c1_t = "1. 备兑看涨期权 (Covered Call) - 赚取额外被动收入"
                                c1_1 = f"- **🎯 适合对象:** 你已经持有至少 100 股 {engine.ticker} 正股，并且觉得它短期内不会暴涨。"
                                c1_2 = f"- **🛠️ 操作方案:** **卖出** 1 张虚值 (OTM) 看涨期权 (Call)，比如行权价设在 ${(engine.price * 1.05):.2f} (现价的 105%)。"
                                c1_3 = f"- **📈 预期效果:** 你将立刻收到一笔期权费（权利金）。如果到期前股价**没有**涨过 ${(engine.price * 1.05):.2f}，期权作废，你白赚这笔钱，可以反复操作降低持仓成本；如果涨破了，你的股票会按 ${(engine.price * 1.05):.2f} 被强制卖出（你依然赚了 5% 的差价 + 期权费，只是错过了更高的利润）。"
                                
                                # Strategy 2
                                c2_t = "2. 保护性看跌 (Protective Put) - 买保险防暴跌"
                                c2_1 = f"- **🎯 适合对象:** 你持有 {engine.ticker} 正股，害怕即将到来的财报暴雷或大盘崩盘，但又不想卖掉股票（比如为了避税或长期看好）。"
                                c2_2 = f"- **🛠️ 操作方案:** **买入** 1 张虚值看跌期权 (Put)，比如行权价设在 ${(engine.price * 0.9):.2f}。"
                                c2_3 = f"- **📈 预期效果:** 类似于给车买车险。付出一笔保费，如果股票真的腰斩，你有权在 ${(engine.price * 0.9):.2f} 这个价位强制卖出。无论跌多惨，你的最大损失都被锁死在 10% 以内。"
                                
                                # Strategy 3
                                c3_t = "3. 领型期权 (Collar Strategy) - 零成本对冲保险"
                                c3_1 = f"- **🎯 适合对象:** 想买 Put 保护正股，但觉得期权费（保费）太贵了，不舍得花钱。"
                                c3_2 = f"- **🛠️ 操作方案:** **买入** 1 张 OTM Put 防暴跌，同时 **卖出** 1 张 OTM Call 赚权利金来补贴买 Put 的钱。"
                                c3_3 = f"- **📈 预期效果:** 几乎“零成本”上保险。代价是：你不仅封死了下跌空间，也把向上暴涨的利润空间给封死了。非常适合想安心睡大觉的长期投资者。"
                                
                                # Strategy 4
                                s1_t = "1. 牛市看涨价差 (Bull Call Spread) - 以小博大，控制风险"
                                s1_1 = f"- **🎯 适合对象:** 强烈看涨 {engine.ticker}，但觉得直接买 Call 太贵，且不想承受太大的时间损耗 (Theta)。"
                                s1_2 = f"- **🛠️ 操作方案:** **买入** 1 张平值 (ATM) Call，同时 **卖出** 1 张更高行权价的虚值 (OTM) Call。"
                                s1_3 = f"- **📈 预期效果:** 卖 Call 收到的钱抵消了部分买 Call 的成本，大大降低了你的入场费。你的最大亏损变小了，但在暴涨情况下的最大利润也被封顶了。适合“稳中求胜”的投机者。"
                                
                                # Strategy 5
                                s2_t = "2. 铁鹰 / 蝴蝶期权 (Iron Condor / Butterfly) - 震荡市收割机"
                                s2_1 = f"- **🎯 适合对象:** 预测 {engine.ticker} 接下来一段时间会**横盘震荡**，不会大涨也不会大跌。"
                                s2_2 = f"- **🛠️ 操作方案 (铁鹰):** 卖出一个 OTM Call Spread，同时卖出一个 OTM Put Spread（构建一个无风险的盈利区间）。"
                                s2_3 = f"- **📈 预期效果:** 时间 (Theta) 是你最好的朋友。只要股价在到期日乖乖待在中间的区间里，四大期权全部作废，你安稳收割所有的期权费。"
                                
                                # Strategy 6
                                s3_t = "3. 跨式组合 (Straddle) - 押注大事件与财报方向"
                                s3_1 = f"- **🎯 适合对象:** 马上要发财报了，你预感 {engine.ticker} 会有**剧烈波动（非暴涨即暴跌）**，但你**不知道方向**。"
                                s3_2 = f"- **🛠️ 操作方案:** 同时 **买入** 1 张同等行权价的 Call 和 Put。"
                                s3_3 = f"- **📈 预期效果:** 你付出了两份高昂的期权费。只要最终股票的涨跌幅超过了你付出的总期权费成本，哪怕其中一边归零，另一边的暴涨也能让你大幅盈利。最怕的是“雷声大雨点小”（横盘），这样两边的钱都会输光。"
                            
                            else:
                                h_title = "#### 🛡️ Hedgers & Income Seekers"
                                s_title = "#### ⚔️ Speculators & Volatility Seekers"
                                
                                # Strategy 1
                                c1_t = "1. Covered Call - Passive Income Generator"
                                c1_1 = f"- **🎯 Best For:** You own at least 100 shares of {engine.ticker} and expect a neutral to slightly bullish market."
                                c1_2 = f"- **🛠️ Action:** **Sell** 1 Out-of-the-Money (OTM) Call, e.g., Strike ${(engine.price * 1.05):.2f}."
                                c1_3 = f"- **📈 Expected Result:** You instantly collect a premium. If the stock stays below ${(engine.price * 1.05):.2f}, you keep the cash. If it surges, your shares are called away at a 5% profit. Win-win, but upside is capped."
                                
                                # Strategy 2
                                c2_t = "2. Protective Put - Crash Insurance"
                                c2_1 = f"- **🎯 Best For:** You own {engine.ticker} but fear an upcoming earnings miss or macro crash, yet you don't want to sell."
                                c2_2 = f"- **🛠️ Action:** **Buy** 1 OTM Put, e.g., Strike ${(engine.price * 0.9):.2f}."
                                c2_3 = f"- **📈 Expected Result:** You pay a premium (insurance fee). No matter how far the stock plummets, your max loss is strictly capped at 10%. Perfect for downside protection."
                                
                                # Strategy 3
                                c3_t = "3. Collar Strategy - Zero-Cost Hedge"
                                c3_1 = f"- **🎯 Best For:** You want a Protective Put but don't want to pay the expensive premium."
                                c3_2 = f"- **🛠️ Action:** **Buy** an OTM Put AND **Sell** an OTM Call simultaneously."
                                c3_3 = f"- **📈 Expected Result:** The premium received from the Call finances the Put. You lock in a hard floor for losses, but completely surrender any breakout profits. Total peace of mind."
                                
                                # Strategy 4
                                s1_t = "1. Bull Call Spread - Leveraged Upside"
                                s1_1 = f"- **🎯 Best For:** Highly bullish on {engine.ticker} but naked Calls are too expensive (high IV)."
                                s1_2 = f"- **🛠️ Action:** **Buy** 1 ATM Call AND **Sell** 1 higher OTM Call."
                                s1_3 = f"- **📈 Expected Result:** Massively reduces capital entry requirement and mitigates time decay (Theta). Max loss is low, but max profit is rigidly capped."
                                
                                # Strategy 5
                                s2_t = "2. Iron Condor - Sideways Harvester"
                                s2_1 = f"- **🎯 Best For:** You expect {engine.ticker} to chop sideways (low volatility)."
                                s2_2 = f"- **🛠️ Action:** Sell an OTM Call Spread AND an OTM Put Spread."
                                s2_3 = f"- **📈 Expected Result:** Theta (time) is your friend. As long as the stock remains within the defined corridor by expiry, all options expire worthless, and you harvest the total premium."
                                
                                # Strategy 6
                                s3_t = "3. Straddle - Earnings Volatility Play"
                                s3_1 = f"- **🎯 Best For:** Major binary event upcoming (Earnings, FDA trial). You expect massive movement but **don't know the direction**."
                                s3_2 = f"- **🛠️ Action:** **Buy** 1 ATM Call AND **Buy** 1 ATM Put."
                                s3_3 = f"- **📈 Expected Result:** Very expensive upfront. But as long as the stock violently crashes or skyrockets beyond the breakeven cost, profit is infinite. Worst case scenario: the stock chops sideways."

                            with strategy_col1:
                                with st.container(border=True):
                                    st.markdown(h_title)
                                    
                                    with st.expander(c1_t, expanded=True):
                                        st.markdown(c1_1)
                                        st.markdown(c1_2)
                                        st.markdown(c1_3)
                                        
                                    with st.expander(c2_t):
                                        st.markdown(c2_1)
                                        st.markdown(c2_2)
                                        st.markdown(c2_3)
                                        
                                    with st.expander(c3_t):
                                        st.markdown(c3_1)
                                        st.markdown(c3_2)
                                        st.markdown(c3_3)

                            with strategy_col2:
                                with st.container(border=True):
                                    st.markdown(s_title)
                                    
                                    with st.expander(s1_t, expanded=True):
                                        st.markdown(s1_1)
                                        st.markdown(s1_2)
                                        st.markdown(s1_3)

                                    with st.expander(s2_t):
                                        st.markdown(s2_1)
                                        st.markdown(s2_2)
                                        st.markdown(s2_3)

                                    with st.expander(s3_t):
                                        st.markdown(s3_1)
                                        st.markdown(s3_2)
                                        st.markdown(s3_3)
                                        
                    else:
                        st.warning("⚠ No option expiration dates found for this ticker on Yahoo Finance.")
                except Exception as e:
                    st.error(f"Unable to fetch option chain data: {e}")

    # [模块 12：免责声明]
    st.markdown("---")
    with st.container(border=True):
        st.markdown(f"### {T['disclaimer_title']}")
        st.markdown(T['disclaimer_1'])
        st.markdown(T['disclaimer_2'])
        st.markdown(T['disclaimer_3'])
        st.markdown("")
        st.markdown(
            "<div style='text-align: center; color: #94a3b8; font-size: 12px; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 10px;'>"
            "© 2026 Thomas. All rights reserved. | Developed for Academic & Quantitative Research."
            "</div>", 
            unsafe_allow_html=True
        )

if __name__ == '__main__':
    main()
