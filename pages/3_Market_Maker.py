import streamlit as st
import numpy as np


# ==========================================
# 1. Page Configuration
# ==========================================
st.set_page_config(page_title="Market Maker Strategy", layout="wide")
st.title("Market Maker & Delta Hedging")
st.markdown("Simulate quoting (bid/ask) and hedging based on portfolio risks.")


# ==========================================
# 2. Main UI: Inputs
# ==========================================
st.header("1. Market & Inventory Data")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Option-parameter")
    fair_price = st.number_input("Fair option price (€)", value=10.0, step=0.5)
    option_delta = st.number_input("Option Delta (Δ)", value=0.5, step=0.05, min_value=-1.0, max_value=1.0)
    current_stock_hedge = st.number_input("Current equity hedge in the portfolio (units)", value=0, step=10)

with col2:
    st.subheader("Market Maker Settings")
    base_spread = st.number_input("Base Spread (€)", value=0.50, step=0.05)
    inventory = st.number_input("Current Option Inventory (units)", value=0, step=10)
    st.caption("Positive = You own options (Long). Negative = You have shorted options (Short).")
    risk_aversion = st.slider("Risk Aversion (Skew per Option)", 0.001, 0.050, 0.010, 0.001)

st.divider()

# ==========================================
# 3. Berechnungen
# ==========================================
# A. Quoting (Bid/Ask Skewing)
skew = inventory * risk_aversion
bid_price = fair_price - (base_spread / 2) - skew
ask_price = fair_price + (base_spread / 2) - skew


# Validity check (prices cannot be negative, ask > bid)
bid_price = max(0.01, bid_price)
ask_price = max(bid_price + 0.01, ask_price)

# B. Delta Hedging
portfolio_option_delta = inventory * option_delta
total_portfolio_delta = portfolio_option_delta + current_stock_hedge
required_hedge_trade = -total_portfolio_delta

# ==========================================
# Issue 4 & Instructions
# ==========================================
st.header("2. Strategy Execution")

st.info(f"**Fair Reference Price:** €{fair_price:.2f} | **Calculated Skew:** €{-skew:.2f}")

col_quote1, col_quote2 = st.columns(2)
with col_quote1:
    st.metric("Your BID (You're buying at)", f"€{bid_price:.2f}", f"{- (fair_price - bid_price):.2f} vs Fair")
    st.markdown("*If you have a large position, your bid price decreases to avoid further purchases.*")

with col_quote2:
    st.metric("Your ASK (You're selling at)", f"€{ask_price:.2f}", f"{+ (ask_price - fair_price):.2f} vs Fair", delta_color="inverse")
    st.markdown("*If you have a large position, your ask price decreases to encourage sales.*")

st.divider()

st.subheader("Risk Management (Delta Neutrality)")
st.write(f"Your current portfolio delta is **{total_portfolio_delta:.2f}**. To achieve market neutrality, you must bring this delta to 0.")

if required_hedge_trade > 0:
    st.success(f"📈 **Action:** Buy **{abs(required_hedge_trade):.2f}** shares of the underlying asset.")
elif required_hedge_trade < 0:
    st.error(f"📉 **Action:** Sell (short) **{abs(required_hedge_trade):.2f}** shares of the underlying asset.")
else:
    st.info("✅ Your portfolio is perfectly delta-neutral. No hedge required.")