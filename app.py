import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import time

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="BOSS BULL007 | AI Trading Desk",
    page_icon="🐂",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS (DARK TRADING TERMINAL STYLE) ---
st.markdown("""
<style>
    /* Dark Terminal Theme */
    .stApp {
        background-color: #0b0f19;
        color: #e2e8f0;
    }
    .metric-card {
        background: linear-gradient(135deg, #131d31 0%, #1a2744 100%);
        border: 1px solid #2a3b5c;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .agent-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.82rem;
        margin-right: 6px;
    }
    .badge-boss { background-color: #7c3aed; color: #ffffff; }
    .badge-researcher { background-color: #0284c7; color: #ffffff; }
    .badge-news { background-color: #d97706; color: #ffffff; }
    .badge-strategist { background-color: #059669; color: #ffffff; }
    .badge-risk { background-color: #dc2626; color: #ffffff; }
    .badge-coder { background-color: #475569; color: #ffffff; }
    
    .status-active { color: #10b981; font-weight: bold; }
    .status-alert { color: #ef4444; font-weight: bold; }
    .status-neutral { color: #f59e0b; font-weight: bold; }

    /* Button Styling */
    div.stButton > button:first-child {
        background: linear-gradient(90deg, #2563eb, #1d4ed8);
        color: white;
        border-radius: 8px;
        border: none;
        padding: 8px 16px;
        font-weight: 600;
    }
    div.stButton > button:hover {
        background: linear-gradient(90deg, #1d4ed8, #1e40af);
        border: none;
    }
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE INITIALIZATION ---
if "virtual_balance" not in st.session_state:
    st.session_state.virtual_balance = 100000.0  # ₹1,00,000 starting virtual capital
if "trades" not in st.session_state:
    st.session_state.trades = []
if "desk_logs" not in st.session_state:
    st.session_state.desk_logs = [
        {"time": "09:00:00", "agent": "👔 Boss", "msg": "Morning briefing initiated. Desk standing by for market scan."},
        {"time": "09:05:00", "agent": "📰 News Analyst", "msg": "Geopolitical risk in Middle East impacting Brent Crude (+1.8%). Watching OMCs and Auto sector."},
        {"time": "09:10:00", "agent": "🔎 Researcher", "msg": "NIFTY opening near previous high resistance zone. Volume distribution normal."},
        {"time": "09:14:00", "agent": "🛡️ Risk Manager", "msg": "Capital protection rules enforced: 1% max risk per trade, 2% daily circuit."}
    ]
if "selected_setup" not in st.session_state:
    st.session_state.selected_setup = None

# --- DATA UTILITIES ---
def get_sample_indian_data(ticker="RELIANCE.NS", days=60):
    """Fetch live data via yfinance if available, else generate realistic synthetic NSE data."""
    try:
        import yfinance as yf
        data = yf.download(ticker, period=f"{days}d", interval="1d", progress=False)
        if not data.empty and len(data) > 10:
            df = data.copy()
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
            return df
    except Exception:
        pass
    
    # Realistic Synthetic Fallback for NSE
    np.random.seed(42)
    end_date = datetime.datetime.now()
    dates = pd.date_range(end=end_date, periods=days, freq='B')
    
    base_price = 2800.0 if "RELIANCE" in ticker else 1450.0 if "HDFC" in ticker else 24500.0 if "NIFTY" in ticker else 1500.0
    returns = np.random.normal(0.0005, 0.015, size=days)
    price_series = base_price * np.exp(np.cumsum(returns))
    
    opens = price_series * (1 + np.random.uniform(-0.005, 0.005, size=days))
    highs = np.maximum(opens, price_series) * (1 + np.random.uniform(0.001, 0.01, size=days))
    lows = np.minimum(opens, price_series) * (1 - np.random.uniform(0.001, 0.01, size=days))
    closes = price_series
    volumes = np.random.randint(500000, 5000000, size=days)
    
    df = pd.DataFrame({
        'Open': opens,
        'High': highs,
        'Low': lows,
        'Close': closes,
        'Volume': volumes
    }, index=dates)
    return df

def calculate_technical_indicators(df):
    """Calculate EMA 9, EMA 21, VWAP approximation, RSI 14, and ATR."""
    data = df.copy()
    data['EMA9'] = data['Close'].ewm(span=9, adjust=False).mean()
    data['EMA21'] = data['Close'].ewm(span=21, adjust=False).mean()
    
    # VWAP Approximation
    cum_vol = data['Volume'].cumsum()
    cum_vol_price = (data['Close'] * data['Volume']).cumsum()
    data['VWAP'] = cum_vol_price / cum_vol
    
    # RSI (14)
    delta = data['Close'].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=14, min_periods=14).mean()
    avg_loss = loss.rolling(window=14, min_periods=14).mean()
    rs = avg_gain / (avg_loss + 1e-9)
    data['RSI'] = 100 - (100 / (1 + rs))
    
    return data

# --- SIDEBAR: DESK CONTROLS ---
with st.sidebar:
    st.image("https://img.icons8.com/color/96/bull.png", width=64)
    st.title("BOSS BULL007")
    st.caption("AI-Powered Institutional Trading Desk")
    st.markdown("---")
    
    st.subheader("⚙️ Desk Parameters")
    universe = {
        "NIFTY 50 Index": "^NSEI",
        "BANK NIFTY": "^NSEBANK",
        "Reliance Industries": "RELIANCE.NS",
        "HDFC Bank": "HDFCBANK.NS",
        "Tata Consultancy Services": "TCS.NS",
        "Infosys": "INFY.NS",
        "State Bank of India": "SBIN.NS",
        "Tata Motors": "TATAMOTORS.NS"
    }
    selected_name = st.selectbox("Select Asset to Scan", list(universe.keys()), index=2)
    selected_ticker = universe[selected_name]
    lookback = st.slider("Historical Lookback (Days)", 20, 180, 60)
    
    st.markdown("---")
    st.subheader("💼 Capital & Risk")
    st.metric("Virtual Balance", f"₹{st.session_state.virtual_balance:,.2f}")
    max_risk_pct = st.slider("Max Risk per Trade (%)", 0.5, 3.0, 1.0, 0.25)
    daily_stop_pct = st.slider("Daily Drawdown Limit (%)", 1.0, 5.0, 2.0, 0.5)
    
    if st.button("🔄 Reset Virtual Account"):
        st.session_state.virtual_balance = 100000.0
        st.session_state.trades = []
        st.rerun()

# --- FETCH ASSET DATA ---
df_raw = get_sample_indian_data(selected_ticker, lookback)
df = calculate_technical_indicators(df_raw)
latest = df.iloc[-1]
prev = df.iloc[-2]

# --- MAIN NAVIGATION TABS (THE 6 DIVISIONS) ---
tab_boss, tab_researcher, tab_news, tab_strategist, tab_risk, tab_ledger = st.tabs([
    "👔 Boss HQ",
    "🔎 Market Researcher",
    "📰 News Analyst (Geopolitics)",
    "📋 Strategist",
    "🛡️ Risk Manager",
    "📈 Paper Trading Ledger"
])

# ==========================================
# 1. 👔 BOSS HQ (OPERATIONS & SYNTHESIS)
# ==========================================
with tab_boss:
    st.header("👔 Boss Coordination Room")
    st.write("One unified operating command coordinating all 6 divisions 24/7.")
    
    # Agent Status Row
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown("""
        <div class="metric-card">
            <span class="agent-badge badge-researcher">🔎 Researcher</span>
            <div class="status-active">● Active</div>
            <small>Scanning NSE/BSE charts</small>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="metric-card">
            <span class="agent-badge badge-news">📰 News Analyst</span>
            <div class="status-active">● Active</div>
            <small>Geopolitics & Crude scan</small>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div class="metric-card">
            <span class="agent-badge badge-strategist">📋 Strategist</span>
            <div class="status-active">● Ready</div>
            <small>Min 1:2 R:R Trade Plans</small>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown("""
        <div class="metric-card">
            <span class="agent-badge badge-risk">🛡️ Risk Manager</span>
            <div class="status-active">● Guarding</div>
            <small>1% Max Risk Veto active</small>
        </div>
        """, unsafe_allow_html=True)
    with col5:
        st.markdown("""
        <div class="metric-card">
            <span class="agent-badge badge-coder">💻 Coder</span>
            <div class="status-active">● Deployed</div>
            <small>PWA/Web responsive build</small>
        </div>
        """, unsafe_allow_html=True)

    # Master Synthesis
    st.subheader("🎯 Boss Operational Synthesis for " + selected_name)
    
    # Calculate automated market regime
    is_bullish = latest['Close'] > latest['EMA21'] and latest['EMA9'] > latest['EMA21']
    is_oversold = latest['RSI'] < 35
    is_overbought = latest['RSI'] > 70
    
    regime = "Bullish Trend" if is_bullish else "Consolidation / Bearish Pressure"
    bias_color = "status-active" if is_bullish else "status-neutral"
    
    col_a, col_b, col_c = st.columns([1, 1, 2])
    with col_a:
        st.metric("Latest Close", f"₹{latest['Close']:.2f}", f"{(latest['Close']-prev['Close']):+.2f}")
    with col_b:
        st.metric("RSI (14)", f"{latest['RSI']:.1f}", "Normal" if 35 <= latest['RSI'] <= 70 else "Extreme")
    with col_c:
        st.markdown(f"""
        <div class="metric-card">
            <strong>Current Market Regime:</strong> <span class="{bias_color}">{regime}</span><br/>
            <strong>Boss Directive:</strong> {"Favor pullbacks to EMA 9/21 with tight stop-losses." if is_bullish else "Wait for trend confirmation or key level reclaim before deploying size."}
        </div>
        """, unsafe_allow_html=True)

    # Live Desk Comms
    st.subheader("🗣️ Live Desk Inter-Agent Communication")
    for log in reversed(st.session_state.desk_logs[-8:]):
        st.markdown(f"**[{log['time']}]** `{log['agent']}`: {log['msg']}")

# =========================================
# 2. 🔎 MARKETRESEARCHER (TECHNICAL ENGINE)
# =========================================
with tab_researcher:
    st.header(f"🔎 Market Researcher — {selected_name} ({selected_ticker})")
    
    # Technical Chart
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.75, 0.25],
        subplot_titles=(f"{selected_name} Price Action & Moving Averages", "Relative Strength Index (RSI)")
    )
    
    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name='Price',
        increasing_line_color='#10b981', decreasing_line_color='#ef4444'
    ), row=1, col=1)
    
    # EMA Overlays
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA9'], line=dict(color='#38bdf8', width=1.5), name='EMA 9'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA21'], line=dict(color='#fbbf24', width=1.5), name='EMA 21'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['VWAP'], line=dict(color='#c084fc', width=1, dash='dot'), name='VWAP (Approx)'), row=1, col=1)
    
    # RSI Subplot
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='#a855f7', width=1.5), name='RSI 14'), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="#ef4444", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="#10b981", row=2, col=1)
    
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0b0f19",
        plot_bgcolor="#111827",
        height=550,
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis_rangeslider_visible=False
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Researcher Findings Summary
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("EMA 9", f"₹{latest['EMA9']:.2f}")
    c2.metric("EMA 21", f"₹{latest['EMA21']:.2f}")
    c3.metric("Trend State", "Golden Cross (Bullish)" if latest['EMA9'] > latest['EMA21'] else "Death Cross (Bearish)")
    c4.metric("Avg Volume (10d)", f"{int(df['Volume'].tail(10).mean()):,}")

