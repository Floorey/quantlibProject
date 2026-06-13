import streamlit as st
import numpy as np
import yfinance as yf
import plotly.graph_objects as go

# ==========================================
# 1. Page Config
# ==========================================
st.set_page_config(page_title="Exotic Option Pricer", layout="wide")
st.title("🚧 Exotic Pricer (Monte Carlo Knock-Outs)")
st.markdown(
	"Bewertet pfadabhängige Derivate (z.B. Barrier-Optionen). Hier zählt nicht nur der Preis am Verfallstag, sondern der gesamte Weg dorthin.")


# ==========================================
# 2. Die Quant-Mathematik (Monte Carlo GBM)
# ==========================================
def monte_carlo_barrier_pricer(S, K, barrier, T, r, sigma, simulations=10000, steps=252):
	"""
	Simuliert Pfade via Geometrischer Brownscher Bewegung und bewertet einen Up-and-Out Call.
	"""
	if T <= 0 or sigma <= 0:
		return 0.0, np.zeros((1, 1))

	dt = T / steps

	# Pre-allokiere die Pfad-Matrix (Zeilen = Schritte, Spalten = Simulationen)
	paths = np.zeros((steps + 1, simulations))
	paths[0] = S

	# 1. Stochastische Pfade generieren (GBM)
	for t in range(1, steps + 1):
		# Zufallsvariable Z aus Normalverteilung
		z = np.random.standard_normal(simulations)
		# S_t = S_{t-1} * exp((r - 0.5*sigma^2)*dt + sigma*sqrt(dt)*Z)
		paths[t] = paths[t - 1] * np.exp((r - 0.5 * sigma ** 2) * dt + sigma * np.sqrt(dt) * z)

	# 2. Pfadabhängigkeit prüfen (Knock-Out Bedingung)
	# Hat der Pfad an irgendeinem Punkt die Barriere überschritten?
	knocked_out = np.max(paths, axis=0) >= barrier

	# 3. Auszahlung (Payoff) am Ende berechnen
	# Wenn knocked_out == True -> 0, ansonsten max(S_T - K, 0)
	payoffs = np.where(knocked_out, 0.0, np.maximum(paths[-1] - K, 0.0))

	# 4. Fairen Wert berechnen (Diskontierter Durchschnitt aller Payoffs)
	fair_value = np.exp(-r * T) * np.mean(payoffs)

	return fair_value, paths, knocked_out


# ==========================================
# 3. Input & Parameter
# ==========================================
st.header("1. Exotische Options-Parameter (Up-and-Out Call)")

col1, col2, col3, col4 = st.columns(4)

with col1:
	ticker = st.text_input("Basiswert Ticker", value="NVDA").upper()
	simulations = st.selectbox("Simulationen (Pfade)", [1000, 5000, 10000, 50000], index=2)
with col2:
	strike = st.number_input("Basispreis (Strike) in $", value=120.0, step=5.0)
	barrier = st.number_input("Knock-Out Barriere in $", value=150.0, step=5.0,
	                          help="Wenn die Aktie diesen Preis berührt, verfällt die Option wertlos.")
with col3:
	days_to_expiry = st.number_input("Restlaufzeit (Tage)", value=90, step=1)
	steps = st.number_input("Schritte (Tage simuliert)", value=90, step=1)
with col4:
	implied_vol = st.number_input("Implizite Volatilität (%)", value=50.0, step=1.0) / 100
	risk_free_rate = st.number_input("Risikofreier Zins (%)", value=4.0, step=0.1) / 100

# Plausibilitätsprüfung
if barrier <= strike:
	st.error("🚨 Fehler: Bei einem Up-and-Out Call muss die Barriere über dem Strike liegen!")
	st.stop()

if st.button("Knock-Out Option bepreisen", type="primary"):
	with st.spinner("Berechne zehntausende stochastische Zukunftspfade..."):
		try:
			# Live Kurs holen
			stock = yf.Ticker(ticker)
			current_price = stock.history(period="1d")['Close'].iloc[-1]

			if current_price >= barrier:
				st.error(
					f"Die Aktie ({current_price:.2f}$) hat die Barriere ({barrier}$) bereits durchbrochen. Die Option ist wertlos.")
				st.stop()

			T_years = days_to_expiry / 365.0

			# Monte Carlo Maschine anwerfen
			fair_value, paths, knocked_out = monte_carlo_barrier_pricer(
				current_price, strike, barrier, T_years, risk_free_rate, implied_vol, simulations, steps
			)

			# Statistik für die Ausgabe berechnen
			total_knocked_out = np.sum(knocked_out)
			ko_probability = (total_knocked_out / simulations) * 100

			st.divider()
			st.header("2. Pricing Ergebnisse")

			c1, c2, c3, c4 = st.columns(4)
			c1.metric("Aktueller Kurs", f"${current_price:.2f}")
			c2.metric("Fairer Preis (Monte Carlo)", f"${fair_value:.3f}", "Knock-Out bewertet", delta_color="off")
			c3.metric("Simulierte Pfade", f"{simulations:,}")
			c4.metric("Knock-Out Wahrscheinlichkeit", f"{ko_probability:.1f}%", delta_color="inverse")

			# ==========================================
			# 4. Visualisierung der Pfadabhängigkeit
			# ==========================================
			st.subheader("Visualisierung der stochastischen Pfade")
			st.markdown(
				"Das Chart zeigt exemplarisch 150 der simulierten Pfade. Rote Pfade haben die Knock-Out-Barriere berührt und sind verfallen. Grüne Pfade haben überlebt und Gewinn erzielt.")

			# Wir plotten aus Performance-Gründen maximal 150 Pfade
			paths_to_plot = min(simulations, 150)

			fig = go.Figure()

			# Einzelne Pfade zeichnen
			for i in range(paths_to_plot):
				# Wenn der Pfad ausgeknockt wurde, markieren wir ihn rot
				if knocked_out[i]:
					path_color = 'rgba(255, 50, 50, 0.3)'  # Rot
				# Wenn er nicht ausknockte und am Ende über Strike ist -> grün
				elif paths[-1, i] > strike:
					path_color = 'rgba(50, 255, 50, 0.4)'  # Grün
				# Überlebt, aber unter Strike -> grau
				else:
					path_color = 'rgba(150, 150, 150, 0.2)'  # Grau

				fig.add_trace(go.Scatter(x=np.arange(steps + 1), y=paths[:, i], mode='lines',
				                         line=dict(color=path_color, width=1), showlegend=False))

			# Harte Linien für Strike und Barriere
			fig.add_hline(y=barrier, line_dash="dash", line_color="red", line_width=3,
			              annotation_text="Knock-Out Barriere")
			fig.add_hline(y=strike, line_dash="solid", line_color="green", line_width=2,
			              annotation_text="Basispreis (Strike)")
			fig.add_hline(y=current_price, line_dash="dot", line_color="white", annotation_text="Startpreis")

			fig.update_layout(
				xaxis_title="Simulationstage",
				yaxis_title="Aktienkurs in $",
				template="plotly_dark",
				height=600
			)
			st.plotly_chart(fig)

		except Exception as e:
			st.error(f"Fehler bei der Berechnung: {e}")