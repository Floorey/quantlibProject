import streamlit as st
import yfinance as yf
import numpy as np
from scipy.stats import norm
import plotly.graph_objects as go

# ==========================================
# 1. Page Configuration
# ==========================================
st.set_page_config(page_title="Warrant Pricer", layout="wide")
st.title("🛡️ Fair Value Warrant Calculator (Optionsscheine)")
st.markdown("Überprüfe die Preisstellung der Banken und berechne das versteckte Aufgeld bei deutschen Optionsscheinen.")


# ==========================================
# 2. Black-Scholes Engine für Warrants
# ==========================================
def black_scholes_warrant(S, K, T, r, sigma, ratio, option_type="Call"):
	"""Berechnet den fairen Preis eines Optionsscheins."""
	if T <= 0 or sigma <= 0:
		return 0.0

	d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
	d2 = d1 - sigma * np.sqrt(T)

	if option_type == "Call":
		bs_price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
	else:
		bs_price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

	return bs_price * ratio


# ==========================================
# 3. Input & Parameter
# ==========================================
st.header("1. Schein-Parameter eingeben")

col1, col2, col3, col4 = st.columns(4)

with col1:
	ticker = st.text_input("Basiswert Ticker (z.B. MU)", value="MU").upper()
	option_type = st.selectbox("Typ", ["Call", "Put"])
with col2:
	strike = st.number_input("Basispreis (Strike) in $", value=150.0, step=5.0)
	ratio = st.number_input("Bezugsverhältnis (Ratio)", value=0.1, step=0.01, format="%.3f")
with col3:
	days_to_expiry = st.number_input("Restlaufzeit (Tage)", value=90, step=1)
	bank_price = st.number_input("Preis der Bank (€)", value=5.00, step=0.1)
with col4:
	implied_vol = st.number_input("Implizite Volatilität (%)", value=45.0, step=1.0) / 100
	risk_free_rate = st.number_input("Risikofreier Zins (%)", value=4.0, step=0.1) / 100
	eur_usd_rate = st.number_input("Wechselkurs (EUR/USD)", value=1.08, step=0.01,
	                               help="Wichtig, da US-Aktien in $, Scheine in €!")

if st.button("Fairen Wert berechnen", type="primary"):
	with st.spinner(f"Lade Live-Kurs für {ticker} und berechne fairen Wert..."):
		# Live Daten ziehen
		stock = yf.Ticker(ticker)
		try:
			current_price_usd = stock.history(period="1d")['Close'].iloc[-1]

			st.divider()

			# ==========================================
			# 4. Berechnung & Bewertung
			# ==========================================
			T_years = days_to_expiry / 365.0

			# Fairer Wert in USD
			fair_value_usd = black_scholes_warrant(current_price_usd, strike, T_years, risk_free_rate, implied_vol,
			                                       ratio, option_type)

			# Umrechnung in EUR
			fair_value_eur = fair_value_usd / eur_usd_rate

			# Premium (Aufgeld der Bank) berechnen
			premium_pct = ((bank_price - fair_value_eur) / fair_value_eur) * 100 if fair_value_eur > 0 else 0

			st.header("2. Analyse-Ergebnis")

			c1, c2, c3, c4 = st.columns(4)
			c1.metric("Aktueller Aktienkurs", f"${current_price_usd:.2f}")
			c2.metric("Fairer Wert (Mathematisch)", f"€{fair_value_eur:.3f}")
			c3.metric("Preis der Bank", f"€{bank_price:.3f}")

			# Rote oder grüne Anzeige je nach Aufgeld
			if premium_pct > 0:
				c4.metric("Verstecktes Aufgeld", f"+{premium_pct:.2f}%", delta_color="inverse")
				st.warning(
					f"**Achtung:** Der Emittent verlangt aktuell einen Aufschlag von **{premium_pct:.2f}%** auf den rein mathematischen Wert. Das ist die Marge der Bank!")
			else:
				c4.metric("Verstecktes Aufgeld", f"{premium_pct:.2f}%", delta_color="normal")
				st.success(
					f"**Guter Deal:** Die Bank stellt den Schein aktuell günstiger als unser Black-Scholes-Modell bewertet (-{abs(premium_pct):.2f}%).")

			# ==========================================
			# 5. Visualisierung: Was-wäre-wenn (Szenario Analyse)
			# ==========================================
			st.subheader("Szenario-Analyse: Wie reagiert der Schein?")

			# Preis-Range generieren (+/- 20% vom aktuellen Kurs)
			price_range = np.linspace(current_price_usd * 0.8, current_price_usd * 1.2, 50)
			warrant_prices = [black_scholes_warrant(p, strike, T_years, risk_free_rate, implied_vol, ratio,
			                                        option_type) / eur_usd_rate for p in price_range]

			fig = go.Figure()
			fig.add_trace(go.Scatter(x=price_range, y=warrant_prices, mode='lines', name='Fairer Wert des Scheins (€)',
			                         line=dict(color='#00ccff', width=3)))

			# Aktuelle Position markieren
			fig.add_vline(x=current_price_usd, line_dash="dash", line_color="gray", annotation_text="Aktueller Kurs")
			fig.add_hline(y=fair_value_eur, line_dash="dash", line_color="green", annotation_text="Fairer Wert")
			fig.add_hline(y=bank_price, line_dash="dash", line_color="red", annotation_text="Bank Preis")

			fig.update_layout(
				title=f"Theoretischer Wertverlauf des {option_type}-Scheins auf {ticker}",
				xaxis_title="Aktienkurs in $",
				yaxis_title="Schein-Preis in €",
				template="plotly_dark",
				hovermode="x unified"
			)
			st.plotly_chart(fig, use_container_width=True)

		except Exception as e:
			st.error(f"Fehler beim Abrufen der Marktdaten. Bitte überprüfe den Ticker. Details: {e}")