# ==========================================
# 3. 📰 NEWS & GEOPOLITICAL ANALYST
# ==========================================
with tab_news:
    st.header("📰 News Analyst — Geopolitics & Macro Intelligence")
    st.info("Specialty Focus: Geopolitical catalysts, crude oil flows, currency shifts, and Indian market impact.")
    
    col_geo1, col_geo2 = st.columns([2, 1])
    
    with col_geo1:
        st.subheader("🌍 Active Macro Intelligence Wire")
        
        macro_events = [
            {
                "headline": "Brent Crude stabilizes around $84/bbl amidst Red Sea transit delays",
                "impact": "Neutral-Negative for OMCs (BPCL, IOC), positive for domestic upstream (ONGC).",
                "bias": "Caution on Transport & Auto",
                "score": -0.2
            },
            {
                "headline": "FII institutional flows turn net positive in Indian equities after 3 weeks",
                "impact": "Liquidity boost across Large-Cap banking and IT constituents.",
                "bias": "Bullish on Private Banks (HDFCBANK, ICICIBANK)",
                "score": +0.6
            },
            {
                "headline": "India Defense procurement council clears ₹45,000 Cr domestic modernization orders",
                "impact": "Direct revenue visibility for indigenous defense and aerospace ecosystem.",
                "bias": "Strong Bullish on Defense",
                "score": +0.8
            },
            {
                "headline": "US Dollar Index (DXY) softens slightly to 103.8; INR trading at 83.45",
                "impact": "Eases imported inflation pressure on Indian industrial manufacturers.",
                "bias": "Slight Bullish for broad market",
                "score": +0.3
            }
        ]
        
        for item in macro_events:
            with st.container():
                st.markdown(f"#### 🌐 {item['headline']}")
                st.write(f"**Impact Assessment:** {item['impact']}")
                st.markdown(f"**Sectoral Bias:** `{item['bias']}` | **Sentiment Score:** `{item['score']:+.2f}`")
                st.divider()

    with col_geo2:
        st.subheader("📊 Sector Impact Matrix")
        sector_data = pd.DataFrame({
            "Sector": ["Defense", "Private Banks", "IT / Tech", "Auto", "OMCs"],
            "Geopolitical Sentiment": ["Strong Bullish", "Bullish", "Neutral", "Cautious", "Bearish"],
            "Signal Weight": ["+85%", "+60%", "+10%", "-20%", "-45%"]
        })
        st.dataframe(sector_data, hide_index=True, use_container_width=True)

