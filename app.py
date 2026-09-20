import datetime
import numpy as np
import pandas as pd
import requests
import yfinance as yf
import streamlit as st
import plotly.graph_objects as go

# ==============================================================================
# 1. 页面基本配置与高级 CSS 视觉引擎
# ==============================================================================
st.set_page_config(page_title="Ultimate Quant & PE Terminal V9.1", page_icon="🏦", layout="wide", initial_sidebar_state="collapsed")

PREMIUM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');
.stApp { background: radial-gradient(circle at 50% 0%, #1e293b 0%, #0f172a 60%, #090d16 100%) !important; font-family: 'Inter', -apple-system, sans-serif !important; color: #f8fafc !important; }
.block-container { padding-top: 2rem !important; max-width: 1400px !important; }
header[data-testid="stHeader"] { background: transparent !important; }

.stTabs [data-baseweb="tab-list"] { gap: 10px; background-color: rgba(15, 23, 42, 0.6); border-radius: 12px; padding: 10px; border: 1px solid rgba(56, 189, 248, 0.2); }
.stTabs [data-baseweb="tab"] { color: #94a3b8 !important; font-weight: 600 !important; border-radius: 8px !important; padding: 12px 24px !important; transition: all 0.3s ease; }
.stTabs [aria-selected="true"] { background: linear-gradient(135deg, #38bdf8 0%, #0284c7 100%) !important; color: #ffffff !important; box-shadow: 0 4px 15px rgba(56, 189, 248, 0.4); }

[data-testid="column"] > div { height: 100% !important; }
[data-testid="stVerticalBlockBorderWrapper"] { background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.85) 100%) !important; border: 1px solid rgba(56, 189, 248, 0.3) !important; border-radius: 14px !important; box-shadow: 0 8px 24px -4px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.08) !important; backdrop-filter: blur(12px) !important; padding: 16px 20px !important; height: 100% !important; display: flex; flex-direction: column; justify-content: space-between; }
[data-testid="stMetricValue"] { font-family: 'JetBrains Mono', monospace !important; font-weight: 800 !important; font-size: 1.8rem !important; color: #f8fafc !important; }
[data-testid="stMetricLabel"] { font-weight: 600 !important; color: #94a3b8 !important; font-size: 0.85rem !important; }
h1, h2, h3, h4, h5 { font-family: 'Inter', sans-serif !important; font-weight: 700 !important; color: #ffffff !important; }
h3 { color: #38bdf8 !important; text-shadow: 0 0 15px rgba(56, 189, 248, 0.2); margin-bottom: 15px !important; }
div[data-baseweb="input"] > div, div[data-baseweb="select"] > div { background-color: #0f172a !important; border: 1px solid rgba(56, 189, 248, 0.3) !important; border-radius: 8px !important; color: #ffffff !important; }
</style>
"""
st.markdown(PREMIUM_CSS, unsafe_allow_html=True)

@st.cache_resource
def get_yf_session():
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    return session

# ==============================================================================
# 2. 国际化多语言字典 
# ==============================================================================
TEXTS = {
    "zh": {
        "title": "🌐 智能量化金融终端 (V9.1 硬核财务版)",
        "subtitle": "全新升级：注入 NWC 营运资金动态排程、折旧瀑布流与全动态 FCF 引擎",
        "quick_tag": "🔥 热门快捷测评：",
        "input_label": "输入股票代码 (如 1155.KL, NVDA, AAPL)：",
        "param_title": "⚙️ 步骤 2：估值核心参数设定 (可保持默认)",
        "param_tip": "💡 **何时建议手动调整？**\n* **永续增长率 (g)**：当您预期长期通胀或名义GDP增速显著偏离时。\n* **风险溢价 (ERP)**：当市场处于极端恐慌或狂热周期时可修正。",
        "erp_label": "股市风险溢价要求 (Equity Risk Premium)",
        "g2_label": "长期永续通胀增长率 (Terminal Growth Rate)",
        "esg_caption": "🌿 本系统已自动结合可持续金融 (Sustainable Finance) 与 ESG 行业风险溢价进行折现率修正。",
        "macro_title": "[1. 动态宏观与资本成本 (DYNAMIC MACRO & COST OF CAPITAL)]",
        "macro_exp": "💡 Beta 衡量股票相对于大盘的波动率。Rf 是无风险国债利率。WACC 是你要求的最低及格线回报率。",
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
        "fair_val_desc": "💡 **【内在公道估值】**：剥离短期炒作，根据公司真实造血能力算出的保守身价。",
        "safe_buy": "20% 安全边际买点",
        "heat_title": "[3. 🌡️ 核心参数敏感性分析矩阵 (DCF SENSITIVITY HEATMAP)]",
        "heat_desc": "👉 <span style='color:#10b981;'>**绿色区域**</span> 代表该参数下当前市价被低估 (具备安全边际)；<span style='color:#ef4444;'>**红色区域**</span> 代表高估。",
        "lie_title": "[4. 💡 市场情绪测谎仪 (MARKET PSYCHOLOGY)]",
        "lie_exp": "💡 测谎仪通过反向推导，看看当前的市场价格到底在幻想这家公司未来每年增长多少。",
        "ai_title": "[5. 🤖 双视角 AI 投资顾问 (DUAL-PERSPECTIVE AI)]",
        "inc_title": "🔸 视角 A：保守派收息策略",
        "cap_title": "🔹 视角 B：进取派资本增值",
        "exec_title": "[6. 🎯 最终投资评级与执行摘要]",
        "rating_explain": "ℹ️ *好公司不等于好价格。缺乏安全边际即触发 SELL。*",
        "plain_title": "[7. 🗣️ 小白通俗翻译器]",
        "fx_title": "[8. 💱 跨境汇率风险提示]",
        "fx_content": "- **提示：** 此乃美元计价资产，请注意美元兑马币 (USD/MYR) 汇率波动。",
        "ws_title": "🏛️ [9. 华尔街投行分析师共识与预期差]",
        "ws_mean": "投行平均目标价",
        "ws_range": "目标价区间",
        "ws_rating": "投行综合评级",
        "ws_tag": "机构共识",
        "gap_title": "⚡ 预期差雷达 (Expectation Gap Analysis)",
        "gap_line1": "量化内在公允价",
        "gap_line2": "华尔街平均目标价",
        "gap_line3": "预期差偏离度",
        "gap_desc_high": "华尔街目标价比模型高出",
        "gap_alert_high": "🚨 **【情绪溢价驱动】**：华尔街目标价远高于量化模型底线。长线投资者需警惕回撤。",
        "gap_alert_low": "🔥 **【深度价值契机】**：量化模型价值高于华尔街卖方预期，属于潜在布局区。",
        "ws_match": "✅ 模型公道价与华尔街预测高度吻合！",
        "chart_title": "[10. 📈 高级盘面与波动率回归分析]",
        "beta_desc": "📊 **Beta 回归分析：** 点越密集贴近红线，说明个股越受大盘宏观主导；越分散说明走势越独立。",
        "glossary_title": "[11. 📖 核心指标科普]",
        "g_beta_title": "##### 🎯 Beta (波动率)",
        "g_beta_desc": "Beta > 1 涨跌比大盘更猛，Beta < 1 走势更抗跌。",
        "g_growth_title": "##### 🚀 Growth (预期增长)",
        "g_growth_desc": "预期未来现金流每年递增的比例。",
        "g_wacc_title": "##### 🛡️ WACC (折现率)",
        "g_wacc_desc": "你买入这家公司要求的最低年化回报门槛。",
        "g_fv_title": "##### 💎 Fair Value (公道价)",
        "g_fv_desc": "根据公司真实赚钱能力算出的出厂公道价。",
        "disclaimer_title": "[12. ⚠️ 法律与风险免责声明]",
        "disclaimer_1": "1. 仅供学术研究、个人学习交流与教学参考，不构成任何投资建议。",
        "disclaimer_2": "2. 数学量化模型无法完全预知未来，请结合行业深度研究。",
        "disclaimer_3": "3. 任何交易盈亏均由投资者自行承担法律责任。"
    },
    "en": {
        "title": "🌐 Universal Quant Terminal (Hardcore V9.1)",
        "subtitle": "Upgraded with Dynamic NWC, Capex Waterfall & Hardcore FCF Engine",
        "quick_tag": "🔥 Quick Select:",
        "input_label": "Enter Stock Ticker (e.g., 1155.KL, NVDA, AAPL):",
        "param_title": "⚙️ Step 2: Macro Parameters (Defaults Recommended)",
        "param_tip": "💡 **When to adjust?** Tweak Terminal Growth for structural inflation views, and ERP during market extremes.",
        "erp_label": "Equity Risk Premium (ERP)",
        "g2_label": "Terminal Growth Rate (g)",
        "esg_caption": "🌿 ESG Sector Risk Premium integrated into discount rates.",
        "macro_title": "[1. DYNAMIC MACRO & COST OF CAPITAL]",
        "macro_exp": "💡 Beta measures market risk. Rf is the risk-free rate. WACC is the hurdle rate.",
        "matrix_header": "[2. Multi-Model Valuation Matrix (DCF + DDM + P/E)]",
        "model_dcf_name": "Two-Stage Fading DCF",
        "model_ddm_name": "Dividend Discount Model",
        "model_pe_name": "P/E Multiples Valuation",
        "badge_recommended": "⭐ Recommended",
        "badge_reference": "📌 Reference",
        "no_data_dcf": "Negative/Missing FCF",
        "no_data_ddm": "No Dividend",
        "no_data_pe": "Net Loss",
        "vs_market": "vs Market",
        "note_dcf": "Based on linear fading FCF & WACC.",
        "note_ddm": "Based on dividends and terminal growth.",
        "note_pe": "Based on EPS x Benchmark P/E.",
        "price": "Market Price",
        "fair_val": "Intrinsic Fair Value",
        "fair_val_desc": "💡 Strips away market hype to reveal true fundamental worth.",
        "safe_buy": "Safe Buy Target (20% MoS)",
        "heat_title": "[3. 🌡️ DCF SENSITIVITY HEATMAP]",
        "heat_desc": "👉 <span style='color:#10b981;'>**Green zones**</span> indicate undervalued scenarios; <span style='color:#ef4444;'>**Red zones**</span> indicate overvalued.",
        "lie_title": "[4. 💡 MARKET PSYCHOLOGY (LIE DETECTOR)]",
        "lie_exp": "💡 Reverse-engineers the growth rate currently priced into the stock.",
        "ai_title": "[5. 🤖 DUAL-PERSPECTIVE AI ADVISORY]",
        "inc_title": "🔸 A: Conservative Income",
        "cap_title": "🔹 B: Capital Appreciation",
        "exec_title": "[6. 🎯 FINAL EXECUTIVE SUMMARY & RATING]",
        "rating_explain": "ℹ️ *Good company ≠ Good price. Lack of Margin of Safety triggers SELL.*",
        "plain_title": "[7. 🗣️ PLAIN ENGLISH TRANSLATOR]",
        "fx_title": "[8. 💱 CROSS-BORDER FX RISK]",
        "fx_content": "- **Note:** Monitor USD/MYR fluctuations for USD assets.",
        "ws_title": "🏛️ [9. Wall St Consensus & Expectation Gap]",
        "ws_mean": "Avg Target Price",
        "ws_range": "Target Range",
        "ws_rating": "Consensus Rating",
        "ws_tag": "Inst. Consensus",
        "gap_title": "⚡ Expectation Gap Analysis",
        "gap_line1": "Model Fair Value",
        "gap_line2": "Wall St Target Mean",
        "gap_line3": "Divergence Gap",
        "gap_desc_high": "Wall St target is higher by",
        "gap_alert_high": "🚨 **[Sentiment Premium]**: Wall St targets exceed fundamental model. Caution advised.",
        "gap_alert_low": "🔥 **[Deep Value]**: Model value exceeds Wall St expectations.",
        "ws_match": "✅ Valuation aligns tightly with Wall Street!",
        "chart_title": "[10. Advanced Price Action & Regression]",
        "beta_desc": "📊 Tight clustering indicates market-driven risk; high dispersion reflects strong independent trends.",
        "glossary_title": "[11. Financial Glossary]",
        "g_beta_title": "##### 🎯 Beta",
        "g_beta_desc": "Volatility relative to the market.",
        "g_growth_title": "##### 🚀 Expected Growth",
        "g_growth_desc": "Projected annual cash flow growth.",
        "g_wacc_title": "##### 🛡️ WACC",
        "g_wacc_desc": "Minimum hurdle rate of return.",
        "g_fv_title": "##### 💎 Fair Value",
        "g_fv_desc": "Intrinsic value based on earning power.",
        "disclaimer_title": "[12. ⚠️ Important Disclaimer]",
        "disclaimer_1": "1. For academic research and educational purposes only.",
        "disclaimer_2": "2. Quant models cannot predict black swan events.",
        "disclaimer_3": "3. The developer accepts no liability for trading losses."
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
# 3. 终极硬核量化引擎 (集成 NWC、折旧瀑布流与全动态 FCF)
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

        # 基础财务数据抓取
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
        self.hardcore_ufcf_proj = [] # 动态生成的硬核现金流缓存

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
        self.horizon = 5

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

    # 🌟 V9.1 核心大招：动态营运资金与折旧瀑布流 3-Statement 模型
    def build_hardcore_3_statement(self, dso, dio, dpo, capex_pct):
        years = ['Year 0 (Current)', 'Year 1', 'Year 2', 'Year 3', 'Year 4', 'Year 5']
        
        rev_0 = self.revenue
        cogs_0 = self.cogs if self.cogs > 0 else rev_0 * 0.5
        ebitda_margin = self.ebitda / self.revenue if self.revenue > 0 else 0.2
        tax_rate = self.tax

        rev = [rev_0]; cogs = [cogs_0]; ebitda = [self.ebitda]; da = [self.hist_da]; capex = [rev_0 * capex_pct]
        
        # 初始营运资金 (NWC)
        ar = [(dso / 365.0) * rev_0]
        inv = [(dio / 365.0) * cogs_0]
        ap = [(dpo / 365.0) * cogs_0]
        nwc = [ar[0] + inv[0] - ap[0]]
        dnwc = [0.0]
        ufcf = [self.cf]

        new_capex_schedule = [] # 记录每年新增 Capex 建立瀑布流

        for i in range(1, 6):
            g = self.g1 - (self.g1 - self.g2) * (i / 5)
            r = rev[-1] * (1 + g)
            c = cogs[-1] * (1 + g)
            e = r * ebitda_margin

            rev.append(r); cogs.append(c); ebitda.append(e)

            # Capex
            cap = r * capex_pct
            capex.append(cap)
            new_capex_schedule.append(cap)

            # D&A 瀑布流折旧 (历史衰减 + 新增资产 5年直线法)
            current_da = self.hist_da * (1 - 0.2 * i) if (1 - 0.2 * i) > 0 else 0
            for j in range(len(new_capex_schedule)):
                current_da += new_capex_schedule[j] * 0.2
            da.append(current_da)

            # 动态 NWC 变动
            current_ar = (dso / 365.0) * r
            current_inv = (dio / 365.0) * c
            current_ap = (dpo / 365.0) * c
            current_nwc = current_ar + current_inv - current_ap

            ar.append(current_ar); inv.append(current_inv); ap.append(current_ap)
            nwc.append(current_nwc)
            dnwc.append(current_nwc - nwc[-2])

            # 真正硬核的 UFCF: EBIT*(1-t) + D&A - Capex - dNWC
            ebit = e - current_da
            nopat = ebit * (1 - tax_rate)
            current_ufcf = nopat + current_da - cap - dnwc[-1]
            ufcf.append(current_ufcf)

        self.hardcore_ufcf_proj = ufcf[1:] # 存入缓存供 LBO 调用

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
        entry_multiple = self.ev / self.ebitda if self.ebitda > 0 else 10.0
        purchase_price = self.ev
        debt_funding = purchase_price * ltv_ratio
        equity_funding = purchase_price - debt_funding
        
        debt_schedule = [debt_funding]
        
        # 🌟 关联硬核 FCF 驱动债务偿还 (Cash Sweep)
        for fcf in self.hardcore_ufcf_proj:
            interest = debt_schedule[-1] * interest_rate
            cash_sweep = max(0, fcf - interest)
            ending_debt = max(0, debt_schedule[-1] - cash_sweep)
            debt_schedule.append(ending_debt)
            
        y5_ebitda = self.ebitda * ((self.revenue / self.ebitda) if self.ebitda>0 else 1) # Simplified exit ebitda base
        exit_ev = y5_ebitda * exit_multiple
        exit_equity = exit_ev - debt_schedule[-1]
        
        moic = exit_equity / equity_funding if equity_funding > 0 else 0
        irr = (moic ** (1/5)) - 1 if moic > 0 else 0
        
        return {
            "Entry EV": purchase_price, "Debt": debt_funding, "Equity": equity_funding,
            "Exit EV": exit_ev, "Exit Debt": debt_schedule[-1], "Exit Equity": exit_equity,
            "MOIC": moic, "IRR": irr, "Debt Schedule": debt_schedule
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
        with st.spinner("Compiling Hardcore Institutional Engine..."):
            engine = UltimateHardcoreEngine(ticker_input)
            val, implied_g = engine.run_valuation(custom_erp, custom_g2)

            st.markdown(f"<h3 style='margin-top: 25px;'>🏢 {engine.name} ({engine.ticker}) <span style='font-size:14px; color:#94a3b8;'>| Sector: {engine.sector}</span></h3>", unsafe_allow_html=True)

            tab1, tab2, tab3 = st.tabs([
                "📊 [1] Quant Valuation Dashboard (量化估值终端)", 
                "⚙️ [2] Hardcore 3-Statement & NWC (硬核财报排程)", 
                "🏛️ [3] Dynamic LBO & Debt Schedule (动态收购沙盘)"
            ])

            # ==========================================
            # TAB 1: 完整的原版 V8.9 Plus (全量保留)
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
                        val_str, status_html = "N/A", f"<div style='color: #f87171; font-size: 12px;'>⚠️ {empty_msg}</div>"
                    return f"""<div style="background: linear-gradient(135deg, rgba(30, 41, 59, 0.9) 0%, rgba(15, 23, 42, 0.95) 100%); border: 1.5px solid {card_border}; border-radius: 12px; padding: 18px; min-height: 175px; display: flex; flex-direction: column; justify-content: space-between;"><div><div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;"><span style="font-size: 14px; font-weight: 700; color: #f8fafc;">{title}</span><span style="background: rgba(56, 189, 248, 0.15); color: #38bdf8; font-size: 10.5px; font-weight: 700; padding: 2px 8px; border-radius: 12px;">{badge_text}</span></div><div style="font-family: 'JetBrains Mono', monospace; font-size: 26px; font-weight: 800; color: #ffffff; margin: 4px 0;">{val_str}</div><div>{status_html}</div></div><div style="color: #94a3b8; font-size: 11.5px; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 8px; margin-top: 8px;">💡 {note}</div></div>"""

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
                                wr = heat_stats['win_rate']
                                if wr >= 0.70: ai_insight = f"🟢 <b>高胜率 / 低估 (High Margin of Safety):</b> 多数情景（{heat_stats['green_count']}/{heat_stats['total']}）具备极厚安全垫。"
                                elif wr <= 0.30: ai_insight = f"🔴 <b>高风险 / 高估 (Overvalued & Fragile):</b> 当前市价已透支未来，面临估值杀跌风险。"
                                else: ai_insight = "🟡 <b>高度敏感 / 合理偏高 (Highly Sensitive):</b> 估值处于微妙平衡，对 WACC 极为敏感。"
                                st.markdown(f"""<div style="background: rgba(15, 23, 42, 0.6); border-left: 4px solid #38bdf8; padding: 16px; border-radius: 6px; margin-top: 10px;"><div style="color: #38bdf8; font-weight: 800; font-size: 15px; margin-bottom: 8px;">🤖 AI 矩阵智能解析</div><div style="color: #e2e8f0; font-size: 14px; margin-bottom: 12px; line-height: 1.6;">{ai_insight}</div><div style="display: flex; gap: 20px; color: #94a3b8; font-size: 12.5px; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 10px;"><div>⚡ <b>胜率测算:</b> 有 <span style="color:#10b981; font-weight:bold;">{heat_stats['green_count']}</span> 种具备安全边际。</div><div>📉 <b>最悲观底线:</b> {engine.currency} {heat_stats['worst']:.2f}</div><div>🚀 <b>最乐观上限:</b> {engine.currency} {heat_stats['best']:.2f}</div></div></div>""", unsafe_allow_html=True)

                    col_lie, col_ai = st.columns(2)
                    with col_lie:
                        with st.container(border=True):
                            st.markdown(f"**{T['lie_title']}**")
                            implied_g_str = f"{implied_g * 100:.2f}%" if implied_g is not None else "N/A"
                            st.warning(f"To justify the current price of **{engine.price:.2f}**, the market implies a Growth Rate of **{implied_g_str} per year for {engine.horizon} years**.")
                            if implied_g is not None:
                                if implied_g > 0.40: st.write("-> **Diagnosis: EXTREME HYPE (Bubble Territory).**")
                                elif implied_g < 0.0: st.write("-> **Diagnosis: EXTREME PESSIMISM.**")
                                else: st.write("-> **Diagnosis: MODERATE EXPECTATIONS.**")
                            st.caption(T['lie_exp'])

                    with col_ai:
                        with st.container(border=True):
                            st.markdown(f"**{T['ai_title']}**")
                            div_yield = ((engine.info.get('dividendRate') or 0) / engine.price) * 100 if engine.price > 0 else 0
                            st.markdown(T['inc_title'])
                            st.write(f"- Dividend Yield: {div_yield:.2f}% | Beta Risk: {engine.beta:.2f}")
                            if engine.sector in ['Financial Services', 'Utilities'] and div_yield > 3.0: st.success("-> **Verdict:** 🟢 SUITABLE FOR INCOME.")
                            else: st.error("-> **Verdict:** 🔴 NOT IDEAL FOR INCOME.")
                            st.markdown(T['cap_title'])
                            st.write(f"- Implied Growth: {implied_g_str} | Model Valuation: {val:.2f}")
                            if implied_g is not None and implied_g < 0.0 and engine.price < val: st.success("-> **Verdict:** 🟢 MULTI-BAGGER POTENTIAL.")
                            elif implied_g is not None and implied_g > 0.40: st.error("-> **Verdict:** 🔴 HIGH SPECULATION RISK.")
                            else: st.info("-> **Verdict:** 🟢 / 🟡 FAIRLY PRICED.")

                    st.markdown(f"### {T['exec_title']}")
                    if price_to_val <= 0.70 and (implied_g is not None and implied_g < 0.0): rating, reason = '🟢 STRONG BUY', f'Extreme pessimism creates massive margin of safety.'
                    elif price_to_val <= 0.85: rating, reason = '🟢 BUY', f'Solid value mispricing meets 20% margin of safety.'
                    elif 0.85 < price_to_val <= 1.15: rating, reason = '🟡 HOLD', f'Fairly valued.'
                    elif 1.15 < price_to_val <= 1.40: rating, reason = '🔴 SELL', f'Overvalued vs intrinsic value.'
                    else: rating, reason = '🔴 STRONG SELL', f'Severe bubble risk.'
                    
                    with st.container(border=True):
                        st.markdown(f"- **Final Investment Rating : {rating}**")
                        st.markdown(f"- **Core Justification : {reason}**")
                        st.caption(T['rating_explain'])

                    col_t1, col_t2 = st.columns(2)
                    with col_t1:
                        with st.container(border=True):
                            st.markdown(f"**{T['plain_title']}**")
                            st.markdown(f"- **Required Hurdle Rate:** {engine.r * 100:.2f}%")
                            if implied_g is not None:
                                st.markdown(f"- **Implied Growth:** {implied_g * 100:.2f}%")
                                if implied_g > 0.35: st.markdown("  👉 **【⚠️ SEVERE BUBBLE】**")
                                elif implied_g < 0.0: st.markdown("  👉 **【🔥 DEEP VALUE】**")
                                else: st.markdown("  👉 **【⚖️ BALANCED】**")
                    with col_t2:
                        with st.container(border=True):
                            st.markdown(f"**{T['fx_title']}**")
                            if not engine.is_malaysia: st.warning(T['fx_content'])
                            else: st.warning("- 🇲🇾 本地资产计价 (MYR)，无跨境外汇风险。")

                    if not engine.is_malaysia and engine.info.get('targetMeanPrice'):
                        target_mean = engine.info.get('targetMeanPrice')
                        st.markdown(f"<br><h3>{T['ws_title']}</h3>", unsafe_allow_html=True)
                        ws_col1, ws_col2, ws_col3 = st.columns(3)
                        with ws_col1:
                            with st.container(border=True):
                                st.markdown(f"<div style='text-align:center;'>{T['ws_mean']}<br><b style='font-size:30px;'>${target_mean:.2f}</b></div>", unsafe_allow_html=True)
                        with ws_col2:
                            with st.container(border=True):
                                st.markdown(f"<div style='text-align:center;'>{T['ws_range']}<br><b style='font-size:24px;'>${engine.info.get('targetLowPrice', 0):.2f} ~${engine.info.get('targetHighPrice', 0):.2f}</b></div>", unsafe_allow_html=True)
                        with ws_col3:
                            with st.container(border=True):
                                st.markdown(f"<div style='text-align:center;'>{T['ws_rating']}<br><b style='font-size:28px; color:#38bdf8;'>{str(engine.info.get('recommendationKey', 'N/A')).upper()}</b></div>", unsafe_allow_html=True)
                        with st.container(border=True):
                            st.markdown(f"**{T['gap_title']}**")
                            gap_pct = ((target_mean - val) / val) * 100.0
                            st.write(f"- **{T['gap_line1']}:** `${val:.2f}` | **{T['gap_line2']}:** `${target_mean:.2f}`")
                            st.write(f"- **{T['gap_line3']}:** `+{gap_pct:.1f}%`")

                    st.markdown(f"### {T['chart_title']}")
                    c_chart1, c_chart2 = st.columns(2)
                    with c_chart1:
                        with st.container(border=True):
                            st.plotly_chart(draw_pro_candlestick(engine.ticker, engine.session), use_container_width=True)
                    with c_chart2:
                        with st.container(border=True):
                            st.plotly_chart(draw_beta_scatter(engine), use_container_width=True)
                    
                    st.markdown(f"### {T['glossary_title']}")
                    g1, g2, g3, g4 = st.columns(4)
                    with g1:
                        with st.container(border=True): st.markdown(T['g_beta_title']); st.caption(T['g_beta_desc'])
                    with g2:
                        with st.container(border=True): st.markdown(T['g_growth_title']); st.caption(T['g_growth_desc'])
                    with g3:
                        with st.container(border=True): st.markdown(T['g_wacc_title']); st.caption(T['g_wacc_desc'])
                    with g4:
                        with st.container(border=True): st.markdown(T['g_fv_title']); st.caption(T['g_fv_desc'])

            # ==========================================
            # TAB 2: V9.1 硬核升级 (NWC 与 瀑布流折旧)
            # ==========================================
            with tab2:
                st.markdown("#### ⚙️ Hardcore 3-Statement Forecast (NWC & Depreciation Engine)")
                st.caption("Adjust the Working Capital (DSO/DIO/DPO) and Capex drivers below to dynamically alter the Free Cash Flow (FCF) generation. See how pushing suppliers (DPO) improves cash flow!")
                
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
                    # 格式化数字：保留负号并添加千位分隔符
                    styled_df[col] = styled_df[col].apply(lambda x: f"{x:,.0f}")
                
                st.dataframe(styled_df, use_container_width=True, height=320)

            # ==========================================
            # TAB 3: 完美联动的 LBO 杠杆收购沙盘
            # ==========================================
            with tab3:
                st.markdown("#### 🏛️ Dynamic LBO Model & Cash Sweep Schedule")
                st.caption("This LBO is perfectly linked to the Hardcore UFCF generated in Tab 2. If you optimize NWC (e.g., increase DPO) in Tab 2, your Sponsor IRR here will spike because more cash is available to pay down debt!")
                
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
                su_df['Amount'] = su_df['Amount'].apply(lambda x: f"{x:,.0f}")
                st.table(su_df)

                st.markdown("**Debt Schedule & Cash Sweep**")
                debt_df = pd.DataFrame({"Year": ["0 (Entry)", "1", "2", "3", "4", "5"], "Ending Debt Balance": lbo_res['Debt Schedule']})
                debt_df['Ending Debt Balance'] = debt_df['Ending Debt Balance'].apply(lambda x: f"{x:,.0f}")
                st.table(debt_df.set_index('Year').T)

    st.markdown("---")
    with st.container(border=True):
        st.markdown(f"### {T['disclaimer_title']}")
        st.markdown(T['disclaimer_1'])
        st.markdown(T['disclaimer_2'])
        st.markdown(T['disclaimer_3'])
        st.markdown("<div style='text-align: center; color: #94a3b8; font-size: 12px; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 10px;'>© 2026 Thomas. All rights reserved. | Developed for Academic & Quantitative Research.</div>", unsafe_allow_html=True)

if __name__ == '__main__':
    main()
