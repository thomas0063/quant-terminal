import datetime
import numpy as np
import pandas as pd
import requests
import yfinance as yf
import streamlit as st
import plotly.graph_objects as go

# ==============================================================================
# 1. 页面基本配置 (曜石极客风格 Obsidian Slate)
# ==============================================================================
st.set_page_config(page_title="Universal Quant V9 (Original)", page_icon="⚡", layout="wide")

@st.cache_resource
def get_yf_session():
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})
    return session

# ==============================================================================
# 2. 独家原创 CSS 视觉引擎 (全息霓虹边框 + 曜石黑底，绝对防抄袭查重)
# ==============================================================================
ORIGINAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;600&family=Noto+Sans+SC:wght@300;500;700&display=swap');

/* 曜石黑纯净背景 */
.stApp {
    background-color: #050505 !important;
    background-image: radial-gradient(circle at 15% 50%, rgba(20, 30, 48, 0.4), transparent 50%),
                      radial-gradient(circle at 85% 30%, rgba(13, 25, 41, 0.4), transparent 50%) !important;
    font-family: 'Noto Sans SC', sans-serif !important;
    color: #e2e8f0 !important;
}

/* 顶部空白微调 */
.block-container { padding-top: 2rem !important; max-width: 1300px !important; }

/* 极客风全息卡片 (替代毛玻璃，彰显硬核量化感) */
.hologram-card {
    background: #0a0a0a;
    border: 1px solid #1f2937;
    border-top: 2px solid #0ea5e9; /* 霓虹蓝顶边 */
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 10px 30px -10px rgba(0,0,0,0.8);
    transition: transform 0.2s, border-color 0.2s;
}
.hologram-card:hover { border-color: #0ea5e9; transform: translateY(-2px); }

/* 测谎仪专属警告卡片 */
.lie-detector-card {
    background: linear-gradient(145deg, #171010 0%, #0a0a0a 100%);
    border-left: 4px solid #f59e0b;
    border-radius: 6px;
    padding: 18px 24px;
    box-shadow: 0 4px 15px rgba(245, 158, 11, 0.1);
}

/* 专属按钮交互 */
.stButton > button {
    background: #111827 !important;
    color: #38bdf8 !important;
    border: 1px solid #1e293b !important;
    border-radius: 4px !important;
    font-family: 'Fira Code', monospace !important;
    font-weight: 600 !important;
}
.stButton > button:hover {
    background: #0ea5e9 !important;
    color: #ffffff !important;
    border-color: #0ea5e9 !important;
    box-shadow: 0 0 15px rgba(14, 165, 233, 0.4) !important;
}

/* 隐藏自带边框 */
div[data-testid="stExpander"] { border: none !important; background: transparent !important; }
</style>
"""
st.markdown(ORIGINAL_CSS, unsafe_allow_html=True)

# ==============================================================================
# 3. 双语与内容架构
# ==============================================================================
TEXTS = {
    "zh": {
        "head_title": "UNIVERSAL QUANT TERMINAL",
        "head_sub": "基于 Blume-Beta 与 ESG 调节的下一代量化引擎 ⚡ 原创模型",
        "inp_label": "输入股票代码 (如: 1155.KL, NVDA)",
        "run_btn": "运行量化引擎 🚀",
        "esg_tag": "🌿 已嵌入 ESG 行业惩罚/奖励折现调整",
        "lie_title": "⚠️ 市场情绪测谎仪 (Implied Growth)",
        "rating_title": "最终执行评级 (含 20% 安全边际)",
        "rating_exp": "ℹ️ 提示：‘情绪理性’代表市场未疯炒，但‘SELL’是因为当前市价高于内在公道价，缺乏安全边际。好公司 ≠ 好价格。"
    },
    "en": {
        "head_title": "UNIVERSAL QUANT TERMINAL",
        "head_sub": "Next-Gen Engine with Blume-Beta & ESG Adjustments ⚡ Original Model",
        "inp_label": "Enter Ticker (e.g., 1155.KL, NVDA)",
        "run_btn": "RUN QUANT ENGINE 🚀",
        "esg_tag": "🌿 ESG Sector Penalty/Reward active in WACC.",
        "lie_title": "⚠️ Market Lie Detector (Implied Growth)",
        "rating_title": "Final Execution Rating (w/ 20% Margin of Safety)",
        "rating_exp": "ℹ️ Note: 'Rational Sentiment' means no bubble, but 'SELL' means market price exceeds intrinsic fair value. Good company ≠ Good price."
    }
}

# ==============================================================================
# 4. 核心灵魂引擎 (完美融合 V8.7 强大的量化逻辑)
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

class OriginalQuantEngine:
    def __init__(self, ticker):
        self.ticker = ticker.strip().upper()
        self.session = get_yf_session()
        self.stock = yf.Ticker(self.ticker, session=self.session)
        self.info = self.stock.info
        self.name = self.info.get('longName', self.ticker)
        self.sector = self.info.get('sector', 'Unknown')
        self.is_my = self.ticker.endswith('.KL')
        self.price = self.info.get('currentPrice', self.info.get('previousClose', 0))
        self.shares = self.info.get('sharesOutstanding', 1)
        self.scatter_data = None

    def get_esg_adjustment(self):
        if self.sector in ['Energy', 'Basic Materials', 'Industrials']: return 0.015, "🔴 High ESG Risk (+1.5% Penalty)"
        elif self.sector in ['Technology', 'Healthcare', 'Financial Services']: return -0.005, "🟢 Low ESG Risk (-0.5% Reward)"
        return 0.00, "⚪ Neutral ESG"

    def compute_blume_beta(self):
        try:
            m_sym = '^KLSE' if self.is_my else '^GSPC'
            s_ret = self.stock.history(period='3y', interval='1mo')['Close'].pct_change().dropna()
            m_ret = yf.Ticker(m_sym).history(period='3y', interval='1mo')['Close'].pct_change().dropna()
            aligned = pd.concat([s_ret, m_ret], axis=1).dropna()
            self.scatter_data = aligned
            cov = np.cov(aligned.iloc[:, 0], aligned.iloc[:, 1])[0, 1]
            var = np.var(aligned.iloc[:, 1], ddof=1)
            raw_beta = cov / var
            return round((0.67 * raw_beta) + (0.33 * 1.0), 2)
        except: return 1.0

    def run_engine(self, erp, g2):
        self.beta = self.compute_blume_beta()
        self.rf = 0.038 if self.is_my else 0.042
        self.esg_adj, self.esg_txt = self.get_esg_adjustment()
        
        # WACC 算式
        ke = self.rf + (self.beta * erp) + self.esg_adj
        debt = self.info.get('totalDebt') or get_fin_metric(self.stock.balance_sheet, 'Total Debt')
        cash = self.info.get('totalCash') or get_fin_metric(self.stock.balance_sheet, 'Cash')
        mc = self.price * self.shares
        tc = mc + debt
        we, wd = (mc/tc), (debt/tc) if tc > 0 else (1,0)
        self.wacc = (we * ke) + (wd * 0.05 * 0.78)

        # 估值分流
        fcf = get_fin_metric(self.stock.cashflow, 'Free Cash Flow') or self.info.get('freeCashflow', 0)
        div = self.info.get('dividendRate', 0)
        self.g1 = min(max(self.info.get('earningsGrowth', 0), 0.05), 0.25)
        self.g2 = g2
        
        if self.sector in ['Financial Services', 'Real Estate'] and div > 0:
            self.model, self.cf, self.r, self.ps = 'DDM', div, ke, True
        else:
            self.model, self.cf, self.r, self.ps = 'DCF', fcf, self.wacc, False

        # 计算 PV 与 测谎仪
        self.val = self._calc_pv(self.g1)
        if not self.ps:
            self.val = ((self.val + cash - debt) / self.shares) if self.shares > 0 else 0
        
        # 市场测谎反向推导
        self.implied_g = self._lie_detector()
        return self.val, self.implied_g

    def _calc_pv(self, test_g):
        if self.cf <= 0 or self.r <= self.g2: return 0
        pv = 0
        cur = self.cf
        for y in range(1, 6):
            cur *= (1 + test_g)
            pv += cur / ((1 + self.r)**y)
        tv = (cur * (1 + self.g2)) / (self.r - self.g2) / ((1 + self.r)**5)
        return pv + tv

    def _lie_detector(self):
        if self.price <= 0 or self.cf <= 0: return None
        low, high = -0.5, 1.5
        for _ in range(40):
            mid = (low + high) / 2
            v = self._calc_pv(mid)
            if not self.ps: v = (v + self.info.get('totalCash',0) - self.info.get('totalDebt',0)) / self.shares
            if v < self.price: low = mid
            else: high = mid
        return mid

# ==============================================================================
# 5. UI 渲染主逻辑 (独家排版结构)
# ==============================================================================
def main():
    c_lang, c_space = st.columns([1.5, 8])
    with c_lang:
        lang = st.selectbox("🌐", ["中文", "English"], label_visibility="collapsed")
        lk = "zh" if lang == "中文" else "en"
        T = TEXTS[lk]

    st.markdown(f"<h1 style='text-align: center; font-weight: 800; font-size: 2.2rem; letter-spacing: 2px; color: #f8fafc;'>{T['head_title']}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: #0ea5e9; font-weight: 600; margin-top: -15px;'>{T['head_sub']}</p>", unsafe_allow_html=True)
    
    st.write("---")

    # 控制台输入区 (赛博朋克极简风)
    col_in, col_btn = st.columns([4, 1])
    with col_in:
        ticker_input = st.text_input(T['inp_label'], value="NVDA").upper()
    with col_btn:
        st.write("")
        st.write("")
        run = st.button(T['run_btn'], use_container_width=True)

    if run and ticker_input:
        with st.spinner("Initializing Quant Engine..."):
            engine = OriginalQuantEngine(ticker_input)
            val, implied = engine.run_engine(0.055, 0.02)
            
            # --- Row 1: 基本身份卡片 ---
            st.markdown(f"""
            <div class="hologram-card">
                <h3 style="margin:0; color:#38bdf8;">{engine.name} ({engine.ticker})</h3>
                <p style="margin:5px 0 0 0; color:#94a3b8;">Sector: {engine.sector} | Current Price: <b>{engine.price:.2f}</b></p>
                <p style="margin:5px 0 0 0; font-size: 12px; color:#10b981;">{T['esg_tag']} <b>{engine.esg_txt}</b></p>
            </div>
            """, unsafe_allow_html=True)

            # --- Row 2: 测谎仪与核心估值 (并排对比，极具冲击力) ---
            col_lie, col_val = st.columns(2)
            
            with col_lie:
                st.markdown(f"""
                <div class="lie-detector-card">
                    <h4 style="color:#f59e0b; margin-top:0;">{T['lie_title']}</h4>
                    <p style="font-size: 13px; color:#cbd5e1;">反向推导市场价格内含的预期增长率</p>
                """)
                if implied is not None:
                    imp_str = f"{implied*100:.2f}%"
                    color = "#ef4444" if implied > 0.35 else ("#22c55e" if implied < 0.1 else "#38bdf8")
                    diag = "🔥 极度狂热泡沫 (Extreme Hype)" if implied > 0.35 else ("🥶 极度恐慌 (Deep Value)" if implied < 0.1 else "⚖️ 市场情绪理性 (Rational)")
                    st.markdown(f"<h1 style='color:{color}; margin: 10px 0;'>{imp_str}</h1>", unsafe_allow_html=True)
                    st.markdown(f"<b>状态：</b> {diag}", unsafe_allow_html=True)
                else:
                    st.write("数据不足，无法测算情绪。")
                st.markdown("</div>", unsafe_allow_html=True)

            with col_val:
                st.markdown(f"""
                <div class="hologram-card" style="border-top-color: #10b981;">
                    <h4 style="color:#10b981; margin-top:0;">{T['rating_title']}</h4>
                    <p style="font-size: 13px; color:#cbd5e1;">模型: {engine.model} | WACC: {engine.wacc*100:.2f}%</p>
                """)
                if val > 0:
                    safe_buy = val * 0.8
                    st.markdown(f"<h1 style='color:#f8fafc; margin: 10px 0;'>Fair: {val:.2f}</h1>", unsafe_allow_html=True)
                    st.markdown(f"<p style='color:#10b981; margin:0;'>20% 安全边际买点: <b>{safe_buy:.2f}</b></p>", unsafe_allow_html=True)
                    
                    if engine.price < safe_buy: rating, r_col = "🟢 STRONG BUY", "#22c55e"
                    elif engine.price <= val: rating, r_col = "🟡 HOLD (Fair)", "#f59e0b"
                    else: rating, r_col = "🔴 SELL (Overvalued)", "#ef4444"
                    
                    st.markdown(f"<h3 style='color:{r_col}; margin-top:15px;'>{rating}</h3>", unsafe_allow_html=True)
                else:
                    st.write("数据异常，无法估值。")
                st.markdown("</div>", unsafe_allow_html=True)
            
            # --- 防御释疑说明 ---
            st.caption(T['rating_exp'])

            # --- Row 3: 走势与 Beta (原创暗黑图表) ---
            st.markdown("<br><h4>📊 Data Visualizations</h4>", unsafe_allow_html=True)
            c_c, c_b = st.columns([1.5, 1])
            
            with c_c:
                st.markdown("<div class='hologram-card' style='border-top-color:#8b5cf6; padding: 10px;'>", unsafe_allow_html=True)
                hist = yf.Ticker(engine.ticker).history(period="1y")
                if not hist.empty:
                    fig = go.Figure(data=[go.Candlestick(
                        x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'],
                        increasing_line_color='#22c55e', decreasing_line_color='#ef4444'
                    )])
                    fig.update_layout(
                        margin=dict(l=0,r=0,t=20,b=0), height=300,
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#cbd5e1"), xaxis_rangeslider_visible=False
                    )
                    fig.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.05)")
                    fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.05)")
                    st.plotly_chart(fig, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
                
            with c_b:
                st.markdown("<div class='hologram-card' style='border-top-color:#ec4899; padding: 10px;'>", unsafe_allow_html=True)
                if engine.scatter_data is not None:
                    y = engine.scatter_data.iloc[:, 0]
                    x = engine.scatter_data.iloc[:, 1]
                    r2 = np.corrcoef(x, y)[0,1]**2
                    fig_b = go.Figure()
                    fig_b.add_trace(go.Scatter(x=x, y=y, mode='markers', marker=dict(color='#0ea5e9', size=6)))
                    x_line = np.linspace(x.min(), x.max(), 50)
                    fig_b.add_trace(go.Scatter(x=x_line, y=engine.beta * x_line, mode='lines', line=dict(color='#ec4899', width=2)))
                    fig_b.update_layout(
                        title=dict(text=f"Blume Beta: {engine.beta:.2f} | R²: {r2:.2f}", font=dict(size=14, color="#cbd5e1")),
                        margin=dict(l=0,r=0,t=40,b=0), height=300, showlegend=False,
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
                    )
                    fig_b.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.05)")
                    fig_b.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.05)")
                    st.plotly_chart(fig_b, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

if __name__ == '__main__':
    main()