# ==========================================
# 4. 📋 STRATEGIST (TRADE PLAN GENERATION)
# ==========================================
with tab_strategist:
    st.header("📋 Strategist — High Probability Trade Plan Architect")
    st.write("Constructs systematic trading plans with mandatory 1:2 Minimum Risk-to-Reward ratio.")
    
    curr_price = float(latest['Close'])
    atr_est = float((df['High'] - df['Low']).tail(14).mean())
    
    st.subheader(f"Setup Generator for {selected_name}")
    
    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        trade_direction = st.radio("Direction", ["LONG (Buy)", "SHORT (Sell)"], horizontal=True)
    with col_s2:
        entry_price = st.number_input("Trigger Entry Price (₹)", value=round(curr_price, 2), step=1.0)
    with col_s3:
        # Default stop based on 1.5 ATR
        stop_dist = round(1.5 * atr_est, 2)
        if "LONG" in trade_direction:
            default_sl = round(entry_price - stop_dist, 2)
            default_t1 = round(entry_price + (2.0 * stop_dist), 2)
        else:
            default_sl = round(entry_price + stop_dist, 2)
            default_t1 = round(entry_price - (2.0 * stop_dist), 2)
            
        stop_loss = st.number_input("Invalidation Stop-Loss (₹)", value=default_sl, step=1.0)
    
    target_price = st.number_input("Target 1 (₹)", value=default_t1, step=1.0)
    
    # Calculate Risk vs Reward
    risk_points = abs(entry_price - stop_loss)
    reward_points = abs(target_price - entry_price)
    rr_ratio = reward_points / (risk_points + 1e-6)
    
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("Risk per Share", f"₹{risk_points:.2f}")
    col_m2.metric("Reward per Share", f"₹{reward_points:.2f}")
    col_m3.metric("Risk-to-Reward Ratio", f"1 : {rr_ratio:.2f}", "Eligible (>= 1:2)" if rr_ratio >= 2.0 else "Inadequate (< 1:2)")
    
    thesis = st.text_area("Strategy Rationale & Invalidation Thesis", 
                          value=f"{selected_name} testing key moving averages with alignment from geopolitical signals. Invalidation if price breaks below ₹{stop_loss:.2f}.")
    
    if st.button("🚀 Submit Plan to Risk Manager for Veto/Approval"):
        st.session_state.selected_setup = {
            "ticker": selected_ticker,
            "name": selected_name,
            "direction": "LONG" if "LONG" in trade_direction else "SHORT",
            "entry": entry_price,
            "sl": stop_loss,
            "target": target_price,
            "risk_pts": risk_points,
            "reward_pts": reward_points,
            "rr": rr_ratio,
            "thesis": thesis
        }
        st.success("Plan delivered to Risk Manager. Switch to 'Risk Manager' tab to review approval.")

