import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

# ==========================================
# 1. Page Configuration
# ==========================================
st.set_page_config(page_title="Portfolio Optimierung", layout="wide")
st.title("Markowitz Portfolio Optimierung (Efficient Frontier)")
st.markdown("Simuliere Tausende von Gewichtungen, um das optimale Risiko-Rendite-Profil zu finden.")

# ==========================================
# 2. Daten-Simulation (Mockup für historische Daten)
# ==========================================
# Wir simulieren korrelierte Jahresrenditen für 4 Assets
assets = ["Tech (Growth)", "Energie (Value)", "Gesundheit (Defensiv)", "Anleihen (Safe)"]
num_assets = len(assets)

# Erwartete jährliche Renditen
expected_returns = np.array([0.12, 0.08, 0.06, 0.03])

# Kovarianz-Matrix (Volatilität auf der Diagonale, Korrelationen abseits)
# Tech ist sehr volatil, Anleihen kaum. Tech und Energie korrelieren wenig.
cov_matrix = np.array([
	[0.0400, 0.0050, 0.0100, -0.0020],
	[0.0050, 0.0250, 0.0080, -0.0010],
	[0.0100, 0.0080, 0.0150, 0.0010],
	[-0.0020, -0.0010, 0.0010, 0.0020]
])

# ==========================================
# 3. Sidebar: Simulations-Parameter
# ==========================================
st.sidebar.header("Optimierungs-Parameter")
num_portfolios = st.sidebar.slider("Anzahl simulierter Portfolios", 1000, 20000, 5000, 1000)
risk_free_rate = st.sidebar.number_input("Risikofreier Zins (%)", value=2.0, step=0.1) / 100

st.sidebar.info(
	"Der Algorithmus testet zufällige Gewichtungen dieser 4 Anlageklassen, um die 'Efficient Frontier' (Effizienzgrenze) zu zeichnen.")


# ==========================================
# 4. Monte-Carlo-Simulation der Gewichtungen
# ==========================================
def simulate_portfolios(num_portfolios, expected_returns, cov_matrix, risk_free_rate):
	results = np.zeros((3, num_portfolios))
	weights_record = []

	for i in range(num_portfolios):
		# Zufällige Gewichtungen erzeugen und auf 1 (100%) normalisieren
		weights = np.random.random(num_assets)
		weights /= np.sum(weights)
		weights_record.append(weights)

		# Erwartete Portfolio-Rendite
		portfolio_return = np.sum(weights * expected_returns)

		# Erwartete Portfolio-Volatilität (Risiko)
		portfolio_std_dev = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))

		# Sharpe Ratio
		sharpe_ratio = (portfolio_return - risk_free_rate) / portfolio_std_dev

		results[0, i] = portfolio_std_dev
		results[1, i] = portfolio_return
		results[2, i] = sharpe_ratio

	return results, weights_record


with st.spinner("Berechne Portfolios..."):
	results, weights_record = simulate_portfolios(num_portfolios, expected_returns, cov_matrix, risk_free_rate)

# ==========================================
# 5. Auswertung: Die besten Portfolios identifizieren
# ==========================================
# Max Sharpe Ratio (Bestes Risiko-Rendite-Verhältnis)
max_sharpe_idx = np.argmax(results[2])
std_max_sharpe = results[0, max_sharpe_idx]
ret_max_sharpe = results[1, max_sharpe_idx]
weights_max_sharpe = weights_record[max_sharpe_idx]

# Min Volatility (Geringstes absolutes Risiko)
min_vol_idx = np.argmin(results[0])
std_min_vol = results[0, min_vol_idx]
ret_min_vol = results[1, min_vol_idx]
weights_min_vol = weights_record[min_vol_idx]

# ==========================================
# 6. Main UI: Visualisierung
# ==========================================
st.header("1. Effizienzgrenze (Efficient Frontier)")

# Plotly Scatter Plot
fig = go.Figure()

# Alle simulierten Portfolios
fig.add_trace(go.Scatter(
	x=results[0],
	y=results[1],
	mode='markers',
	marker=dict(
		color=results[2],
		colorscale='Viridis',
		showscale=True,
		size=4,
		colorbar=dict(title="Sharpe Ratio")
	),
	name='Simulierte Portfolios',
	hoverinfo='text',
	text=[f"Rendite: {r * 100:.2f}%<br>Risiko (Vol): {v * 100:.2f}%<br>Sharpe: {s:.2f}"
	      for r, v, s in zip(results[1], results[0], results[2])]
))

# Max Sharpe Marker (Roter Stern)
fig.add_trace(go.Scatter(
	x=[std_max_sharpe], y=[ret_max_sharpe], mode='markers',
	marker=dict(color='red', size=15, symbol='star'),
	name='Max Sharpe Ratio'
))

# Min Volatility Marker (Blauer Stern)
fig.add_trace(go.Scatter(
	x=[std_min_vol], y=[ret_min_vol], mode='markers',
	marker=dict(color='cyan', size=15, symbol='star'),
	name='Min Volatility'
))

fig.update_layout(
	xaxis_title="Risiko (Volatilität / Standardabweichung)",
	yaxis_title="Erwartete Rendite",
	template="plotly_dark",
	height=600,
	showlegend=True,
	legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# ==========================================
# 7. Main UI: Portfolio-Gewichtungen
# ==========================================
st.header("2. Optimale Allokationen")

col1, col2 = st.columns(2)

with col1:
	st.subheader("⭐ Tangential-Portfolio (Max Sharpe)")
	st.markdown("Bietet die höchste Überrendite pro Risikoeinheit.")
	st.metric("Erwartete Rendite", f"{ret_max_sharpe * 100:.2f}%")
	st.metric("Erwartetes Risiko", f"{std_max_sharpe * 100:.2f}%")
	st.metric("Sharpe Ratio", f"{results[2, max_sharpe_idx]:.2f}")

	df_max_sharpe = pd.DataFrame({"Asset": assets, "Gewichtung": [f"{w * 100:.2f}%" for w in weights_max_sharpe]})
	st.dataframe(df_max_sharpe, hide_index=True, use_container_width=True)

with col2:
	st.subheader("🛡️ Global Minimum Variance")
	st.markdown("Das Portfolio mit den geringsten absoluten Schwankungen.")
	st.metric("Erwartete Rendite", f"{ret_min_vol * 100:.2f}%")
	st.metric("Erwartetes Risiko", f"{std_min_vol * 100:.2f}%")
	st.metric("Sharpe Ratio", f"{results[2, min_vol_idx]:.2f}")

	df_min_vol = pd.DataFrame({"Asset": assets, "Gewichtung": [f"{w * 100:.2f}%" for w in weights_min_vol]})
	st.dataframe(df_min_vol, hide_index=True, use_container_width=True)