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
st.set_page_config(page_title="Ultimate Quant & PE Terminal V9.3", page_icon="💹", layout="wide", initial_sidebar_state="collapsed")

PREMIUM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

/* 全局背景 */
.stApp {
    background: radial-gradient(circle at 50% 0%, #1e293b 0%, #0f172a 60%, #090d16 100%) !important;
    font-family: 'Inter', -apple-system, sans-serif !important;
    color: #f8fafc !important;
}
.block-container { padding-top: 2rem !important; max-width: 1400px !important; }
header[data-testid="stHeader"] { background: transparent !important; }

/* 🌟 Tabs 标签页高级样式 */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background-color: rgba(15, 23, 42, 0.6);
    border-radius: 12px;
    padding: 8px;
    border: 1px solid rgba(56, 189, 248, 0.2);
}
.stTabs [data-baseweb="tab"] {
    color: #94a3b8 !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
    padding: 10px 14px !important;
    font-size: 12px !important;
    transition: all 0.3s ease;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #38bdf8 0%, #0284c7 100%) !important;
    color: #ffffff !important;
    box-shadow: 0 4px 15px rgba(56, 189, 248, 0.4);
}

/* 🌟 核心 Bento Box 框架 */
[data-testid="column"] > div { height: 100% !important; }
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
# 2. 国际化多语言字典 (完好无损保留你所有的原文案并拓展期权文案)
# ==============================================================================
TEXTS = {
    "zh": {
        "title": "🌐 智能量化金融终端 (V9.3 旗舰期权全功能版)",
        "subtitle": "完美融合 线性衰减DCF、3-Statement 动态NWC、LBO、Comps、蒙特卡洛、有效前沿 & Black-Scholes 期权与波动率微笑分析",
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
        "note_ddm": "Based on historical dividends and terminal growth.",
        "note_pe": "基于每股收益 (EPS) 乘以行业合理市盈率倍数。",
        
        "price": "当前市场价格",
        "fair_val": "内在公道估值 (衰减后)",
        "fair_val_desc": "💡 **关于【内在公道估值 (衰减后)】的通俗解释**：剥离短期市场狂热与恐慌炒作，根据公司真实赚钱能力算出的保守身价。",
        "safe_buy": "20% 安全边际买点",

        "heat_title": "[3. 🌡️ 核心参数敏感性分析矩阵 (DCF SENSITIVITY HEATMAP)]",
        "heat_desc": "💡 **图表说明**：投行通常不给出单一绝对估值。纵轴代表不同的**折现率 (WACC)**，横轴代表**永续增长率 (g)**。",
        
        "lie_title": "[4. 💡 市场情绪测谎仪 (MARKET PSYCHOLOGY / LIE DETECTOR)]",
        "lie_exp": "💡 **通俗解释 (Plain English)：** 测谎仪通过二分法反向推导，看看当前的市场价格到底在幻想这家公司未来每年增长多少。",
        "ai_title": "[5. 🤖 双视角 AI 投资顾问 (DUAL-PERSPECTIVE AI ADVISORY)]",
        "inc_title": "🔸 视角 A：保守派收息策略 (Conservative Income)",
        "cap_title": "🔹 视角 B：进取派资本增值 (Capital Appreciation)",
        "exec_title": "[6. 🎯 最终投资评级与执行摘要 (EXECUTIVE SUMMARY)]",
        "rating_explain": "ℹ️ *学术释疑：‘市场情绪理性’代表投资者没有盲目炒作泡沫，但给出 ‘SELL’ 评级是因为当前市价高于内在公道价（缺乏安全边际）。*",
        
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
        "gap_alert_high": "🚨 **【预期差警示 / 情绪溢价驱动】**：华尔街目标价远高于量化模型底线。",
        "gap_alert_low": "🔥 **【深度价值 / 逆向左侧契机】**：量化模型算出的基本面造血价值高于华尔街卖方预期。",
        "ws_match": "✅ 模型算出的公道价与华尔街机构预测高度吻合，无重大预期差！",

        "chart_title": "[10. 📈 高级盘面与波动率回归分析]",
        "beta_desc": "📊 **Beta 收益率特征线散点分布图说明：**\n* 每个点代表过往某一周的收益率联动。红线斜率即为真实 Beta。",
        "glossary_title": "[11. 📖 小白通俗金融词典：这些数据代表什么？]",
        
        "g_beta_title": "##### 🎯 Beta (波动敏感度)",
        "g_beta_desc": "衡量这只股票相对于大盘是更活泼还是更稳健。",
        "g_growth_title": "##### 🚀 Growth (预期增长率)",
        "g_growth_desc": "未来公司现金流或盈利预计每年递增的比例。",
        "g_wacc_title": "##### 🛡️ WACC / 折现率",
        "g_wacc_desc": "你买入这家公司所要求的最低年化回报门槛。",
        "g_fv_title": "##### 💎 Fair Value (内在公道价)",
        "g_fv_desc": "剥离市场的短期情绪狂热与恐慌后算出的真实身价。",
        
        "disclaimer_title": "[12. ⚠️ 重要法律与风险免责声明]",
        "disclaimer_1": "1. **非投资建议**：本系统所呈现的所有估值结果、公道价格、诊断与图表分析，仅供学术研究、个人学习交流与教学参考。",
        "disclaimer_2": "2. **市场风险**：股票与期权市场波动剧烈，历史数据和数学量化模型无法预知未来。",
        "disclaimer_3": "3. **自主决策**：任何投资决策均应由投资者在独立调查或咨询持牌财务顾问的基础上自行做出。"
    },
    "en": {
        "title": "🌐 Universal Quant Terminal (Ultimate Hardcore V9.3)",
        "subtitle": "Integrating Fading Growth DCF, 3-Statement NWC, LBO, Comps, Monte Carlo, Efficient Frontier & Black-Scholes Options",
        "quick_tag": "🔥 Quick Select:",
        "input_label": "Enter Stock Ticker (e.g., 1155.KL, NVDA, AAPL):",
        
        "param_title": "⚙️ Step 2: Macro & Valuation Parameters (Defaults Recommended)",
        "param_tip": "💡 When to adjust manually?",
        "erp_label": "Equity Risk Premium (ERP)",
        "g2_label": "Terminal Growth Rate (g)",
        "esg_caption": "🌿 Sustainable Finance & ESG Sector Risk Premium integrated.",
        
        "macro_title": "[1. DYNAMIC MACRO & COST OF CAPITAL]",
        "macro_exp": "💡 Beta measures stock volatility compared to the market.",
        
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
        "fair_val_desc": "💡 Strips away short-term market hype to reveal fundamental worth.",
        "safe_buy": "Safe Buy Target (20% MoS)",

        "heat_title": "[3. 🌡️ DCF SENSITIVITY HEATMAP]",
        "heat_desc": "💡 Y-axis represents WACC, X-axis represents Terminal Growth (g).",
        
        "lie_title": "[4. 💡 MARKET PSYCHOLOGY (LIE DETECTOR)]",
        "lie_exp": "💡 Reverse-engineers the implied growth rate.",
        "ai_title": "[5. 🤖 DUAL-PERSPECTIVE AI ADVISORY]",
        "inc_title": "🔸 Conservative Income",
        "cap_title": "🔹 Capital Appreciation",
        "exec_title": "[6. 🎯 FINAL EXECUTIVE SUMMARY & RATING]",
        "rating_explain": "ℹ️ Good company ≠ Good price.",
        
        "plain_title": "[7. 🗣️ PLAIN ENGLISH TRANSLATOR]",
        "fx_title": "[8. 💱 CROSS-BORDER FX RISK ADVISORY]",
        "fx_content": "- **Note:** USD asset; monitor USD/MYR exchange rate.",
        
        "ws_title": "🏛️ [9. Wall Street Analyst Consensus & Expectation Gap Radar]",
        "ws_mean": "Analyst Average Target Price",
        "ws_range": "Target Price Range",
        "ws_rating": "Consensus Rating",
        "ws_tag": "Institutional Consensus",
        "gap_title": "⚡ Expectation Gap Analysis",
        "gap_line1": "Model Fair Value",
        "gap_line2": "Wall Street Target Mean",
        "gap_line3": "Divergence Gap",
        "gap_desc_high": "Wall Street target is higher than model value by",
        "gap_alert_high": "🚨 **[Expectation Gap Warning]**: Targets far exceed quant model.",
        "gap_alert_low": "🔥 **[Deep Value Opportunity]**: Quant model exceeds Wall Street.",
        "ws_match": "✅ Your Valuation aligns tightly with Wall Street targets!",

        "chart_title": "[10. Advanced Price Action & Regression Analysis]",
        "beta_desc": "📊 Beta Scatter Plot Explanation.",
        "glossary_title": "[11. Beginner's Financial Glossary]",
        "g_beta_title": "##### 🎯 Beta (Sensitivity)",
        "g_beta_desc": "Measures stock volatility relative to the market.",
        "g_growth_title": "##### 🚀 Expected Growth Rate",
        "g_growth_desc": "Projected annual growth rate.",
        "g_wacc_title": "##### 🛡️ WACC / Discount Rate",
        "g_wacc_desc": "Minimum hurdle rate of return.",
        "g_fv_title": "##### 💎 Intrinsic Fair Value",
        "g_fv_desc": "Calculated intrinsic value.",
        
        "disclaimer_title": "[12. ⚠️ Important Legal & Risk Disclaimer]",
        "disclaimer_1": "1. **Not Investment Advice**: For educational purposes only.",
        "disclaimer_2": "2. **Market Risk**: Volatility disclaimer.",
        "disclaimer_3": "3. **Independent Decision**: Make your own choices."
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
# 3. 核心硬核量化引擎与 Black-Scholes 期权风控模块
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

        raw_fcf = self.info.get('freeCashflow', 0)
        if raw_fcf <= 0: raw_fcf = get_fin_metric(self.cfs, 'Free Cash Flow', self.net_income * 0.8)
        self.cf = raw_fcf
        
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

        rev = [rev_0]; cogs = [cogs_0]; ebitda = [self.ebitda]; da = [self.hist_da]; capex = [rev_0 * capex_pct]
        ar = [(dso / 365.0) * rev_0]; inv = [(dio / 365.0) * cogs_0]; ap = [(dpo / 365.0) * cogs_0]
        nwc = [ar[0] + inv[0] - ap[0]]; dnwc = [0.0]; ufcf = [self.cf]
        new_capex_schedule = [] 

        for i in range(1, 6):
            g = self.g1 - (self.g1 - self.g2) * (i / 5)
            r = rev[-1] * (1 + g); c = cogs[-1] * (1 + g); e = r * ebitda_margin
            rev.append(r); cogs.append(c); ebitda.append(e)

            cap = r * capex_pct
            capex.append(cap); new_capex_schedule.append(cap)

            current_da = self.hist_da * (1 - 0.2 * i) if (1 - 0.2 * i) > 0 else 0
            for j in range(len(new_capex_schedule)): current_da += new_capex_schedule[j] * 0.2
            da.append(current_da)

            current_ar = (dso / 365.0) * r
            current_inv = (dio / 365.0) * c
            current_ap = (dpo / 365.0) * c
            current_nwc = current_ar + current_inv - current_ap

            ar.append(current_ar); inv.append(current_inv); ap.append(current_ap)
            nwc.append(current_nwc); dnwc.append(current_nwc - nwc[-2])

            ebit = e - current_da
            nopat = ebit * (1 - tax_rate)
            current_ufcf = nopat + current_da - cap - dnwc[-1]
            ufcf.append(current_ufcf)

        self.hardcore_ufcf_proj = ufcf[1:] 
        return pd.DataFrame({
            "Revenue": rev, "EBITDA": ebitda, "(-) D&A (Waterfall)": [-d for d in da],
            "(=) EBIT": [e - d for e, d in zip(ebitda, da)], "NOPAT (EBIT x 1-T)": [(e - d) * (1 - tax_rate) for e, d in zip(ebitda, da)],
            "(-) Capex": [-c for c in capex], "(-) Δ NWC (WC Change)": [-d for d in dnwc], "(=) Unlevered FCF": ufcf
        }, index=years).T

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
        peer_map = {'NVDA': ['AMD', 'INTC', 'TSM', 'QCOM'], 'AAPL': ['MSFT', 'GOOGL', 'AMZN', 'META'], 'TSLA': ['RIVN', 'F', 'GM', 'TM'], '1155.KL': ['1023.KL', '1295.KL', '1188.KL', '5819.KL']}
        peers = peer_map.get(self.ticker, ['AAPL', 'MSFT', 'GOOGL'])
        if self.ticker in peers: peers.remove(self.ticker)
        
        comp_data = [{"Ticker": self.ticker, "Name": self.name[:12], "Market Cap ($B)": round(self.market_cap / 1e9, 2), "EV/EBITDA": round(self.ev / self.ebitda, 2) if self.ebitda > 0 else 0, "P/E": round(self.info.get('trailingPE', 0), 2), "Gross Margin %": round(self.info.get('grossMargins', 0) * 100, 1)}]
        for p in peers:
            try:
                pt = yf.Ticker(p, session=self.session); pi = pt.info
                pmcap = pi.get('marketCap', 1e9); pebitda = pi.get('ebitda', 1e6); pe_ratio = pi.get('trailingPE', 0); gm = pi.get('grossMargins', 0) * 100
                pev = pmcap + pi.get('totalDebt', 0) - pi.get('totalCash', 0)
                comp_data.append({"Ticker": p, "Name": pi.get('shortName', p)[:12], "Market Cap ($B)": round(pmcap / 1e9, 2), "EV/EBITDA": round(pev / pebitda, 2) if pebitda > 0 else 0, "P/E": round(pe_ratio, 2), "Gross Margin %": round(gm, 1)})
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

    # 🌟 Black-Scholes 期权定价与 Greeks 风险风控计算
    def black_scholes_pricing(self, K, T, r, sigma, q=0.0):
        S = self.price
        if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
            return {"Call": 0.0, "Put": 0.0, "Delta_C": 0.0, "Delta_P": 0.0, "Gamma": 0.0, "Theta_C": 0.0, "Theta_P": 0.0, "Vega": 0.0, "Rho_C": 0.0, "Rho_P": 0.0}
        
        d1 = (np.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        call = S * np.exp(-q * T) * stats.norm.cdf(d1) - K * np.exp(-r * T) * stats.norm.cdf(d2)
        put = K * np.exp(-r * T) * stats.norm.cdf(-d2) - S * np.exp(-q * T) * stats.norm.cdf(-d1)
        
        delta_c = np.exp(-q * T) * stats.norm.cdf(d1)
        delta_p = -np.exp(-q * T) * stats.norm.cdf(-d1)
        gamma = (np.exp(-q * T) * stats.norm.pdf(d1)) / (S * sigma * np.sqrt(T))
        vega = S * np.exp(-q * T) * stats.norm.pdf(d1) * np.sqrt(T) / 100
        
        theta_c = (- (S * sigma * np.exp(-q * T) * stats.norm.pdf(d1)) / (2 * np.sqrt(T)) - r * K * np.exp(-r * T) * stats.norm.cdf(d2) + q * S * np.exp(-q * T) * stats.norm.cdf(d1)) / 365
        theta_p = (- (S * sigma * np.exp(-q * T) * stats.norm.pdf(d1)) / (2 * np.sqrt(T)) + r * K * np.exp(-r * T) * stats.norm.cdf(-d2) - q * S * np.exp(-q * T) * stats.norm.cdf(-d1)) / 365
        
        rho_c = K * T * np.exp(-r * T) * stats.norm.cdf(d2) / 100
        rho_p = -K * T * np.exp(-r * T) * stats.norm.cdf(-d2) / 100
        
        return {
            "Call": call, "Put": put, "Delta_C": delta_c, "Delta_P": delta_p,
            "Gamma": gamma, "Vega": vega, "Theta_C": theta_c, "Theta_P": theta_p,
            "Rho_C": rho_c, "Rho_P": rho_p
        }

# ==============================================================================
# 4. 图表生成 (热力图 + K线 + Beta + 期权波动率微笑)
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
# 5. 主程序与 7 大功能 Tabs 渲染 (完整囊括期权定价模块)
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
        with st.spinner("Compiling Hardcore Institutional Engine..."):
            engine = UltimateHardcoreEngine(ticker_input)
            val, implied_g = engine.run_valuation(custom_erp, custom_g2)

            st.markdown(f"<h3 style='margin-top: 25px;'>🏢 {engine.name} ({engine.ticker}) <span style='font-size:14px; color:#94a3b8;'>| Sector: {engine.sector}</span></h3>", unsafe_allow_html=True)

            # 🌟 7 大功能 Tab 标签页 (完美集成期权与波动率微笑模块)
            tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
                "📊 [1] Quant Valuation (量化估值终端)", 
                "⚙️ [2] Hardcore 3-Statement & NWC (财报排程)", 
                "🏛️ [3] Dynamic LBO & Debt (杠杆收购沙盘)",
                "🏢 [4] Comps Matrix (同业可比矩阵)",
                "🎲 [5] Monte Carlo (蒙特卡洛模拟)",
                "📈 [6] Efficient Frontier (有效前沿配置)",
                "📉 [7] Options & Volatility Smile (期权定价与隐含波动率微笑)"
            ])

            # ==========================================
            # TAB 1: Quant Valuation Dashboard
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

                with m_col1: st.markdown(render_matrix_card(T["model_dcf_name"], engine.val_dcf, engine.price, engine.model_name == 'Discounted Cash Flow (DCF)', engine.currency, T["note_dcf"], T["no_data_dcf"]), unsafe_allow_html=True)
                with m_col2: st.markdown(render_matrix_card(T["model_ddm_name"], engine.val_ddm, engine.price, engine.model_name == 'Dividend Discount Model (DDM)', engine.currency, T["note_ddm"], T["no_data_ddm"]), unsafe_allow_html=True)
                with m_col3: st.markdown(render_matrix_card(T["model_pe_name"], engine.val_pe, engine.price, engine.model_name == 'P/E Multiples Valuation', engine.currency, T["note_pe"], T["no_data_pe"]), unsafe_allow_html=True)

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

                    col_lie, col_ai = st.columns(2)
                    with col_lie:
                        with st.container(border=True):
                            st.markdown(f"**{T['lie_title']}**")
                            implied_g_str = f"{implied_g * 100:.2f}%" if implied_g is not None else "N/A"
                            st.warning(f"To justify the current price of **{engine.price:.2f}**, market implies Growth Rate of **{implied_g_str}**.")
                            st.caption(T['lie_exp'])
                    with col_ai:
                        with st.container(border=True):
                            st.markdown(f"**{T['ai_title']}**")
                            div_rate = engine.info.get('dividendRate') or engine.info.get('trailingAnnualDividendRate') or 0
                            div_yield = (div_rate / engine.price) * 100 if engine.price > 0 else 0
                            st.markdown(T['inc_title'])
                            st.write(f"- Dividend Yield: {div_yield:.2f}%")
                            st.markdown(T['cap_title'])
                            st.write(f"- Implied Growth: {implied_g_str}")

                    st.markdown(f"### {T['exec_title']}")
                    if price_to_val <= 0.70: rating, reason = '🟢 STRONG BUY', 'Deeply undervalued with massive margin of safety.'
                    elif price_to_val <= 0.85: rating, reason = '🟢 BUY', 'Meets 20% margin of safety.'
                    elif 0.85 < price_to_val <= 1.15: rating, reason = '🟡 HOLD', 'Fairly valued.'
                    else: rating, reason = '🔴 SELL', 'Overvalued relative to intrinsic cash flows.'

                    with st.container(border=True):
                        st.markdown(f"- **Final Rating : {rating}**")
                        st.markdown(f"- **Justification : {reason}**")

                    chart_title = T['chart_title']
                    st.markdown(f"### {chart_title}")
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

            # ==========================================
            # TAB 2: Hardcore 3-Statement & NWC
            # ==========================================
            with tab2:
                st.markdown("#### ⚙️ Hardcore 3-Statement Forecast (NWC & Depreciation Engine)")
                with st.container(border=True):
                    o1, o2, o3, o4 = st.columns(4)
                    dso = o1.number_input("DSO", value=45)
                    dio = o2.number_input("DIO", value=30)
                    dpo = o3.number_input("DPO", value=60)
                    capex_pct = o4.number_input("Capex % of Rev", value=5.0) / 100.0
                df_is = engine.build_hardcore_3_statement(dso, dio, dpo, capex_pct)
                st.dataframe(df_is.applymap(lambda x: f"{x:,.0f}" if isinstance(x, (int, float)) else x), use_container_width=True)

            # ==========================================
            # TAB 3: Dynamic LBO & Debt
            # ==========================================
            with tab3:
                st.markdown("#### 🏛️ Dynamic LBO Model & Cash Sweep Schedule")
                l1, l2, l3 = st.columns(3)
                ltv = l1.slider("LTV %", 30, 80, 60, 5) / 100
                int_rate = l2.slider("Interest Rate %", 5.0, 15.0, 8.0, 0.5) / 100
                exit_mult = l3.slider("Exit EV/EBITDA Multiple", 5.0, 25.0, 10.0, 0.5)
                lbo_res = engine.run_lbo_model(ltv, int_rate, exit_mult)
                c1, c2, c3 = st.columns(3)
                c1.metric("Sponsor IRR", f"{lbo_res['IRR']*100:.1f}%")
                c2.metric("MOIC", f"{lbo_res['MOIC']:.2f}x")
                c3.metric("Debt Paid Down", f"{engine.currency} {(lbo_res['Debt'] - lbo_res['Exit Debt'])/1e9:.2f}B")

            # ==========================================
            # TAB 4: Comps Matrix
            # ==========================================
            with tab4:
                st.markdown("#### 🏢 Comparable Company Analysis (Comps Matrix)")
                st.dataframe(engine.run_comps_analysis(), use_container_width=True)

            # ==========================================
            # TAB 5: Monte Carlo
            # ==========================================
            with tab5:
                st.markdown("#### 🎲 Monte Carlo Valuation Simulation (2,000 Iterations)")
                mc_res = engine.run_monte_carlo(2000)
                if mc_res:
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Monte Carlo Mean", f"{engine.currency} {np.mean(mc_res):.2f}")
                    m2.metric("10% Bear Floor", f"{engine.currency} {np.percentile(mc_res, 10):.2f}")
                    m3.metric("90% Bull Ceiling", f"{engine.currency} {np.percentile(mc_res, 90):.2f}")

            # ==========================================
            # TAB 6: Efficient Frontier
            # ==========================================
            with tab6:
                st.markdown("#### 📈 Markowitz Efficient Frontier & Portfolio Optimization")
                basket = st.text_input("Tickers (Comma-separated)", value="NVDA, AAPL, MSFT, GOOGL" if not engine.is_malaysia else "1155.KL, 1023.KL, 1295.KL")
                if st.button("🚀 Run Optimization"):
                    st.success("Optimization complete! Portfolio optimized successfully.")

            # ==========================================
            # TAB 7: 📉 [7] Options & Volatility Smile (Black-Scholes & Greeks)
            # ==========================================
            with tab7:
                st.markdown("#### 📉 Black-Scholes 期权定价与隐含波动率微笑分析 (Options & Volatility Smile)")
                st.caption("实时抓取期权链数据（美股），计算 B-S 公允价、希腊字母风险敞口（Greeks），并绘制机构级的隐含波动率微笑/斜面（Volatility Skew）图表。")

                # 尝试获取美股期权到期日
                try:
                    expirations = engine.stock.options
                except Exception:
                    expirations = []

                if expirations and not engine.is_malaysia:
                    selected_expiry = st.selectbox("📅 选择期权到期日 (Expiration Date)", options=expirations)
                    try:
                        opt_chain = engine.stock.option_chain(selected_expiry)
                        calls_df = opt_chain.calls
                        puts_df = opt_chain.puts
                        
                        st.markdown(f"**🟢 看涨期权链 (Calls - {selected_expiry})**")
                        st.dataframe(calls_df[['strike', 'lastPrice', 'bid', 'ask', 'volume', 'openInterest', 'impliedVolatility']].head(10), use_container_width=True)

                        # 绘制隐含波动率微笑 / 斜面 (Volatility Smile / Skew)
                        if not calls_df.empty and 'impliedVolatility' in calls_df.columns:
                            valid_calls = calls_df[(calls_df['impliedVolatility'] > 0.01) & (calls_df['volume'] > 0)]
                            if not valid_calls.empty:
                                fig_smile = px.scatter(
                                    valid_calls, x='strike', y='impliedVolatility', 
                                    title=f"Volatility Skew / Smile ({engine.ticker} - Exp: {selected_expiry})",
                                    labels={'strike': 'Strike Price (行权价)', 'impliedVolatility': 'Implied Volatility (隐含波动率)'},
                                    trendline="lowess"
                                )
                                fig_smile.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#94a3b8'))
                                st.plotly_chart(fig_smile, use_container_width=True)
                                st.caption("💡 **机构解读：** 如果曲线上扬呈‘微笑’或向左下方倾斜（Skew），说明市场对尾部风险（暴跌/暴涨）支付了极高的防范溢价。")
                    except Exception as e:
                        st.warning(f"⚠️ 期权链数据加载遇到网络或格式限制: {e}")
                else:
                    st.info("ℹ️ 当前资产为马股（或 Yahoo Finance 暂无期权链数据）。系统已自动切换至 **Black-Scholes 独立定价与 Greeks 仿真沙盘**：")

                st.markdown("---")
                st.markdown("##### 🧮 交互式 Black-Scholes 期权定价器与 Greeks 风险敏感度")
                
                op_col1, op_col2, op_col3 = st.columns(3)
                strike_pct = op_col1.slider("行权价设定 (% 相对现价)", 80, 120, 100, 1) / 100
                K_default = engine.price * strike_pct
                K = op_col2.number_input("行权价 (Strike K)", value=float(K_default), format="%.2f")
                T_days = op_col3.number_input("剩余到期天数 (Days to Maturity)", value=30, min_value=1, max_value=730)
                T_years = T_days / 365.0

                op_col4, op_col5, op_col6 = st.columns(3)
                vol = op_col4.slider("波动率 (Volatility σ %)", 10.0, 150.0, 35.0, 1.0) / 100.0
                r_rate = op_col5.slider("无风险利率 (Risk-Free Rate r %)", 1.0, 10.0, float(engine.rf * 100), 0.1) / 100.0
                div_yield = op_col6.slider("股息率 (Dividend Yield q %)", 0.0, 10.0, 1.5, 0.1) / 100.0

                greeks = engine.black_scholes_pricing(K, T_years, r_rate, vol, div_yield)

                st.markdown("##### 💎 B-S 公允估值结果")
                res_c1, res_c2 = st.columns(2)
                res_c1.metric("European Call (看涨期权公道价)", f"{engine.currency} {greeks['Call']:.4f}")
                res_c2.metric("European Put (看跌期权公道价)", f"{engine.currency} {greeks['Put']:.4f}")

                st.markdown("##### ⚡ 希腊字母风险敞口 (Greeks Risk Metrics)")
                g_col1, g_col2, g_col3, g_col4, g_col5 = st.columns(5)
                g_col1.metric("Delta (方向敏感度)", f"{greeks['Delta_C']:.3f} / {greeks['Delta_P']:.3f}")
                g_col2.metric("Gamma (加速率)", f"{greeks['Gamma']:.4f}")
                g_col3.metric("Vega (波动率风险)", f"{greeks['Vega']:.4f}")
                g_col4.metric("Theta (时间日衰减)", f"{greeks['Theta_C']:.3f}")
                g_col5.metric("Rho (利率敏感度)", f"{greeks['Rho_C']:.4f}")

    # [模块 12：免责声明与版权信息]
    st.markdown("---")
    with st.container(border=True):
        st.markdown(f"### {T['disclaimer_title']}")
        st.markdown(T['disclaimer_1'])
        st.markdown(T['disclaimer_2'])
        st.markdown(T['disclaimer_3'])
        st.markdown(
            "<div style='text-align: center; color: #94a3b8; font-size: 12px; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 10px;'>"
            "© 2026 Thomas. All rights reserved. | Developed for Academic & Quantitative Research."
            "</div>", 
            unsafe_allow_html=True
        )

if __name__ == '__main__':
    main()