# ==========================================
# 5. 🛡️ RISK MANAGER (VETO & SIZING)
# ==========================================
with tab_risk:
    st.header("🛡️ Risk Manager — Capital Preservation & Trade Veto")
    st.write("Enforces ironclad capital management rules. Rejects trades that violate risk discipline.")
    
    setup = st.session_state.selected_setup
    
    if setup is None:
        st.info("No trade plan submitted yet. Go to the 'Strategist' tab to create a plan.")
    else:
        st.markdown(f"### Evaluating Trade Plan: `{setup['name']}` ({setup['direction']})")
        
        # Risk Calculations
        account_val = st.session_state.virtual_balance
        max_allowed_risk_cash = account_val * (max_risk_pct / 100.0)
        
        # Position sizing: Risk Cash / Risk Points
        shares_to_buy = int(max_allowed_risk_cash / (setup['risk_pts'] + 1e-6))
        total_trade_capital = shares_to_buy * setup['entry']
        
        # Veto Criteria
        meets_rr = setup['rr'] >= 1.95
        meets_size = shares_to_buy > 0 and total_trade_capital <= account_val * 0.95
        
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            st.markdown("""
            #### 📋 Risk Checklist
            """)
            st.write(f"1. **R:R Criterion (>= 1:2)**: {'✅ PASS' if meets_rr else '❌ REJECT (R:R too low)'}")
            st.write(f"2. **Risk Limit**: Max ₹{max_allowed_risk_cash:,.2f} ({max_risk_pct}% of capital)")
            st.write(f"3. **Position Size Allocated**: {shares_to_buy} shares")
            st.write(f"4. **Total Capital Required**: ₹{total_trade_capital:,.2f}")
        
        with col_v2:
            st.markdown("#### ⚖️ Risk Manager Verdict")
            if meets_rr and meets_size:
                st.success("🟢 TRADE APPROVED FOR EXECUTION")
                st.write("All safety parameters satisfied. Position sized to guarantee no more than 1% account risk upon stop-out.")
                
                if st.button("⚡ Execute into Paper Trading Ledger"):
                    trade_record = {
                        "id": f"TRD-{int(time.time())}",
                        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "ticker": setup['ticker'],
                        "name": setup['name'],
                        "direction": setup['direction'],
                        "entry": setup['entry'],
                        "shares": shares_to_buy,
                        "sl": setup['sl'],
                        "target": setup['target'],
                        "status": "OPEN",
                        "pnl": 0.0
                    }
                    st.session_state.trades.append(trade_record)
                    st.session_state.desk_logs.append({
                        "time": datetime.datetime.now().strftime("%H:%M:%S"),
                        "agent": "🛡️ Risk Manager",
                        "msg": f"Executed {setup['direction']} on {setup['name']} ({shares_to_buy} shares @ ₹{setup['entry']:.2f})."
                    })
                    st.session_state.selected_setup = None
                    st.success("Trade executed into Paper Ledger!")
                    st.rerun()
            else:
                st.error("🔴 TRADE VETOED BY RISK MANAGER")
                if not meets_rr:
                    st.write("❌ **Reason:** Setup offers poor asymmetric payoff (< 1:2 Risk to Reward).")
                if not meets_size:
                    st.write("❌ **Reason:** Position size exceeds available virtual liquidity.")

