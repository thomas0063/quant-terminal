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
st.set_page_config(page_title="Universal Quant Terminal V8.9 Plus", page_icon="💹", layout="wide", initial_sidebar_state="collapsed")

# ==============================================================================
# 2. 独家高级 CSS 视觉引擎 (Bento Box 等高对齐 + 冰蓝框架感 + 清爽深蓝背景)
# ==============================================================================
PREMIUM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

/* 全局背景：清爽的深石墨蓝渐变，告别压抑死黑 */
.stApp {
    background: radial-gradient(circle at 50% 0%, #1e293b 0%, #0f172a 60%, #090d16 100%) !important;
    font-family: 'Inter', -apple-system, sans-serif !important;
    color: #f8fafc !important;
}
.block-container { padding-top: 2rem !important; max-width: 1280px !important; }

header[data-testid="stHeader"] { background: transparent !important; }

/* 🌟 核心：强制所有列内元素等高，并加上精致、清晰的冰蓝色边框与深蓝实底 */
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
# 3. 国际化多语言字典 (已完全双语化适配)
# ==============================================================================
TEXTS = {
    "zh": {
        "title": "🌐 智能量化金融终端 (旗舰全功能版)",
        "subtitle": "完美融合 线性衰减DCF、三模型矩阵、CAPM、WACC、市场情绪测谎仪与双视角 AI 顾问",
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
        
        "lie_title": "[3. 💡 市场情绪测谎仪 (MARKET PSYCHOLOGY / LIE DETECTOR)]",
        "lie_exp": "💡 **通俗解释 (Plain English)：** 测谎仪通过二分法反向推导，看看当前的市场价格到底在幻想这家公司未来每年增长多少。",
        "ai_title": "[4. 🤖 双视角 AI 投资顾问 (DUAL-PERSPECTIVE AI ADVISORY)]",
        "inc_title": "🔸 视角 A：保守派收息策略 (Conservative Income)",
        "cap_title": "🔹 视角 B：进取派资本增值 (Capital Appreciation)",
        "exec_title": "[5. 🎯 最终投资评级与执行摘要 (EXECUTIVE SUMMARY)]",
        "rating_explain": "ℹ️ *学术释疑：‘市场情绪理性’代表投资者没有盲目炒作泡沫，但给出 ‘SELL’ 评级是因为当前市价高于内在公道价（缺乏安全边际）。即：好公司不等于好价格。*",
        
        "plain_title": "[6. 🗣️ 小白通俗翻译器 (PLAIN ENGLISH TRANSLATOR)]",
        "fx_title": "[7. 💱 跨境汇率风险提示 (CROSS-BORDER FX RISK)]",
        "fx_content": "- **提示：** 此乃美元计价资产，请注意美元兑马币 (USD/MYR) 的汇率波动风险。",
        
        "ws_title": "🏛️ 华尔街专业投行分析师共识与预期差雷达 (Wall Street & Expectation Gap)",
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

        "chart_title": "[8. 📈 高级盘面与波动率回归分析]",
        "beta_desc": "📊 **Beta 收益率特征线散点分布图说明：**\n* 每个点代表过往某一周的收益率联动。红线斜率即为真实 Beta（马股对标 MSCI Malaysia ETF，美股对标 S&P 500）。\n* **$R^2$（拟合优度）补充解析**：点越密集贴近红线，说明该股越受大盘宏观主导（如银行股）；点越分散，说明该股具有极强的个股独立行情（如科技股）。",
        "glossary_title": "[9. 📖 小白通俗金融词典：这些数据代表什么？]",
        
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
        "subtitle": "Integrating Fading Growth DCF, Multi-Model Matrix, CAPM, WACC, Lie Detector & AI Advisory",
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
        
        "lie_title": "[3. 💡 MARKET PSYCHOLOGY (LIE DETECTOR)]",
        "lie_exp": "💡 **Plain English Explanation:** The lie detector uses reverse-engineering to find out what growth rate investors are currently pricing into the stock.",
        "ai_title": "[4. 🤖 DUAL-PERSPECTIVE AI ADVISORY]",
        "inc_title": "🔸 Perspective A: Conservative Income",
        "cap_title": "🔹 Perspective B: Capital Appreciation",
        "exec_title": "[5. 🎯 FINAL EXECUTIVE SUMMARY & RATING]",
        "rating_explain": "ℹ️ *Academic Note: 'Rational Market Sentiment' means investors are not irrationally hyping the stock, but a 'SELL' rating is triggered strictly because the market price exceeds the intrinsic value (Lack of Margin of Safety). Good company ≠ Good price.*",
        
        "plain_title": "[6. 🗣️ PLAIN ENGLISH TRANSLATOR]",
        "fx_title": "[7. 💱 CROSS-BORDER FX RISK ADVISORY]",
        "fx_content": "- **Note:** USD-denominated asset; monitor USD/MYR exchange rate fluctuations.",
        
        "ws_title": "🏛️ Wall Street Analyst Consensus & Expectation Gap Radar",
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

        "chart_title": "[8. Advanced Price Action & Regression Analysis]",
        "beta_desc": "📊 **Beta Scatter Plot Explanation:** Each dot represents past weekly return correlation. The red line slope represents the true Beta (Bursa benchmarks against MSCI Malaysia ETF, US equities against S&P 500).\n* **$R^2$ Analysis**: Tight clustering indicates market-driven systemic risk; higher dispersion reflects strong independent trends.",
        "glossary_title": "[9. Beginner's Financial Glossary]",
        
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
# 4. 防崩溃财报提取函数
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
# 5. 核心量化引擎 (集成线性衰减增长模型 + WACC + Blume Beta + ESG + 三模型矩阵)
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

        # 1. 计算 DCF 模型值
        self.val_dcf = self.calculate_dcf_pv(self.g1)

        # 2. 计算 DDM 模型值
        div = self.info.get('dividendRate') or self.info.get('trailingAnnualDividendRate') or 0.0
        self.val_ddm = None
        if div > 0:
            g_ddm = min(self.g2, self.ke - 0.01)
            self.val_ddm = (div * (1.0 + g_ddm)) / (self.ke - g_ddm) if self.ke > g_ddm else 0.0

        # 3. 计算 P/E 倍数模型值
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

        # 选择主推荐模型值（V8.9 核心逻辑：金融/公用事业用 DDM，其余用 DCF/PE）
        if self.sector in ['Financial Services', 'Real Estate', 'Utilities'] and self.val_ddm is not None and self.val_ddm > 0:
            self.model_name = 'Dividend Discount Model (DDM)'
            self.r = self.ke
            val = self.val_ddm
        elif self.val_dcf is not None and self.val_dcf > 0:
            self.model_name = 'Discounted Cash Flow (DCF)'
            self.r = self.wacc
            val = self.val_dcf
        elif self.val_pe is not None and self.val_pe > 0:
            self.model_name = 'P/E Multiples Valuation'
            self.r = self.wacc
            val = self.val_pe
        else:
            self.model_name = 'Discounted Cash Flow (DCF)'
            self.r = self.wacc
            val = self.val_dcf if self.val_dcf else 0.0

        return val, self.find_implied_growth()

    def calculate_dcf_pv(self, test_g):
        if self.cf <= 0 or self.wacc <= self.g2: return None
        pv1 = 0
        curr_cf = self.cf
        
        # 💡 机构级核心修复：采用线性衰减增长率 (Linear Fading Growth)
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
# 6. 图表生成函数
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
# 7. 主程序与双语 UI 渲染
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
        with st.spinner("Analyzing quantitative model..."):
            engine = UniversalQuantEngine(ticker_input)
            val, implied_g = engine.run_valuation(custom_erp, custom_g2)

            st.markdown(f"<h3 style='margin-top: 25px;'>🏢 {engine.name} ({engine.ticker}) <span style='font-size:14px; color:#94a3b8;'>| Sector: {engine.sector}</span></h3>", unsafe_allow_html=True)

            # [模块 1：动态宏观与资本成本]
            with st.container(border=True):
                st.markdown(f"**{T['macro_title']}**")
                c1, c2, c3 = st.columns(3)
                c1.metric("Beta Risk", f"{engine.beta:.2f}", delta=engine.beta_type, delta_color="off")
                c2.metric("Rf Rate", f"{engine.rf * 100:.2f}%")
                c3.metric("WACC", f"{engine.r * 100:.2f}%", engine.esg_tag)
                st.caption(T['macro_exp'])

            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

            # [模块 2：三大经典估值模型横向对比矩阵]
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
            
            # 💡 醒目的通俗小解释：已完全双语化绑定
            st.info(T['fair_val_desc'])

            if val > 0 and engine.price > 0:
                price_to_val = engine.price / val

                # [模块 3：市场情绪测谎仪] & [模块 4：双视角 AI 投资顾问]
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
                            st.success("-> **Verdict:** 🟢 SUITABLE FOR INCOME.")
                        else:
                            st.error("-> **Verdict:** 🔴 NOT IDEAL FOR INCOME.")
                        
                        st.markdown(T['cap_title'])
                        st.write(f"- Implied Growth: {implied_g_str} | Model Valuation: {val:.2f}")
                        if implied_g is not None and implied_g < 0.0 and engine.price < val:
                            st.success("-> **Verdict:** 🟢 MULTI-BAGGER POTENTIAL.")
                        elif implied_g is not None and implied_g > 0.40:
                            st.error("-> **Verdict:** 🔴 HIGH SPECULATION RISK.")
                        else:
                            st.info("-> **Verdict:** 🟢 / 🟡 FAIRLY PRICED.")

                # [模块 5：最终投资评级与执行摘要]
                st.markdown(f"### {T['exec_title']}")
                if price_to_val <= 0.70 and (implied_g is not None and implied_g < 0.0):
                    rating, reason = '🟢 STRONG BUY', f'Extreme pessimism creates massive margin of safety. Price ({engine.price:.2f}) heavily discounted vs intrinsic value ({val:.2f}).'
                elif price_to_val <= 0.85:
                    rating, reason = '🟢 BUY', f'Solid value mispricing. Price ({engine.price:.2f}) meets 20% margin of safety.'
                elif 0.85 < price_to_val <= 1.15:
                    rating, reason = '🟡 HOLD', f'Fairly valued. Price ({engine.price:.2f}) aligns with intrinsic value ({val:.2f}).'
                elif 1.15 < price_to_val <= 1.40:
                    rating, reason = '🔴 SELL', f'Overvalued. Price ({engine.price:.2f}) exceeds intrinsic value ({val:.2f}).'
                else:
                    rating, reason = '🔴 STRONG SELL', f'Severe bubble risk. Implied growth is priced for perfection.'

                with st.container(border=True):
                    st.markdown(f"- **Final Investment Rating : {rating}**")
                    st.markdown(f"- **Core Justification : {reason}**")
                    st.markdown("")
                    st.caption(T['rating_explain'])

                # [模块 6：小白通俗翻译器] & [模块 7：跨境汇率风险提示]
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    with st.container(border=True):
                        st.markdown(f"**{T['plain_title']}**")
                        st.markdown(f"- **Required Hurdle Rate / Discount Rate:** {engine.r * 100:.2f}%")
                        st.markdown("  👉 Minimum required return.")
                        if implied_g is not None:
                            st.markdown(f"- **Market Sentiment / Implied Growth:** {implied_g * 100:.2f}%")
                            if implied_g > 0.35: st.markdown("  👉 **【⚠️ SEVERE BUBBLE WARNING】**")
                            elif implied_g < 0.0: st.markdown("  👉 **【🔥 EXTREME PESSIMISM / DEEP VALUE】**")
                            else: st.markdown("  👉 **【⚖️ BALANCED & RATIONAL】**")
                
                with col_t2:
                    with st.container(border=True):
                        if not engine.is_malaysia:
                            st.markdown(f"**{T['fx_title']}**")
                            st.warning(T['fx_content'])
                        else:
                            st.markdown(f"**{T['fx_title']}**")
                            st.warning("- 🇲🇾 本地资产计价 (MYR)，无直接跨境外汇风险暴露。")

                # [模块 8：华尔街共识 + 预期差雷达]
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

                # [模块 8：盘面与波动率回归分析]
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

                # [模块 9：小白金融词典]
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

    # [模块 10：免责声明]
    st.markdown("---")
    with st.container(border=True):
        st.markdown(f"### {T['disclaimer_title']}")
        st.markdown(T['disclaimer_1'])
        st.markdown(T['disclaimer_2'])
        st.markdown(T['disclaimer_3'])

if __name__ == '__main__':
    main()
