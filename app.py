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
# 1. 页面基本配置与高级 CSS 视觉引擎
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
    session.headers.update({'User-Agent': 'Mozilla/5.0'})
    return session

# ==============================================================================
# 2. 国际化多语言字典 (扩充完毕)
# ==============================================================================
TEXTS = {
    "zh": {
        "title": "🌐 智能量化与衍生品金融终端 (V9.6 旗舰全功能版)",
        "subtitle": "完美融合 线性衰减DCF、热力图、动态NWC与折旧瀑布流、LBO、同业Comps、有效前沿与智能期权顾问",
        "quick_tag": "🔥 热门快捷测评：",
        "input_label": "输入股票代码 (如 1155.KL, NVDA, AAPL)：",
        "param_title": "⚙️ 步骤 2：估值核心参数设定 (可保持默认)",
        "param_tip": "💡 **何时建议手动调整？**\n* **永续增长率 (g)**：预期长期通胀或名义GDP增速偏离常态时微调。\n* **风险溢价 (ERP)**：市场极度恐慌或狂热时手动修正。",
        "erp_label": "股市风险溢价要求 (Equity Risk Premium)",
        "g2_label": "长期永续通胀增长率 (Terminal Growth Rate)",
        "esg_caption": "🌿 本系统已自动结合可持续金融 (Sustainable Finance) 与 ESG 行业风险溢价进行折现率修正。",
        "macro_title": "[1. 动态宏观与资本成本 (DYNAMIC MACRO & COST OF CAPITAL)]",
        "macro_exp": "💡 **通俗解释：** Beta 衡量波动率。Rf 是无风险利率。WACC 是你作为投资者要求的最低及格线回报率。",
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
        "note_dcf": "基于线性衰减自由现金流与 WACC 折现。",
        "note_ddm": "基于历史股息分红及永续增长率折现。",
        "note_pe": "基于每股收益 (EPS) 乘以合理市盈率倍数。",
        "price": "当前市场价格",
        "fair_val": "内在公道估值 (衰减后)",
        "fair_val_desc": "💡 **关于【公道估值】**：剥离短期炒作，算出保守身价。“衰减后”代表模型让高速增长逐年平稳递减，防止科技巨头复利失真。",
        "safe_buy": "20% 安全边际买点",
        "heat_title": "[3. 🌡️ 核心参数敏感性分析矩阵 (DCF SENSITIVITY HEATMAP)]",
        "heat_desc": "👉 <span style='color:#10b981;'>**绿色区域**</span> 代表该参数下当前市价被低估；<span style='color:#ef4444;'>**红色区域**</span> 代表高估。",
        "lie_title": "[4. 💡 市场情绪测谎仪 (MARKET PSYCHOLOGY)]",
        "lie_exp": "💡 测谎仪通过二分法反向推导，看看当前市价到底在幻想这家公司未来每年增长多少。",
        "ai_title": "[5. 🤖 双视角 AI 投资顾问]",
        "inc_title": "🔸 视角 A：保守派收息策略",
        "cap_title": "🔹 视角 B：进取派资本增值",
        "exec_title": "[6. 🎯 最终投资评级与执行摘要]",
        "rating_explain": "ℹ️ *好公司不等于好价格。若缺乏安全边际，系统将触发 SELL。*",
        "plain_title": "[7. 🗣️ 小白通俗翻译器]",
        "fx_title": "[8. 💱 跨境汇率风险提示]",
        "fx_content": "- **提示：** 此乃美元计价资产，请注意 USD/MYR 的汇率波动风险。",
        "ws_title": "🏛️ [9. 华尔街投行分析师共识与预期差]",
        "ws_mean": "投行平均目标价",
        "ws_range": "目标价区间",
        "ws_rating": "投行综合评级",
        "ws_tag": "投行机构共识",
        "gap_title": "⚡ 华尔街 vs 量化模型：深度预期差雷达",
        "gap_line1": "量化内在公允价",
        "gap_line2": "华尔街平均目标价",
        "gap_line3": "预期差偏离度",
        "gap_desc_high": "华尔街目标价比模型估值高出",
        "gap_alert_high": "🚨 **【预期差警示】**：华尔街目标价远高于量化底线，长线价值投资者需警惕。",
        "gap_alert_low": "🔥 **【深度价值】**：量化模型价值高于卖方预期，属于潜在布局区。",
        "ws_match": "✅ 模型算出的公道价与华尔街机构预测高度吻合！",
        "chart_title": "[10. 📈 高级盘面与波动率回归分析]",
        "beta_desc": "📊 **$R^2$补充解析**：点越密集贴近红线，说明受大盘主导；点越分散，说明具个股独立行情。",
        "glossary_title": "[11. 📖 小白通俗金融词典]",
        "g_beta_title": "##### 🎯 Beta (波动敏感度)",
        "g_beta_desc": "Beta > 1 涨跌比大盘更猛，Beta < 1 走势更抗跌防守。",
        "g_growth_title": "##### 🚀 Growth (预期增长率)",
        "g_growth_desc": "未来公司现金流预计每年递增的比例。",
        "g_wacc_title": "##### 🛡️ WACC / 折现率",
        "g_wacc_desc": "买入这家公司所要求的最低年化回报门槛。",
        "g_fv_title": "##### 💎 Fair Value (内在公道价)",
        "g_fv_desc": "剥离情绪，根据真实赚钱能力算出的厂牌公道价。",
        "disclaimer_title": "[12. ⚠️ 重要法律与风险免责声明]",
        "disclaimer_1": "1. **非投资建议**：本系统仅供学术研究与教学参考，不构成任何投资建议。",
        "disclaimer_2": "2. **市场风险**：股票市场波动剧烈，历史数据无法预知未来。",
        "disclaimer_3": "3. **自主决策**：任何投资决策均应由投资者自行做出。"
    },
    "en": {
        "title": "🌐 Universal Quant & Derivatives Terminal (Flagship V9.6)",
        "subtitle": "Integrating Fading Growth DCF, Capex Waterfall, Dynamic NWC, LBO, Comps, Monte Carlo, Efficient Frontier & AI Options Strategist",
        "quick_tag": "🔥 Quick Select:",
        "input_label": "Enter Stock Ticker (e.g., 1155.KL, NVDA, AAPL):",
        "param_title": "⚙️ Step 2: Macro & Valuation Parameters (Defaults Recommended)",
        "param_tip": "💡 **When to adjust?**\n* **Terminal Growth (g)**: Adjust if long-term inflation/GDP growth deviates.\n* **Risk Premium (ERP)**: Adjust during extreme market cycles.",
        "erp_label": "Equity Risk Premium (ERP)",
        "g2_label": "Terminal Growth Rate (g)",
        "esg_caption": "🌿 Sustainable Finance & ESG Risk Premium automatically integrated.",
        "macro_title": "[1. DYNAMIC MACRO & COST OF CAPITAL]",
        "macro_exp": "💡 **Explanation:** Beta measures stock volatility. Rf is the benchmark bond yield. WACC is your hurdle rate.",
        "matrix_header": "[2. Multi-Model Valuation Matrix (DCF + DDM + P/E)]",
        "model_dcf_name": "Two-Stage Fading Growth DCF",
        "model_ddm_name": "Dividend Discount Model (DDM)",
        "model_pe_name": "P/E Multiples Valuation",
        "badge_recommended": "⭐ System Recommended",
        "badge_reference": "📌 Reference",
        "no_data_dcf": "Negative or Missing FCF",
        "no_data_ddm": "Company pays no dividend",
        "no_data_pe": "Company in net loss",
        "vs_market": "vs Market",
        "note_dcf": "Based on linear fading FCF and WACC.",
        "note_ddm": "Based on historical dividends.",
        "note_pe": "Based on EPS and benchmark P/E.",
        "price": "Current Market Price",
        "fair_val": "Intrinsic Fair Value (Faded)",
        "fair_val_desc": "💡 **Explanation**: Strips away hype. 'Faded' prevents multi-year compounding errors.",
        "safe_buy": "Safe Buy Target (20% MoS)",
        "heat_title": "[3. 🌡️ DCF SENSITIVITY HEATMAP]",
        "heat_desc": "👉 <span style='color:#10b981;'>**Green zones**</span> indicate undervalued; <span style='color:#ef4444;'>**Red zones**</span> indicate overvalued.",
        "lie_title": "[4. 💡 MARKET PSYCHOLOGY (LIE DETECTOR)]",
        "lie_exp": "💡 Uses reverse-engineering to find what growth rate investors are currently pricing in.",
        "ai_title": "[5. 🤖 DUAL-PERSPECTIVE AI ADVISORY]",
        "inc_title": "🔸 Perspective A: Conservative Income",
        "cap_title": "🔹 Perspective B: Capital Appreciation",
        "exec_title": "[6. 🎯 FINAL EXECUTIVE SUMMARY & RATING]",
        "rating_explain": "ℹ️ *Good company ≠ Good price. Lack of Margin of Safety triggers SELL.*",
        "plain_title": "[7. 🗣️ PLAIN ENGLISH TRANSLATOR]",
        "fx_title": "[8. 💱 CROSS-BORDER FX RISK]",
        "fx_content": "- **Note:** USD asset; monitor USD/MYR fluctuations.",
        "ws_title": "🏛️ [9. Wall Street Analyst Consensus]",
        "ws_mean": "Analyst Average Target Price",
        "ws_range": "Target Price Range",
        "ws_rating": "Consensus Rating",
        "ws_tag": "Institutional Consensus",
        "gap_title": "⚡ Wall Street vs. Quant Model: Expectation Gap",
        "gap_line1": "Model Fair Value",
        "gap_line2": "Wall Street Target Mean",
        "gap_line3": "Divergence Gap",
        "gap_desc_high": "Wall Street target is higher by",
        "gap_alert_high": "🚨 **[Warning]**: Wall Street targets far exceed the quant model. Remain cautious.",
        "gap_alert_low": "🔥 **[Deep Value]**: Quant model exceeds Wall Street expectations.",
        "ws_match": "✅ Your Valuation aligns tightly with Wall Street targets!",
        "chart_title": "[10. Advanced Price Action & Regression Analysis]",
        "beta_desc": "📊 **$R^2$ Analysis**: Tight clustering indicates systemic risk; high dispersion reflects independent trends.",
        "glossary_title": "[11. Beginner's Financial Glossary]",
        "g_beta_title": "##### 🎯 Beta (Sensitivity)",
        "g_beta_desc": "Beta > 1 means higher aggression, Beta < 1 indicates defensive traits.",
        "g_growth_title": "##### 🚀 Expected Growth Rate",
        "g_growth_desc": "The projected annual growth rate of company cash flows.",
        "g_wacc_title": "##### 🛡️ WACC / Discount Rate",
        "g_wacc_desc": "The minimum hurdle rate of return required.",
        "g_fv_title": "##### 💎 Intrinsic Fair Value",
        "g_fv_desc": "Intrinsic value based on earning power, stripping away hype.",
        "disclaimer_title": "[12. ⚠️ Important Legal & Risk Disclaimer]",
        "disclaimer_1": "1. **Not Investment Advice**: For academic research and educational purposes only.",
        "disclaimer_2": "2. **Market Risk**: Historical data cannot predict the future.",
        "disclaimer_3": "3. **Independent Decision**: All decisions must be made independently."
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
# 3. 核心硬核量化引擎 
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
        
        raw_fcf = self.info.get('freeCashflow', 0)
        if raw_fcf <= 0: raw_fcf = get_fin_metric(self.cfs, 'Free Cash Flow', 0)
        if raw_fcf <= 0: raw_fcf = max(self.net_income * 0.6, self.ebitda * 0.15, 1000000) if self.net_income > 0 else self.revenue * 0.05
        self.cf = raw_fcf

        self.market_cap = self.price * self.shares
        self.ev = self.market_cap + self.debt - self.cash
        self.scatter_data = None 
        self.hardcore_ufcf_proj = []

    def get_esg_adjustment(self):
        if self.sector in ['Energy', 'Basic Materials', 'Industrials']: return 0.015, "🔴 High ESG Risk"
        elif self.sector in ['Technology', 'Healthcare', 'Financial Services']: return -0.005, "🟢 Low ESG Risk"
        return 0.00, "⚪ Neutral ESG Risk"

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
        self.wacc = max((w_e * self.ke) + (w_d * kd * (1 - self.tax)), terminal_g + 0.02)
        
        self.g1 = min(max(self.info.get('earningsGrowth', 0) or 0.08, 0.03), 0.25)
        self.g2 = terminal_g
        self.horizon = 10 if self.sector in ['Technology', 'Communication Services'] else 5

        self.val_dcf = self.calc_specific_dcf(self.wacc, self.g2)
        div = self.info.get('dividendRate') or self.info.get('trailingAnnualDividendRate') or 0.0
        self.val_ddm = ((div * (1.0 + min(self.g2, self.ke - 0.01))) / (self.ke - min(self.g2, self.ke - 0.01))) if div > 0 and self.ke > self.g2 else None
        
        eps = self.info.get('trailingEps') or self.info.get('forwardEps') or (self.net_income / self.shares if self.net_income > 0 else 0)
        bench_pe = 24.0 if self.sector in ['Technology', 'Communication Services'] else (11.5 if self.sector == 'Financial Services' else 16.0)
        self.val_pe = eps * bench_pe if eps > 0 else None

        if self.sector in ['Financial Services', 'Real Estate', 'Utilities'] and self.val_ddm:
            self.model_name = 'Dividend Discount Model (DDM)'
            self.r, val = self.ke, self.val_ddm
        elif self.val_dcf:
            self.model_name = 'Discounted Cash Flow (DCF)'
            self.r, val = self.wacc, self.val_dcf
        elif self.val_pe:
            self.model_name = 'P/E Multiples Valuation'
            self.r, val = self.wacc, self.val_pe
        else:
            self.model_name = 'Discounted Cash Flow (DCF)'
            self.r, val = self.wacc, 0.0
        return val, self.find_implied_growth()

    def calc_specific_dcf(self, test_wacc, test_g2):
        if self.cf <= 0 or test_wacc <= test_g2: return None
        pv1, curr_cf = 0, self.cf
        growth_rates = np.linspace(self.g1, test_g2, self.horizon)
        for y in range(1, self.horizon + 1):
            curr_cf *= (1 + growth_rates[y - 1])
            pv1 += curr_cf / ((1 + test_wacc) ** y)
        pv_tv = (curr_cf * (1 + test_g2)) / (test_wacc - test_g2) / ((1 + test_wacc) ** self.horizon)
        return (pv1 + pv_tv + self.cash - self.debt) / self.shares if self.shares > 0 else 0

    def find_implied_growth(self):
        if self.price <= 0 or self.cf <= 0: return None
        low, high = -0.50, 2.00
        for _ in range(50):
            mid = (low + high) / 2
            val = self.calc_specific_dcf(self.wacc, mid) or 0
            if val < self.price: low = mid
            else: high = mid
        return mid

    def build_hardcore_3_statement(self, dso, dio, dpo, capex_pct):
        years = ['Year 0 (Current)', 'Year 1', 'Year 2', 'Year 3', 'Year 4', 'Year 5']
        rev_0, cogs_0 = self.revenue, self.cogs if self.cogs > 0 else self.revenue * 0.5
        ebitda_margin = self.ebitda / self.revenue if self.revenue > 0 else 0.2
        rev, cogs, ebitda, da, capex, ar, inv, ap, nwc, dnwc, ufcf = [rev_0], [cogs_0], [self.ebitda], [self.hist_da], [rev_0 * capex_pct], [(dso/365)*rev_0], [(dio/365)*cogs_0], [(dpo/365)*cogs_0], [0], [0], [self.cf]
        nwc[0] = ar[0] + inv[0] - ap[0]
        new_capex = []
        for i in range(1, 6):
            g = self.g1 - (self.g1 - self.g2) * (i / 5)
            r = rev[-1] * (1 + g)
            c = cogs[-1] * (1 + g)
            e = r * ebitda_margin
            cap = r * capex_pct
            rev.append(r); cogs.append(c); ebitda.append(e); capex.append(cap); new_capex.append(cap)
            curr_da = max(0, self.hist_da * (1 - 0.2 * i)) + sum(new_capex) * 0.2
            da.append(curr_da)
            curr_nwc = (dso/365)*r + (dio/365)*c - (dpo/365)*c
            nwc.append(curr_nwc); dnwc.append(curr_nwc - nwc[-2])
            ufcf.append((e - curr_da) * (1 - self.tax) + curr_da - cap - dnwc[-1])
        self.hardcore_ufcf_proj = ufcf[1:] 
        df = pd.DataFrame({"Revenue": rev, "EBITDA": ebitda, "(-) D&A": [-d for d in da], "(=) EBIT": [e-d for e,d in zip(ebitda, da)], "NOPAT": [(e-d)*(1-self.tax) for e,d in zip(ebitda,da)], "(-) Capex": [-c for c in capex], "(-) Δ NWC": [-d for d in dnwc], "(=) UFCF": ufcf}, index=years).T
        return df

    def run_lbo_model(self, ltv_ratio, interest_rate, exit_multiple):
        purchase_price = self.ev
        debt_funding, equity_funding = purchase_price * ltv_ratio, purchase_price * (1 - ltv_ratio)
        debt_schedule = [debt_funding]
        for fcf in self.hardcore_ufcf_proj:
            debt_schedule.append(max(0, debt_schedule[-1] - max(0, fcf - (debt_schedule[-1] * interest_rate))))
        exit_ev = self.ebitda * (self.revenue/self.ebitda if self.ebitda>0 else 1) * exit_multiple
        exit_equity = exit_ev - debt_schedule[-1]
        moic = exit_equity / equity_funding if equity_funding > 0 else 0
        return {"Entry EV": purchase_price, "Debt": debt_funding, "Equity": equity_funding, "Exit EV": exit_ev, "Exit Debt": debt_schedule[-1], "Exit Equity": exit_equity, "MOIC": moic, "IRR": (moic ** 0.2) - 1 if moic > 0 else 0, "Debt Schedule": debt_schedule}

    def run_comps_analysis(self):
        peer_map = {'NVDA': ['AMD', 'INTC', 'TSM', 'QCOM'], 'AAPL': ['MSFT', 'GOOGL', 'AMZN', 'META'], 'TSLA': ['RIVN', 'F', 'GM', 'TM'], '1155.KL': ['1023.KL', '1295.KL', '1188.KL', '5819.KL'], '5347.KL': ['5264.KL', '1155.KL', '1023.KL']}
        peers = peer_map.get(self.ticker, ['1155.KL', '1023.KL', '1295.KL', '5347.KL'] if self.is_malaysia else ['AAPL', 'MSFT', 'GOOGL', 'AMZN'])
        if self.ticker in peers: peers.remove(self.ticker)
        comp_data = [{"Ticker": self.ticker, "Name": self.name[:12], "Market Cap ($B)": round(self.market_cap / 1e9, 2), "EV/EBITDA": round(self.ev / self.ebitda, 2) if self.ebitda > 0 else 0, "P/E": round(self.info.get('trailingPE', 0), 2), "Gross Margin %": round(self.info.get('grossMargins', 0) * 100, 1)}]
        for p in peers:
            try:
                pi = yf.Ticker(p, session=self.session).info
                comp_data.append({"Ticker": p, "Name": pi.get('shortName', p)[:12], "Market Cap ($B)": round(pi.get('marketCap', 1e9) / 1e9, 2), "EV/EBITDA": round((pi.get('marketCap',1e9)+pi.get('totalDebt',0)-pi.get('totalCash',0))/pi.get('ebitda',1e6), 2), "P/E": round(pi.get('trailingPE', 0), 2), "Gross Margin %": round(pi.get('grossMargins', 0) * 100, 1)})
            except Exception: pass
        return pd.DataFrame(comp_data)

    def run_monte_carlo(self, sims=2000):
        if self.cf <= 0: return []
        np.random.seed(42)
        results = [self.calc_specific_dcf(w, g) for w, g in zip(np.random.normal(self.wacc, 0.015, sims), np.random.normal(self.g2, 0.005, sims)) if w > g + 0.005]
        return [r for r in results if r and r > 0]

    def black_scholes_pricing(self, S, K, T, r, sigma, q=0.0):
        if T <= 0 or sigma <= 0 or S <= 0 or K <= 0: return {"Call": 0.0, "Put": 0.0, "Delta_C": 0.0, "Delta_P": 0.0, "Gamma": 0.0, "Theta_C": 0.0, "Theta_P": 0.0, "Vega": 0.0, "Rho_C": 0.0, "Rho_P": 0.0}
        d1 = (np.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        return {
            "Call": S * np.exp(-q * T) * stats.norm.cdf(d1) - K * np.exp(-r * T) * stats.norm.cdf(d2),
            "Put": K * np.exp(-r * T) * stats.norm.cdf(-d2) - S * np.exp(-q * T) * stats.norm.cdf(-d1),
            "Delta_C": np.exp(-q * T) * stats.norm.cdf(d1), "Delta_P": -np.exp(-q * T) * stats.norm.cdf(-d1),
            "Gamma": (np.exp(-q * T) * stats.norm.pdf(d1)) / (S * sigma * np.sqrt(T)),
            "Vega": S * np.exp(-q * T) * stats.norm.pdf(d1) * np.sqrt(T) / 100.0,
            "Theta_C": (- (S * sigma * np.exp(-q * T) * stats.norm.pdf(d1)) / (2 * np.sqrt(T)) - r * K * np.exp(-r * T) * stats.norm.cdf(d2) + q * S * np.exp(-q * T) * stats.norm.cdf(d1)) / 365.0,
            "Theta_P": (- (S * sigma * np.exp(-q * T) * stats.norm.pdf(d1)) / (2 * np.sqrt(T)) + r * K * np.exp(-r * T) * stats.norm.cdf(-d2) - q * S * np.exp(-q * T) * stats.norm.cdf(-d1)) / 365.0,
            "Rho_C": K * T * np.exp(-r * T) * stats.norm.cdf(d2) / 100.0, "Rho_P": -K * T * np.exp(-r * T) * stats.norm.cdf(-d2) / 100.0
        }

# ==============================================================================
# 4. 图表生成 (热力图 + K线 + Beta)
# ==============================================================================
def draw_sensitivity_heatmap(engine):
    if engine.cf <= 0: return None, None
    wacc_vals, g2_vals = engine.wacc + np.array([-0.02, -0.01, 0.0, 0.01, 0.02]), engine.g2 + np.array([-0.01, -0.005, 0.0, 0.005, 0.01])
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
        max_diff = max(abs(max(valid_z) - engine.price), abs(min(valid_z) - engine.price)) if valid_z else 1.0 
        stats = {'best': max(valid_z), 'worst': min(valid_z), 'green_count': sum(1 for v in valid_z if v >= engine.price), 'total': len(valid_z), 'win_rate': sum(1 for v in valid_z if v >= engine.price) / len(valid_z)}
    else: max_diff, stats = 1.0, None
    fig = go.Figure(data=go.Heatmap(z=z_vals, x=[f"{g*100:.1f}%" for g in g2_vals], y=[f"{w*100:.1f}%" for w in wacc_vals], text=np.array(z_vals), texttemplate="%{text:.2f}", hoverinfo="text", hovertext=hover_text, colorscale=[[0.0, '#ef4444'], [0.5, '#1e293b'], [1.0, '#10b981']], zmin=engine.price-max_diff, zmax=engine.price+max_diff, showscale=False))
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=320, xaxis_title="Terminal Growth Rate (g) ➡️", yaxis_title="WACC (Discount Rate) ⬇️", yaxis=dict(autorange='reversed', showgrid=False, zeroline=False), xaxis=dict(showgrid=False, zeroline=False), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#94a3b8'))
    return fig, stats

def draw_pro_candlestick(ticker, session):
    hist = yf.Ticker(ticker, session=session).history(period="1y", interval="1d")
    if hist.empty: return None
    hist['MA20'], hist['MA50'] = hist['Close'].rolling(20).mean(), hist['Close'].rolling(50).mean()
    fig = go.Figure(data=[go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], name='Price'), go.Scatter(x=hist.index, y=hist['MA20'], line=dict(color='#f59e0b', width=1.5), name='20-Day SMA'), go.Scatter(x=hist.index, y=hist['MA50'], line=dict(color='#3b82f6', width=1.5), name='50-Day SMA')])
    fig.update_layout(xaxis_rangeslider_visible=False, height=350, margin=dict(l=0, r=0, t=10, b=0), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#94a3b8'), xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'), yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'), legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01))
    return fig

def draw_beta_scatter(engine):
    if engine.scatter_data is None: return None
    stock_ret, market_ret = engine.scatter_data.iloc[:, 0], engine.scatter_data.iloc[:, 1]
    r_sq = np.corrcoef(stock_ret, market_ret)[0, 1] ** 2 if not np.isnan(np.corrcoef(stock_ret, market_ret)[0, 1]) else 0.0
    fig = go.Figure(data=[go.Scatter(x=market_ret, y=stock_ret, mode='markers', marker=dict(color='#38bdf8', size=7, opacity=0.8)), go.Scatter(x=np.linspace(market_ret.min(), market_ret.max(), 100), y=engine.beta * np.linspace(market_ret.min(), market_ret.max(), 100), mode='lines', line=dict(color='#ef4444', width=2))])
    fig.update_layout(title=dict(text=f"Beta Regression (Beta = {engine.beta:.2f} | R² = {r_sq:.2f})", font=dict(color='#ffffff')), xaxis_title="Market Benchmark", yaxis_title="Stock Return (%)", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#94a3b8'), showlegend=False, height=330, margin=dict(l=0, r=0, t=35, b=0))
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
        with col_in1: ticker_input = st.text_input(T['input_label'], key="ticker_input")
        
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

            tabs_zh = [
                "📊 [1] Quant Valuation Dashboard (量化估值终端)", "⚙️ [2] Hardcore 3-Statement & NWC (硬核财报排程)", 
                "🏛️ [3] Dynamic LBO & Debt Schedule (动态收购沙盘)", "🏢 [4] Comps Matrix (同业可比公司矩阵)",
                "🎲 [5] Monte Carlo (蒙特卡洛模拟)", "📈 [6] Efficient Frontier (有效前沿资产配置)", "📉 [7] Options & AI Strategist (期权与智能策略)"
            ]
            tabs_en = [
                "📊 [1] Quant Valuation Dashboard", "⚙️ [2] Hardcore 3-Statement & NWC", 
                "🏛️ [3] Dynamic LBO & Debt Schedule", "🏢 [4] Comps Matrix",
                "🎲 [5] Monte Carlo", "📈 [6] Efficient Frontier", "📉 [7] Options & AI Strategist"
            ]
            tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(tabs_zh if lang_key == "zh" else tabs_en)

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
                        diff = (model_val - price) / price * 100.0 if price > 0 else 0
                        status_html = f"<div style='color: {'#22c55e' if diff > 0 else '#f43f5e'}; font-weight: 700; font-size: 13px;'>{'+' if diff > 0 else ''}{diff:.1f}% {T['vs_market']}</div>"
                        val_str = f"{currency} {model_val:.2f}"
                    else:
                        val_str, status_html = "N/A", f"<div style='color: #f87171; font-size: 12px;'>⚠️ {empty_msg}</div>"
                    return f"""<div style="background: linear-gradient(135deg, rgba(30,41,59,0.9) 0%, rgba(15,23,42,0.95) 100%); border: 1.5px solid {card_border}; border-radius: 12px; padding: 18px; min-height: 175px; display: flex; flex-direction: column; justify-content: space-between;"><div><div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;"><span style="font-size: 14px; font-weight: 700; color: #f8fafc;">{title}</span><span style="background: rgba(56,189,248,0.15); color: #38bdf8; font-size: 10.5px; font-weight: 700; padding: 2px 8px; border-radius: 12px;">{badge_text}</span></div><div style="font-family: 'JetBrains Mono', monospace; font-size: 26px; font-weight: 800; color: #ffffff; margin: 4px 0;">{val_str}</div><div>{status_html}</div></div><div style="color: #94a3b8; font-size: 11.5px; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 8px; margin-top: 8px;">💡 {note}</div></div>"""

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
                                if wr >= 0.70:
                                    ai_insight = f"🟢 <b>高胜率 / 低估 (High Margin of Safety):</b> 无论宏观折现率如何波动，绝大多数预测情景（{heat_stats['green_count']}/{heat_stats['total']}）都显示该公司当前市价被严重低估，具备极厚的安全垫。" if lang_key == "zh" else f"🟢 <b>High Margin of Safety:</b> Across the majority of scenarios ({heat_stats['green_count']}/{heat_stats['total']}), the stock is heavily undervalued."
                                elif wr <= 0.30:
                                    ai_insight = f"🔴 <b>高风险 / 高估 (Overvalued & Fragile):</b> 当前市价已透支未来。除非公司能在极低利率下保持疯狂增长，否则面临估值杀跌风险。" if lang_key == "zh" else f"🔴 <b>Overvalued & Fragile:</b> The current price prices in perfection. High risk of multiple contraction."
                                else:
                                    ai_insight = "🟡 <b>高度敏感 / 合理偏高 (Highly Sensitive):</b> 估值处于微妙的平衡点。当前价格对宏观利率(WACC)极为敏感，没有单边套利空间。" if lang_key == "zh" else "🟡 <b>Highly Sensitive:</b> Valuation is highly sensitive to macro rates. Fairly priced with no clear arbitrage."

                                win_str = "胜率测算:" if lang_key == "zh" else "Win Rate:"
                                in_str = "在" if lang_key == "zh" else "In"
                                sc_str = "种宏观情景中，有" if lang_key == "zh" else "scenarios, "
                                safe_str = "种具备安全边际。" if lang_key == "zh" else "offer a margin of safety."
                                worst_str = "最悲观底线:" if lang_key == "zh" else "Worst Case (Floor):"
                                best_str = "最乐观上限:" if lang_key == "zh" else "Best Case (Ceiling):"

                                st.markdown(f"""
                                <div style="background: rgba(15, 23, 42, 0.6); border-left: 4px solid #38bdf8; padding: 16px; border-radius: 6px; margin-top: 10px;">
                                    <div style="color: #38bdf8; font-weight: 800; font-size: 15px; margin-bottom: 8px;">🤖 AI Sensitivity Summary</div>
                                    <div style="color: #e2e8f0; font-size: 14px; margin-bottom: 12px; line-height: 1.6;">{ai_insight}</div>
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
                                diag = "-> **Diagnosis: EXTREME HYPE (Bubble Territory).**" if implied_g > 0.40 else ("-> **Diagnosis: EXTREME PESSIMISM.**" if implied_g < 0.0 else "-> **Diagnosis: MODERATE EXPECTATIONS.**")
                                st.write(diag)
                            st.caption(T['lie_exp'])

                    with col_ai:
                        with st.container(border=True):
                            st.markdown(f"**{T['ai_title']}**")
                            div_yield = ((engine.info.get('dividendRate') or engine.info.get('trailingAnnualDividendRate') or 0) / engine.price) * 100 if engine.price > 0 else 0
                            st.markdown(T['inc_title'])
                            st.write(f"- Dividend Yield: {div_yield:.2f}% | Beta Risk: {engine.beta:.2f}")
                            st.success("-> **Verdict:** 🟢 SUITABLE FOR INCOME.") if engine.sector in ['Financial Services', 'Utilities', 'Real Estate'] and div_yield > 3.0 else st.error("-> **Verdict:** 🔴 NOT IDEAL FOR INCOME.")
                            st.markdown(T['cap_title'])
                            st.write(f"- Implied Growth: {implied_g_str} | Model Valuation: {val:.2f}")
                            if implied_g is not None and implied_g < 0.0 and engine.price < val: st.success("-> **Verdict:** 🟢 MULTI-BAGGER POTENTIAL.")
                            elif implied_g is not None and implied_g > 0.40: st.error("-> **Verdict:** 🔴 HIGH SPECULATION RISK.")
                            else: st.info("-> **Verdict:** 🟢 / 🟡 FAIRLY PRICED.")

                    st.markdown(f"### {T['exec_title']}")
                    if price_to_val <= 0.70 and (implied_g is not None and implied_g < 0.0): rating, reason = '🟢 STRONG BUY', 'Extreme pessimism creates massive margin of safety.'
                    elif price_to_val <= 0.85: rating, reason = '🟢 BUY', 'Solid value mispricing. 20% margin of safety met.'
                    elif 0.85 < price_to_val <= 1.15: rating, reason = '🟡 HOLD', 'Fairly valued. Aligns with intrinsic value.'
                    elif 1.15 < price_to_val <= 1.40: rating, reason = '🔴 SELL', 'Overvalued. Lacks margin of safety.'
                    else: rating, reason = '🔴 STRONG SELL', 'Severe bubble risk. Priced for perfection.'

                    with st.container(border=True):
                        st.markdown(f"- **Final Investment Rating : {rating}**\n- **Core Justification : {reason}**")
                        st.caption(T['rating_explain'])

                    col_t1, col_t2 = st.columns(2)
                    with col_t1:
                        with st.container(border=True):
                            st.markdown(f"**{T['plain_title']}**")
                            st.markdown(f"- **Required Hurdle Rate / Discount Rate:** {engine.r * 100:.2f}%\n  👉 Minimum required return.")
                            if implied_g is not None:
                                st.markdown(f"- **Market Sentiment / Implied Growth:** {implied_g * 100:.2f}%")
                                st.markdown("  👉 **【⚠️ SEVERE BUBBLE WARNING】**" if implied_g > 0.35 else ("  👉 **【🔥 EXTREME PESSIMISM / DEEP VALUE】**" if implied_g < 0.0 else "  👉 **【⚖️ BALANCED & RATIONAL】**"))
                    
                    with col_t2:
                        with st.container(border=True):
                            st.markdown(f"**{T['fx_title']}**")
                            st.warning("- 🇲🇾 本地资产计价 (MYR)，无直接跨境外汇风险暴露。" if engine.is_malaysia and lang_key == "zh" else ("- 🇲🇾 Local asset (MYR), no direct cross-border FX exposure." if engine.is_malaysia else T['fx_content']))

                    if not engine.is_malaysia:
                        target_mean, target_high, target_low, num_analysts = engine.info.get('targetMeanPrice'), engine.info.get('targetHighPrice'), engine.info.get('targetLowPrice'), engine.info.get('numberOfAnalystOpinions', 0)
                        rec_key = str(engine.info.get('recommendationKey', 'N/A')).upper()
                        if target_mean and num_analysts > 0:
                            st.markdown(f"<br><h3>{T['ws_title']}</h3>", unsafe_allow_html=True)
                            ws_col1, ws_col2, ws_col3 = st.columns(3)
                            with ws_col1:
                                with st.container(border=True):
                                    st.markdown(f"<div style='color:#94a3b8; font-size:13px; font-weight:600; text-align:center;'>{T['ws_mean']}</div><div style='font-size:30px; font-weight:800; font-family:JetBrains Mono; text-align:center; color:#ffffff; margin: 10px 0;'>${target_mean:.2f}</div><div style='color:#38bdf8; font-size:12.5px; text-align:center;'>👥 {num_analysts} Analysts</div>", unsafe_allow_html=True)
                            with ws_col2:
                                with st.container(border=True):
                                    st.markdown(f"<div style='color:#94a3b8; font-size:13px; font-weight:600; text-align:center;'>{T['ws_range']}</div><div style='font-size:24px; font-weight:800; font-family:JetBrains Mono; text-align:center; color:#ffffff; margin: 12px 0;'>${target_low or 0:.2f} ~ ${target_high or 0:.2f}</div><div style='color:#cbd5e1; font-size:12px; text-align:center;'>Low / High Target</div>", unsafe_allow_html=True)
                            with ws_col3:
                                with st.container(border=True):
                                    st.markdown(f"<div style='color:#94a3b8; font-size:13px; font-weight:600; text-align:center;'>{T['ws_rating']}</div><div style='font-size:28px; font-weight:800; font-family:JetBrains Mono; text-align:center; color:#38bdf8; margin: 10px 0;'>{rec_key}</div><div style='color:#4ade80; font-size:12px; text-align:center;'>🏛️ {T['ws_tag']}</div>", unsafe_allow_html=True)
                            
                            with st.container(border=True):
                                st.markdown(f"**{T['gap_title']}**")
                                gap_pct = ((target_mean - val) / val) * 100.0
                                st.write(f"- **{T['gap_line1']}:** `${val:.2f}` | **{T['gap_line2']}:** `${target_mean:.2f}`\n- **{T['gap_line3']}:** `+{gap_pct:.1f}%` ({T['gap_desc_high']} {gap_pct:.1f}%)")
                                if gap_pct > 25.0 and rec_key in ["BUY", "STRONG_BUY"]: st.error(T['gap_alert_high'])
                                elif abs(gap_pct) <= 15.0: st.success(T['ws_match'])
                                elif gap_pct < -15.0: st.info(T['gap_alert_low'])

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
                        with st.container(border=True): st.markdown(T['g_beta_title']); st.caption(T['g_beta_desc'])
                    with g2:
                        with st.container(border=True): st.markdown(T['g_growth_title']); st.caption(T['g_growth_desc'])
                    with g3:
                        with st.container(border=True): st.markdown(T['g_wacc_title']); st.caption(T['g_wacc_desc'])
                    with g4:
                        with st.container(border=True): st.markdown(T['g_fv_title']); st.caption(T['g_fv_desc'])

            # ==========================================
            # TAB 2: 硬核财报排程 
            # ==========================================
            with tab2:
                st.markdown("#### ⚙️ Hardcore 3-Statement Forecast (NWC & Depreciation Engine)")
                st.caption("Adjust the Working Capital (DSO/DIO/DPO) and Capex drivers below to dynamically alter the Free Cash Flow (FCF) generation." if lang_key == "en" else "调整下方营运资本 (DSO/DIO/DPO) 和资本开支，以动态改变自由现金流。")
                
                expander_title_tab2 = "📖 【新手必读 / 核心参数调整指南】营运资本与资本开支 (点击展开)" if lang_key == "zh" else "📖 [Must Read] Operating Assumptions Guide (Click to Expand)"
                guide_tab2 = """
                * **DSO (应收账款天数)**：衡量客户平均需多少天付清账单。默认~45天。预计产业链拖账严重时**调大**。
                * **DIO (存货天数)**：衡量货物在仓库躺几天。默认~30天。供应链滞销时**调大**。
                * **DPO (应付账款天数)**：公司平均多少天付钱给供应商。默认~60天。若想测试极致现金流能力，可**调大**。
                * **Capex % of Revenue (资本开支比)**：每年收入多少比例用于买厂房/设备。扩产期**调高**，维护期**调低**。
                """ if lang_key == "zh" else """
                * **DSO (Days Sales Outstanding)**: Days to collect cash from customers. Increase if credit environment tightens.
                * **DIO (Days Inventory Outstanding)**: Days inventory sits in warehouse. Increase for heavy manufacturing/delays.
                * **DPO (Days Payable Outstanding)**: Days you take to pay suppliers. Increase to boost short-term cash flow.
                * **Capex % of Revenue**: Capital expenditure as a % of sales. Increase during expansion phases, lower during maintenance.
                """
                with st.expander(expander_title_tab2, expanded=False):
                    st.markdown(guide_tab2)

                with st.container(border=True):
                    st.markdown("**🔧 Operating Assumptions (NWC & Capex Drivers)**")
                    o_col1, o_col2, o_col3, o_col4 = st.columns(4)
                    dso = o_col1.number_input("Days Sales Outstanding (DSO)", value=45)
                    dio = o_col2.number_input("Days Inventory Outstanding (DIO)", value=30)
                    dpo = o_col3.number_input("Days Payable Outstanding (DPO)", value=60)
                    capex_pct = o_col4.number_input("Capex as % of Revenue", value=5.0) / 100.0

                styled_df = engine.build_hardcore_3_statement(dso, dio, dpo, capex_pct).copy()
                for col in styled_df.columns: styled_df[col] = styled_df[col].apply(lambda x: f"{x:,.0f}" if isinstance(x, (int, float)) else x)
                st.dataframe(styled_df, use_container_width=True, height=320)

            # ==========================================
            # TAB 3: LBO 
            # ==========================================
            with tab3:
                st.markdown("#### 🏛️ Dynamic LBO Model & Cash Sweep Schedule")
                
                expander_title_tab3 = "📖 【新手必读 / 核心参数调整指南】杠杆收购 (LBO) (点击展开)" if lang_key == "zh" else "📖 [Must Read] LBO Parameter Guide (Click to Expand)"
                guide_tab3 = """
                * **Debt Leverage (LTV %)**：决定收购时向银行借款的百分比。默认 **60%**。银根紧缩时调低，宽松时调高。
                * **Debt Interest Rate (%)**：借款利息成本。处于加息周期需手动调高。
                * **Exit EV/EBITDA Multiple**：5年后卖掉公司的估值倍数。默认等于当前估值。若预计5年后泡沫破裂需调低。
                """ if lang_key == "zh" else """
                * **Debt Leverage (LTV %)**: % of purchase funded by debt. Default is **60%**. Lower if credit is tight.
                * **Debt Interest Rate (%)**: Annual cost of debt. Adjust based on macro environment.
                * **Exit EV/EBITDA Multiple**: Expected exit multiple in Year 5. Lower it if you expect a future market downturn.
                """
                with st.expander(expander_title_tab3, expanded=False):
                    st.markdown(guide_tab3)

                col_l1, col_l2, col_l3 = st.columns(3)
                ltv = col_l1.slider("Debt Leverage (LTV %)", 30, 80, 60, 5) / 100
                int_rate = col_l2.slider("Debt Interest Rate (%)", 5.0, 15.0, 8.0, 0.5) / 100
                exit_mult = col_l3.slider("Exit EV/EBITDA Multiple", 5.0, 25.0, max(5.0, (engine.ev/engine.ebitda if engine.ebitda>0 else 10.0)), 0.5)

                lbo_res = engine.run_lbo_model(ltv, int_rate, exit_mult)
                c_res1, c_res2, c_res3 = st.columns(3)
                c_res1.metric("Sponsor IRR (5-Year)", f"{lbo_res['IRR']*100:.1f}%")
                c_res2.metric("MOIC (Cash-on-Cash)", f"{lbo_res['MOIC']:.2f}x")
                c_res3.metric("Total Debt Paid Down", f"{engine.currency} {(lbo_res['Debt'] - lbo_res['Exit Debt'])/1e9:.2f}B")

                su_df = pd.DataFrame({"Sources": ["Sponsor Equity", "Senior Debt", "Total Sources"], "Amount": [lbo_res['Equity'], lbo_res['Debt'], lbo_res['Entry EV']], "%": [f"{(1-ltv)*100:.1f}%", f"{ltv*100:.1f}%", "100.0%"]})
                su_df['Amount'] = su_df['Amount'].apply(lambda x: f"{x:,.0f}" if isinstance(x, (int, float)) else x)
                st.table(su_df)
                
                debt_df = pd.DataFrame({"Year": ["0 (Entry)", "1", "2", "3", "4", "5"], "Ending Debt Balance": lbo_res['Debt Schedule']})
                debt_df['Ending Debt Balance'] = debt_df['Ending Debt Balance'].apply(lambda x: f"{x:,.0f}" if isinstance(x, (int, float)) else x)
                st.table(debt_df.set_index('Year').T)

            # ==========================================
            # TAB 4, 5, 6
            # ==========================================
            with tab4:
                st.markdown("#### 🏢 Comparable Company Analysis (Peer Valuation Matrix)" if lang_key == "en" else "#### 🏢 相对估值矩阵 (同业可比公司)")
                st.dataframe(engine.run_comps_analysis(), use_container_width=True)

            with tab5:
                st.markdown("#### 🎲 Monte Carlo Valuation Simulation (2,000 Iterations)")
                mc_results = engine.run_monte_carlo(2000)
                if mc_results:
                    mc_mean, mc_p10, mc_p90 = np.mean(mc_results), np.percentile(mc_results, 10), np.percentile(mc_results, 90)
                    mc1, mc2, mc3 = st.columns(3)
                    mc1.metric("Monte Carlo Mean" if lang_key == "en" else "蒙特卡洛均值", f"{engine.currency} {mc_mean:.2f}")
                    mc2.metric("10% Bear Case (Floor)" if lang_key == "en" else "10% 最差情况", f"{engine.currency} {mc_p10:.2f}")
                    mc3.metric("90% Bull Case (Ceiling)" if lang_key == "en" else "90% 极佳情况", f"{engine.currency} {mc_p90:.2f}")
                    fig_mc = px.histogram(x=mc_results, nbins=50, title="Intrinsic Value Probability Distribution", labels={'x': 'Fair Value', 'y': 'Frequency'})
                    fig_mc.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#94a3b8'))
                    st.plotly_chart(fig_mc, use_container_width=True)

            with tab6:
                st.markdown("#### 📈 Markowitz Efficient Frontier & Portfolio Optimization")
                
                expander_title_tab6 = "📖 【新手必读 / 使用指南】马科维茨有效前沿资产配置 (点击展开)" if lang_key == "zh" else "📖 [Must Read] Markowitz Efficient Frontier Guide"
                guide_tab6 = """
                * **用途**：把几只股票放在一起进行数学优化，找出“风险最低、收益最高”的完美配置比例。
                * **如何操作**：直接在下方输入框中用**英文逗号**隔开输入你想要的股票代码，点击运行即可。
                """ if lang_key == "zh" else """
                * **Purpose**: Mathematically optimizes asset weights to find the highest return for the lowest risk.
                * **How to use**: Enter a comma-separated list of stock tickers below and run the simulation.
                """
                with st.expander(expander_title_tab6, expanded=False):
                    st.markdown(guide_tab6)

                basket_input = st.text_input("Asset Basket Tickers (Comma-separated)", value="NVDA, AAPL, MSFT, GOOGL, AMZN" if not engine.is_malaysia else "1155.KL, 1023.KL, 1295.KL, 5819.KL")
                if st.button("🚀 Run Portfolio Optimization"):
                    with st.spinner("Simulating portfolios..."):
                        try:
                            tickers_list = [t.strip().upper() for t in basket_input.split(",") if t.strip()]
                            data = yf.download(tickers_list, period="1y", interval="1d", session=engine.session)['Close']
                            if isinstance(data, pd.Series): data = data.to_frame()
                            returns = data.pct_change().dropna()
                            num_portfolios, results_matrix = 3000, np.zeros((3 + len(tickers_list), 3000))
                            mean_returns, cov_matrix = returns.mean() * 252, returns.cov() * 252
                            
                            for p in range(num_portfolios):
                                weights = np.random.random(len(tickers_list))
                                weights /= np.sum(weights)
                                p_ret = np.sum(mean_returns * weights)
                                p_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
                                results_matrix[0, p], results_matrix[1, p], results_matrix[2, p] = p_ret, p_vol, (p_ret - 0.03) / p_vol 
                                for i, w in enumerate(weights): results_matrix[3 + i, p] = w
                                
                            max_idx = np.argmax(results_matrix[2])
                            opt1, opt2 = st.columns(2)
                            opt1.metric("Optimal Portfolio Return", f"{results_matrix[0, max_idx]*100:.2f}%")
                            opt2.metric("Optimal Portfolio Volatility", f"{results_matrix[1, max_idx]*100:.2f}%")
                            st.table(pd.DataFrame({"Asset": tickers_list, "Weight (%)": [f"{w*100:.1f}%" for w in results_matrix[3:, max_idx]]}).set_index('Asset').T)
                            
                            fig_ef = px.scatter(x=results_matrix[1], y=results_matrix[0], color=results_matrix[2], labels={'x': 'Volatility (Risk)', 'y': 'Expected Return', 'color': 'Sharpe Ratio'}, title="Markowitz Efficient Frontier")
                            fig_ef.add_trace(go.Scatter(x=[results_matrix[1, max_idx]], y=[results_matrix[0, max_idx]], mode='markers', marker=dict(color='yellow', size=15, symbol='star'), name='Max Sharpe Portfolio'))
                            fig_ef.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#94a3b8'))
                            st.plotly_chart(fig_ef, use_container_width=True)
                        except Exception as e:
                            st.error(f"Error fetching basket data: {e}")

            # ==========================================
            # TAB 7: 期权与智能策略 (完整中英切换)
            # ==========================================
            with tab7:
                st.markdown("#### 📉 Options Chain, Volatility Smile & AI Strategist")
                st.caption("综合期权定价、隐含波动率斜面分析，以及针对持股者与投机者的智能策略推荐。" if lang_key == "zh" else "Comprehensive option pricing, volatility skew analysis, and AI strategy recommendations.")
                
                if engine.is_malaysia:
                    st.warning("⚠️ 马股期权数据在 Yahoo Finance 上极度稀疏。建议切换至美股代码体验完整分析！" if lang_key == "zh" else "⚠️ Bursa Malaysia options data is highly sparse on Yahoo Finance. Test US equities (e.g. NVDA) for full functionality.")
                
                try:
                    exp_dates = engine.stock.options
                    if exp_dates:
                        selected_expiry = st.selectbox("📅 选择期权到期日 (Select Expiration Date)" if lang_key == "zh" else "📅 Select Expiration Date", options=exp_dates)
                        opt_chain, calls, puts = engine.stock.option_chain(selected_expiry), engine.stock.option_chain(selected_expiry).calls, engine.stock.option_chain(selected_expiry).puts
                        T_years = max((datetime.datetime.strptime(selected_expiry, "%Y-%m-%d") - datetime.datetime.now()).days / 365.0, 0.01)
                        S, r = engine.price, engine.rf

                        opt_tabs_zh = ["📈 隐含波动率微笑 (Volatility Smile)", "🛡️ 实时期权链与希腊字母", "🧮 独立 B-S 仿真沙盘", "💡 AI 智能期权顾问 ⭐"]
                        opt_tabs_en = ["📈 Volatility Smile / Skew", "🛡️️ Live Option Chain & Greeks", "🧮 BS Interactive Sandbox", "💡 AI Options Strategist ⭐"]
                        opt_tab1, opt_tab2, opt_tab3, opt_tab4 = st.tabs(opt_tabs_zh if lang_key == "zh" else opt_tabs_en)
                        
                        with opt_tab1:
                            st.markdown(f"**Volatility Smile / Skew for Expiry: {selected_expiry}**")
                            fig_smile = go.Figure()
                            if not calls.empty and 'impliedVolatility' in calls.columns: fig_smile.add_trace(go.Scatter(x=calls[(calls['impliedVolatility'] > 0.01) & (calls['impliedVolatility'] < 3.0)]['strike'], y=calls[(calls['impliedVolatility'] > 0.01) & (calls['impliedVolatility'] < 3.0)]['impliedVolatility']*100, mode='markers+lines', name='Calls IV (%)', marker=dict(color='#38bdf8', size=6)))
                            if not puts.empty and 'impliedVolatility' in puts.columns: fig_smile.add_trace(go.Scatter(x=puts[(puts['impliedVolatility'] > 0.01) & (puts['impliedVolatility'] < 3.0)]['strike'], y=puts[(puts['impliedVolatility'] > 0.01) & (puts['impliedVolatility'] < 3.0)]['impliedVolatility']*100, mode='markers+lines', name='Puts IV (%)', marker=dict(color='#ef4444', size=6)))
                            fig_smile.add_vline(x=S, line_dash="dash", line_color="yellow", annotation_text=f"Spot Price: ${S:.2f}")
                            fig_smile.update_layout(xaxis_title="Strike Price ($) ➡️", yaxis_title="Implied Volatility (%) ⬇️", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#94a3b8'), height=400)
                            st.plotly_chart(fig_smile, use_container_width=True)
                            
                            st.info("""💡 **机构级波动率微笑与斜面解读：** 虚值看跌期权 (现价左侧) 的 IV 通常远高于看涨，这反映了机构对**尾部暴跌风险**极其忌惮，愿意支付高昂溢价买防跌保险。""" if lang_key == "zh" else """💡 **Volatility Smile / Skew Insights:** Out-Of-The-Money (OTM) puts (left of spot) generally command higher Implied Volatility due to institutional panic pricing—investors willingly pay high premiums to hedge against black swan tail risks.""")

                        with opt_tab2:
                            st.markdown("**Live Call Option Chain with Black-Scholes Theoretical Pricing & Greeks**")
                            if not calls.empty:
                                bs_results = [{"Strike": r['strike'], "Market Price": r['lastPrice'], "BS Fair Price": round(engine.black_scholes_pricing(S, r['strike'], T_years, r_rate=0.04, sigma=r['impliedVolatility'] if r['impliedVolatility']>0 else 0.3)['Call'], 2), "IV (%)": round((r['impliedVolatility'] if r['impliedVolatility']>0 else 0.3)*100, 1), "Delta": round(engine.black_scholes_pricing(S, r['strike'], T_years, r_rate=0.04, sigma=r['impliedVolatility'] if r['impliedVolatility']>0 else 0.3)['Delta_C'], 2), "Gamma": round(engine.black_scholes_pricing(S, r['strike'], T_years, r_rate=0.04, sigma=r['impliedVolatility'] if r['impliedVolatility']>0 else 0.3)['Gamma'], 3), "Theta": round(engine.black_scholes_pricing(S, r['strike'], T_years, r_rate=0.04, sigma=r['impliedVolatility'] if r['impliedVolatility']>0 else 0.3)['Theta_C'], 2), "Vega": round(engine.black_scholes_pricing(S, r['strike'], T_years, r_rate=0.04, sigma=r['impliedVolatility'] if r['impliedVolatility']>0 else 0.3)['Vega'], 2)} for _, r in calls.head(15).iterrows()]
                                st.dataframe(pd.DataFrame(bs_results), use_container_width=True)
                                st.caption("✨ *注：Delta 衡量股价影响；Gamma 衡量加速度；Theta 衡量每日时间价值损耗；Vega 衡量波动率影响。*" if lang_key == "zh" else "✨ *Note: Delta measures price sensitivity; Gamma measures Delta acceleration; Theta captures daily time decay; Vega measures IV sensitivity.*")

                        with opt_tab3:
                            st.markdown("##### 🧮 交互式 Black-Scholes 期权定价器" if lang_key == "zh" else "##### 🧮 Interactive Black-Scholes Pricer")
                            
                            op_col1, op_col2, op_col3 = st.columns(3)
                            strike_pct = op_col1.slider("行权价设定 (%)" if lang_key == "zh" else "Strike % of Spot", 80, 120, 100, 1) / 100
                            custom_K = op_col2.number_input("行权价 (Strike K)" if lang_key == "zh" else "Strike Price (K)", value=float(engine.price * strike_pct), format="%.2f")
                            custom_T_years = op_col3.number_input("剩余天数 (Days)" if lang_key == "zh" else "Days to Maturity", value=30, min_value=1, max_value=730) / 365.0

                            op_col4, op_col5, op_col6 = st.columns(3)
                            custom_vol = op_col4.slider("波动率 (IV %)" if lang_key == "zh" else "Volatility (IV %)", 10.0, 150.0, 35.0, 1.0) / 100.0
                            custom_r_rate = op_col5.slider("无风险利率 (Rf %)" if lang_key == "zh" else "Risk-Free Rate (Rf %)", 1.0, 10.0, float(engine.rf * 100), 0.1) / 100.0
                            custom_div_yield = op_col6.slider("股息率 (Div %)" if lang_key == "zh" else "Div Yield (%)", 0.0, 10.0, 1.5, 0.1) / 100.0

                            custom_greeks = engine.black_scholes_pricing(engine.price, custom_K, custom_T_years, custom_r_rate, custom_vol, custom_div_yield)
                            res_c1, res_c2 = st.columns(2)
                            res_c1.metric("European Call 公道价" if lang_key == "zh" else "European Call Fair Value", f"{engine.currency} {custom_greeks['Call']:.4f}")
                            res_c2.metric("European Put 公道价" if lang_key == "zh" else "European Put Fair Value", f"{engine.currency} {custom_greeks['Put']:.4f}")

                        with opt_tab4:
                            st.markdown("### 🤖 智能期权策略顾问" if lang_key == "zh" else "### 🤖 AI Options Strategist")
                            st.caption(f"针对 **{engine.ticker}** (当前市价 ${engine.price:.2f})，推荐以下经典策略：" if lang_key == "zh" else f"Strategy playbook for **{engine.ticker}** (Spot: ${engine.price:.2f}):")

                            strategy_col1, strategy_col2 = st.columns(2)
                            with strategy_col1:
                                with st.container(border=True):
                                    st.markdown("#### 🛡️ 持股防御与收息派 (Hedging & Income)")
                                    
                                    with st.expander("1. 备兑看涨期权 (Covered Call)" if lang_key == "zh" else "1. Covered Call (Passive Income)", expanded=True):
                                        st.markdown(f"""
                                        - **操作:** 卖出 1 张虚值看涨 (Sell OTM Call)，如行权价 ${(engine.price * 1.05):.2f}。
                                        - **效果:** 立刻收租。只要不暴涨被行权，期权费白赚，有效降低持仓成本。
                                        """ if lang_key == "zh" else f"""
                                        - **Action:** Sell 1 OTM Call (e.g. Strike ${(engine.price * 1.05):.2f}).
                                        - **Result:** Collect instant premium. Generates yield while capping extreme upside.
                                        """)
                                        
                                    with st.expander("2. 保护性看跌 (Protective Put)" if lang_key == "zh" else "2. Protective Put (Crash Insurance)"):
                                        st.markdown(f"""
                                        - **操作:** 买入 1 张虚值看跌 (Buy OTM Put)，如行权价 ${(engine.price * 0.9):.2f}。
                                        - **效果:** 为正股买保险。无论跌多惨，你的最大损失都被锁死在 10% 以内。
                                        """ if lang_key == "zh" else f"""
                                        - **Action:** Buy 1 OTM Put (e.g. Strike ${(engine.price * 0.9):.2f}).
                                        - **Result:** Hard floor on your downside risk. Max loss is capped regardless of macro crashes.
                                        """)
                                        
                                    with st.expander("3. 领型期权 (Collar Strategy)" if lang_key == "zh" else "3. Collar Strategy (Zero-Cost Hedge)"):
                                        st.markdown("""
                                        - **操作:** 买入 OTM Put 防跌，同时卖出 OTM Call 赚权利金补贴保费。
                                        - **效果:** 几乎“零成本”上保险。既封死下跌空间，也封死了暴涨利润。
                                        """ if lang_key == "zh" else """
                                        - **Action:** Buy OTM Put AND Sell OTM Call.
                                        - **Result:** Near zero-cost insurance. Caps downside risk entirely but also caps your upside profit.
                                        """)

                            with strategy_col2:
                                with st.container(border=True):
                                    st.markdown("#### ⚔️ 纯投机与波动率派 (Speculation & Volatility)")
                                    
                                    with st.expander("1. 牛市看涨价差 (Bull Call Spread)" if lang_key == "zh" else "1. Bull Call Spread (Leveraged Upside)", expanded=True):
                                        st.markdown("""
                                        - **操作:** 买入 ATM Call，同时卖出 OTM Call。
                                        - **效果:** 大大降低直接买 Call 的高昂入场费。最大亏损变小，利润被封顶。
                                        """ if lang_key == "zh" else """
                                        - **Action:** Buy ATM Call & Sell higher OTM Call.
                                        - **Result:** Reduces entry cost and time decay drastically, but caps max profit.
                                        """)

                                    with st.expander("2. 铁鹰期权 (Iron Condor)" if lang_key == "zh" else "2. Iron Condor (Range Harvester)"):
                                        st.markdown("""
                                        - **操作:** 卖出 OTM Call Spread + 卖出 OTM Put Spread。
                                        - **效果:** 预测震荡市。只要股价到期乖乖待在区间内，安稳收割全盘期权费。
                                        """ if lang_key == "zh" else """
                                        - **Action:** Sell OTM Call Spread AND Sell OTM Put Spread.
                                        - **Result:** Harvester for sideways/choppy markets. Collects premium via time decay (Theta).
                                        """)

                                    with st.expander("3. 跨式组合 (Straddle)" if lang_key == "zh" else "3. Straddle (Direction-Neutral Volatility Play)"):
                                        st.markdown("""
                                        - **操作:** 同时买入相同行权价的 Call 和 Put。
                                        - **效果:** 押注财报大事件。不知方向，只要非暴涨即暴跌，利润无限。最怕横盘。
                                        """ if lang_key == "zh" else """
                                        - **Action:** Buy ATM Call AND Buy ATM Put.
                                        - **Result:** Bets purely on explosive volatility (earnings beat/miss) regardless of direction. 
                                        """)
                    else: st.warning("⚠️ No option dates found.")
                except Exception as e: st.error(f"Error fetching options: {e}")

    # [模块 12：免责声明]
    st.markdown("---")
    with st.container(border=True):
        st.markdown(f"### {T['disclaimer_title']}")
        st.markdown(T['disclaimer_1'] + "\n" + T['disclaimer_2'] + "\n" + T['disclaimer_3'])
        st.markdown("<div style='text-align: center; color: #94a3b8; font-size: 12px; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 10px;'>© 2026 Thomas. All rights reserved. | Developed for Academic & Quantitative Research.</div>", unsafe_allow_html=True)

if __name__ == '__main__':
    main()
