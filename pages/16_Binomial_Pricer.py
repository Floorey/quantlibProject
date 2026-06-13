import streamlit as st
import numpy as np
import yfinance as yf
import plotly.graph_objects as go

# ==========================================
# 1. Page Config
# ==========================================
st.set_page_config(page_title="Advanced Option Pricer", layout="wide")
st.title("🌳 Binomial Tree Option Pricer (American Style)")
st.markdown(
	"Das Standardmodell der Wall Street für echte US-Optionen. Berechnet den Premium-Aufschlag für das Recht auf vorzeitige Ausübung (Early Exercise).")


# ==========================================
# 2. Die Quant-Mathematik (Cox-Ross-Rubinstein)
# ==========================================
def binomial_pricer(S, K, T, r, sigma, steps, option_type="Put", style="American"):
	"""
	Berechnet Optionspreise via Binomialbaum.
	"""
	if T <= 0 or sigma <= 0 or steps <= 0:
		return 0.0

	dt = T / steps

	# CRR Parameter
	u = np.exp(sigma * np.sqrt(dt))
	d = 1 / u
	p = (np.exp(r * dt) - d) / (u - d)
	discount = np.exp(-r * dt)

	# 1. Initialisiere die Aktienkurse am Verfallstag (Knoten N)
	# np.arange(steps, -1, -1) generiert [N, N-1, ..., 0] für Up-Moves
	# np.arange(0, steps + 1, 1) generiert [0, 1, ..., N] für Down-Moves
	prices = S * (u ** np.arange(steps, -1, -1)) * (d ** np.arange(0, steps + 1, 1))

	# 2. Berechne den inneren Wert der Option am Verfallstag
	if option_type == "Call":
		values = np.maximum(0, prices - K)
	else:
		values = np.maximum(0, K - prices)

	# 3. Rückwärts-Induktion (Gehe im Baum Schritt für Schritt rückwärts bis zum Start)
	for i in range(steps - 1, -1, -1):
		# Aktualisiere die Aktienkurse für diesen speziellen Zeitschritt
		prices = S * (u ** np.arange(i, -1, -1)) * (d ** np.arange(0, i + 1, 1))

		# Berechne den diskontierten Erwartungswert (Halten der Option)
		values = discount * (p * values[:-1] + (1 - p) * values[1:])

		# Frühe Ausübung prüfen (NUR BEI AMERIKANISCHEN OPTIONEN)
		if style == "American":
			if option_type == "Call":
				values = np.maximum(values, prices - K)
			else:
				values = np.maximum(values, K - prices)

	return values[0]


# ==========================================
# 3. Input & Parameter
# ==========================================
st.header("1. Options-Parameter")

col1, col2, col3, col4 = st.columns(4)

with col1:
	ticker = st.text_input("Basiswert Ticker", value="MU").upper()
	option_type = st.selectbox("Typ", ["Put", "Call"])
with col2:
	strike = st.number_input("Basispreis (Strike) in $", value=880.0, step=5.0)
	days_to_expiry = st.number_input("Restlaufzeit (Tage)", value=21, step=1)
with col3:
	implied_vol = st.number_input("Implizite Volatilität (%)", value=45.0, step=1.0) / 100
	risk_free_rate = st.number_input("Risikofreier Zins (%)", value=4.0, step=0.1) / 100
with col4:
	steps = st.slider("Simulations-Schritte (Tiefe des Baums)", min_value=10, max_value=500, value=100, step=10,
	                  help="Je mehr Schritte, desto genauer, aber langsamer.")

if st.button("Amerikanischen Preis berechnen", type="primary"):
	with st.spinner("Lade Live-Kurs und berechne Binomialbaum..."):
		try:
			# Live Kurs holen
			stock = yf.Ticker(ticker)
			current_price = stock.history(period="1d")['Close'].iloc[-1]

			T_years = days_to_expiry / 365.0

			# Beide Preise berechnen, um den Unterschied zu zeigen
			price_american = binomial_pricer(current_price, strike, T_years, risk_free_rate, implied_vol, steps,
			                                 option_type, style="American")
			price_european = binomial_pricer(current_price, strike, T_years, risk_free_rate, implied_vol, steps,
			                                 option_type, style="European")

			# Die Early-Exercise-Prämie
			early_exercise_premium = price_american - price_european

			st.divider()
			st.header("2. Pricing Ergebnisse")

			c1, c2, c3 = st.columns(3)
			c1.metric("Aktueller Aktienkurs", f"${current_price:.2f}")
			c2.metric(f"Faire US-Option (American)", f"${price_american:.2f}", "Echter Wert bei Alpaca",
			          delta_color="off")
			c3.metric(f"Early Exercise Premium", f"+${early_exercise_premium:.3f}", "Wert der Flexibilität")

			# ==========================================
			# 4. Konvergenz-Analyse (Wie Quants Modelle testen)
			# ==========================================
			st.subheader("Konvergenz-Analyse des Algorithmus")
			st.markdown("Zeigt, wie sich der berechnete Preis stabilisiert, je tiefer der Binomialbaum berechnet wird.")

			# Wir berechnen den Preis für verschiedene Baum-Tiefen, um die Stabilität zu prüfen
			test_steps = [10, 25, 50, 100, 150, 200]
			convergence_prices = []

			progress_bar = st.progress(0)
			for idx, s in enumerate(test_steps):
				p = binomial_pricer(current_price, strike, T_years, risk_free_rate, implied_vol, s, option_type,
				                    style="American")
				convergence_prices.append(p)
				progress_bar.progress((idx + 1) / len(test_steps))
			progress_bar.empty()

			fig = go.Figure()
			fig.add_trace(go.Scatter(x=test_steps, y=convergence_prices, mode='lines+markers',
			                         line=dict(color='#00ccff', width=3)))
			fig.update_layout(
				title=f"Modell-Konvergenz für {option_type}-Option",
				xaxis_title="Anzahl der Berechnungsschritte im Baum",
				yaxis_title="Berechneter Optionspreis ($)",
				template="plotly_dark"
			)
			st.plotly_chart(fig, use_container_width=True)

			st.info(
				"💡 **Warum American Puts teurer sind:** Bei einem Put gewinnst du, wenn die Aktie fällt. Der maximale Gewinn ist erreicht, wenn die Aktie auf 0 fällt. Wenn das vor dem Verfallstag passiert, möchtest du das Geld sofort haben (um Zinsen zu kassieren) und nicht bis zum Verfall warten. Dieses Recht macht amerikanische Puts wertvoller als europäische.")

		except Exception as e:
			st.error(f"Fehler bei der Berechnung: {e}")