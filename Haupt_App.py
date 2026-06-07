import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import yfinance as yf

# ==========================================
# 1. Page Configuration (Muss ganz oben stehen)
# ==========================================
st.set_page_config(
    page_title="Quant Terminal | Home",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 2. Header & Begrüßung
# ==========================================
st.title("📈 Quant & Risk Management Terminal")
st.markdown(
    "Willkommen in deinem persönlichen Hub für quantitative Finanzanalysen, Optionsbewertung und Market Making.")
st.divider()


# ==========================================
# 3. Live Market Data Connection
# ==========================================
st.header("Live Market Data & Risk Analysis")

# Input field for the ticker (default: S&P 500 ETF)
ticker_symbol = st.text_input("Gib ein Ticker-Symbol ein (z.B. AAPL, TSLA, SPY, ^GDAXI):", value="SPY")

with st.spinner(f'load marktdata {ticker_symbol}...'):
    # load data for the last 6 month
    ticker_data = yf.Ticker(ticker_symbol)
    df = ticker_data.history(period="6mo")

    if df.empty:
        st.error("Error: Ticker not found or no data available. Please check the symbol.")
    else:
        # --- Calculations using REAL data ---
        df['Daily_Return'] = df['Close'].pct_change()

        current_price = df['Close'].iloc[-1]
        previous_price = df['Close'].iloc[-2]
        initial_price = df['Close'].iloc[0]

        daily_pnl_abs = current_price - previous_price
        daily_pnl_pct = (current_price / previous_price) - 1
        total_return_pct = (current_price / initial_price) - 1

        # Historical Value at Risk (99%, 1 day) based on actual returns
        # We use the 1st percentile of actual daily returns
        var_99_pct = np.percentile(df['Daily_Return'].dropna(), 1)
        var_99_abs = current_price * var_99_pct

        # --- KPIs (Top Row) ---
        col1, col2, col3, col4 = st.columns(4)
        col1.metric(f"Aktueller Kurs ({ticker_symbol})", f"${current_price:.2f}",f"{total_return_pct * 100:.2f}% (6 Monate)")
        col2.metric("Tagesveränderung", f"${daily_pnl_abs:.2f}", f"{daily_pnl_pct * 100:.2f}%")
        col3.metric("Historische Volatilität (p.a.)", f"{df['Daily_Return'].std() * np.sqrt(252) * 100:.2f}%")
        col4.metric("Value at Risk (99%, 1d)", f"${var_99_abs:.2f}", delta_color="inverse")


        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['Close'],
            mode='lines',
            name=f'{ticker_symbol} Close Price',
            line=dict(color='#00ccff', width=2),
            fill='tozeroy',
            fillcolor='rgba(0, 204, 255, 0.1)'
        ))

        fig.update_layout(
            xaxis_title="Datum",
            yaxis_title="Kurs in USD ($)",
            template="plotly_dark",
            height=350,
            margin=dict(l=0, r=0, t=30, b=0),
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# ==========================================
# 4. Modul-Navigation (Info-Kacheln)
# ==========================================
st.subheader("Verfügbare Module")
st.markdown(
    "Nutze die Seitenleiste links, um in die detaillierten Analyse-Tools zu navigieren, oder informiere dich hier über die Funktionen.")

c1, c2, c3 = st.columns(3)

with c1:
    st.info("""
    **🎲 Monte Carlo Simulation**

    Simuliere Portfolio-Risiken und zukünftige Preis-Pfade für korrelierte Assets unter Nutzung der QuantLib-Engine. Berechne Expected Returns und VaR.
    """)

with c2:
    st.info("""
    **📊 Black-Scholes Pricer**

    Analysiere theoretische Optionspreise für europäische Calls und Puts. Visualisiere interaktiv die Auswirkungen der Griechen (Delta, Gamma, Theta, Vega, Rho).
    """)

with c3:
    st.info("""
    **⚖️ Market Maker Strategie**

    Berechne optimale Bid-Ask-Spreads basierend auf deinem Inventory-Risk (Skewing) und verwalte dein Delta-Hedging, um marktneutral zu bleiben.
    """)