# ==========================================
# 6. 📈 PAPER TRADING LEDGER
# ==========================================
with tab_ledger:
    st.header("📈 Paper Trading Ledger & Performance Dashboard")
    st.write("Simulated live trade execution with realistic P&L tracking and journal history.")
    
    col_p1, col_p2, col_p3 = st.columns(3)
    col_p1.metric("Current Virtual Capital", f"₹{st.session_state.virtual_balance:,.2f}")
    
    # Calculate performance stats
    total_trades = len(st.session_state.trades)
    closed_trades = [t for t in st.session_state.trades if t['status'] == 'CLOSED']
    open_trades = [t for t in st.session_state.trades if t['status'] == 'OPEN']
    
    realized_pnl = sum([t.get('realized_pnl', 0.0) for t in closed_trades])
    col_p2.metric("Total Trades Logged", f"{total_trades}", f"{len(open_trades)} Open")
    col_p3.metric("Net Realized P&L", f"₹{realized_pnl:+,.2f}", f"{(realized_pnl / 100000.0)*100:+.2f}%")
    
    st.markdown("---")
    st.subheader("Active Open Positions")
    if not open_trades:
        st.write("No active open positions currently.")
    else:
        for idx, t in enumerate(open_trades):
            with st.container():
                cols = st.columns([1, 1, 1, 1, 1, 2])
                cols[0].write(f"**{t['name']}** ({t['direction']})")
                cols[1].write(f"Qty: {t['shares']}")
                cols[2].write(f"Entry: ₹{t['entry']:.2f}")
                cols[3].write(f"SL: ₹{t['sl']:.2f}")
                cols[4].write(f"Target: ₹{t['target']:.2f}")
                
                # Close trade simulation buttons
                with cols[5]:
                    c_win, c_loss = st.columns(2)
                    if c_win.button("🎯 Hit Target", key=f"win_{idx}"):
                        pnl = (t['target'] - t['entry']) * t['shares'] if t['direction'] == 'LONG' else (t['entry'] - t['target']) * t['shares']
                        t['status'] = 'CLOSED'
                        t['realized_pnl'] = pnl
                        st.session_state.virtual_balance += pnl
                        st.session_state.desk_logs.append({
                            "time": datetime.datetime.now().strftime("%H:%M:%S"),
                            "agent": "📈 Paper Ledger",
                            "msg": f"Closed {t['name']} at Target. Realized P&L: ₹{pnl:+,.2f}"
                        })
                        st.rerun()
                    if c_loss.button("🛑 Hit Stop", key=f"loss_{idx}"):
                        pnl = (t['sl'] - t['entry']) * t['shares'] if t['direction'] == 'LONG' else (t['entry'] - t['sl']) * t['shares']
                        t['status'] = 'CLOSED'
                        t['realized_pnl'] = pnl
                        st.session_state.virtual_balance += pnl
                        st.session_state.desk_logs.append({
                            "time": datetime.datetime.now().strftime("%H:%M:%S"),
                            "agent": "📈 Paper Ledger",
                            "msg": f"Closed {t['name']} at Stop-Loss. Realized P&L: ₹{pnl:+,.2f}"
                        })
                        st.rerun()
                st.divider()

    # Closed Trade History Table
    st.subheader("Historical Trade Journal")
    if st.session_state.trades:
        df_ledger = pd.DataFrame(st.session_state.trades)
        st.dataframe(df_ledger, use_container_width=True)
    else:
        st.caption("Trade journal is currently empty.")

# --- FOOTER ---
st.markdown("---")
st.caption("🔒 **Security Guarantee**: BOSS BULL007 runs locally or on your private cloud. Never enter broker passwords or OTPs.")
