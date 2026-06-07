import streamlit as st
import numpy as np
import plotly.graph_objects as go
import pandas as pd
from scipy.stats import norm


# ==========================================
# 1. Page Configuration
# ==========================================
st.set_page_config(page_title="Black-Scholes Pricer", layout="wide")
st.title("Black-Scholes Pricer & Risk Sensitivities")
st.markdown("Calculate theoretical prices and risk metrics. Adjust the parameters on the left and see the immediate effects on the right.")


# ==========================================
# 2. Black-Scholes Mathematik
# ==========================================
def bs_price_and_greeks(S, K, T, r, sigma, option_type="call"):
    if T <= 0 or sigma <= 0:
        return {"Price": max(0.0, S - K) if option_type == "call" else max(0.0, K - S),
                "Delta": 0, "Gamma": 0, "Theta": 0, "Vega": 0, "Rho": 0}
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) *T)/ (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    N_d1 = norm.cdf(d1)
    N_d2 = norm.cdf(d2)
    N_minus_d1 = norm.cdf(-d1)
    N_minus_d2 = norm.cdf(-d2)
    n_d1 = norm.ppf(d1)

    gamma = n_d1 / (S * sigma * np.sqrt(T))
    vega = S * n_d1 * np.sqrt(T) / 100

    if option_type == "call":
        price = S * N_d1 - K * np.exp(-r * T) * N_d2
        delta = N_d1
        theta = (-(S * n_d1 * sigma) / (2 * np.sqrt(T)) - r * K *np.exp(-r *T) * N_d2) / 365
        rho = (K * T *np.exp(-r * T) * N_d2) / 100
    else:
        price = K * np.exp(-r * T) * N_minus_d2 - S * N_minus_d1
        delta = N_d1 - 1
        theta = (- (S * n_d1 * sigma) / (2 * np.sqrt(T)) + r * K * np.exp(-r * T) * N_minus_d2) / 365
        rho = (-K * T * np.exp(-r * T) * N_minus_d2) / 100
    return {"Price": price, "Delta": delta, "Gamma": gamma, "Theta": theta, "Vega": vega, "Rho": rho}


# ==========================================
# 3. Main UI: Inputs with Explanations (Side-by-Side)
# ==========================================
st.header("1. Options-Parameter")

# Spot Price
col_in1, col_info1 = st.columns([1, 2])
with col_in1:
    S = st.number_input("Spot Price (S)", value=100.0, step=1.0)
with col_info1:
    st.info("**Spot Price (S):** The current price of the underlying asset (e.g., the stock). If the spot price rises, call options become more expensive (since the chance that they will end up in the money increases) and put options become cheaper.")


# Strike Price
col_in2, col_info2 = st.columns([1, 2])
with col_in2:
    K = st.number_input("Strike-Preis (K)", value=100.0, step=1.0)
with col_info2:
    st.info("**Strike Price (K):** The predetermined price at which the underlying asset can be bought (call) or sold (put) on the expiration date.")

# Duration
col_in3, col_info3  = st.columns([1, 2])
with col_in3:
    T = st.slider("Term in years (T)", 0.01, 5.0, 1.0, 0.05)
with col_info3:
    st.info("**Time to Maturity (T):** The time remaining until the option expires. **1.0** corresponds to exactly one year. A longer time to maturity means a higher time value, as the option has more time to move in a favorable direction.")

# Volatility
col_in4, col_info4 = st.columns([1, 2])
with col_in4:
    sigma = st.slider("Volatility (σ)", 0.01, 1.0, 0.2, 0.01)
with col_info4:
    st.info("**Volatility (σ):** A measure of the expected range of fluctuation of the underlying asset. Higher volatility makes almost all options more expensive, as extreme price movements become more likely.")


# Interest
col_in5, col_info5 = st.columns([1, 2])
with col_in5:
    r = st.slider("Risk-free interest rate (r)", -0.05, 0.15, 0.035, 0.005)
with col_info5:
    st.info("**Risk-free rate (r):** The theoretical interest rate on a risk-free investment. Higher interest rates tend to make call options slightly more expensive and put options slightly cheaper.")

st.divider()

# ==========================================
# 4. Results & Metrics
# ==========================================
st.header("2. Resultate & Griechen")

call_data = bs_price_and_greeks(S, K, T, r, sigma, "call")
put_data = bs_price_and_greeks(S, K, T, r, sigma, "put")

col_call, col_put = st.columns(2)
with col_call:
    st.subheader("Call Option")
    st.metric("Theoretischer Preis", f"€{call_data['Price']:.2f}")
with col_put:
    st.subheader("Put Option")
    st.metric("Theoretischer Preis", f"€{put_data['Price']:.2f}")

df_greeks = pd.DataFrame({
    "Greeks": ["Delta (Δ)", "Gamma (Γ)", "Theta (Θ, pro Tag)", "Vega (ν, pro 1%)", "Rho (ρ, pro 1%)"],
    "Call": [f"{call_data['Delta']:.4f}", f"{call_data['Gamma']:.4f}", f"{call_data['Theta']:.4f}", f"{call_data['Vega']:.4f}", f"{call_data['Rho']:.4f}"],
    "Put": [f"{put_data['Delta']:.4f}", f"{put_data['Gamma']:.4f}", f"{put_data['Theta']:.4f}", f"{put_data['Vega']:.4f}", f"{put_data['Rho']:.4f}"]
})
st.table(df_greeks.set_index("Greeks"))

st.divider()


# ==========================================
# 5. Visualization (Spot vs. Sensitivity)
# ==========================================
st.header("3. Interactive Risk Profile")
spot_range = np.linspace(max(1, S - 40), S + 40, 100)

call_deltas = [bs_price_and_greeks(spot, K, T, r, sigma, "call")["Delta"] for spot in spot_range]
put_deltas = [bs_price_and_greeks(spot, K, T, r, sigma, "put")["Delta"] for spot in spot_range]
gammas = [bs_price_and_greeks(spot, K, T, r, sigma, "call")["Gamma"] for spot in spot_range]

fig1, fig2 = st.columns(2)

with fig1:
    fig_delta = go.Figure()
    fig_delta.add_trace(go.Scatter(x=spot_range, y=call_deltas, name="Call Delta", line=dict(color='#00ff00')))
    fig_delta.add_trace(go.Scatter(x=spot_range, y=put_deltas, name="Put Delta", line=dict(color='#ff0000')))
    fig_delta.add_vline(x=K, line_dash="dot", line_color="gray", annotation_text="Strike")
    fig_delta.update_layout(title="Delta vs. Spot", xaxis_title="Spot-Preis (€)", yaxis_title="Delta", template="plotly_dark", height=400)
    st.plotly_chart(fig_delta, use_container_width=True)

with fig2:
    fig_gamma = go.Figure()
    fig_gamma.add_trace(go.Scatter(x=spot_range, y=gammas, name="Gamma (Call & Put)", line=dict(color='#00ccff')))
    fig_gamma.add_vline(x=K, line_dash="dot", line_color="gray", annotation_text="Strike")
    fig_gamma.update_layout(title="Gamma vs. Spot", xaxis_title="Spot-Preis (€)", yaxis_title="Gamma", template="plotly_dark", height=400)
    st.plotly_chart(fig_gamma, use_container_width=True)

