import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import statsmodels.api as sm
from statsmodels.tsa.stattools import coint

# ==========================================
# 1. Page Configuration
# ==========================================
st.set_page_config(page_title="Pairs Trading", layout="wide")
st.title("⚖️ Pairs Trading & Cointegration")
st.markdown("Finde Assets, die an einer unsichtbaren Leine laufen (Mean Reversion) und generiere Trading-Signale.")

# ==========================================
# 2. Input & Parameter
# ==========================================
col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
with col1:
	ticker_A = st.text_input("Asset A (z.B. KO)", value="KO").upper()  # Coca-Cola
with col2:
	ticker_B = st.text_input("Asset B (z.B. PEP)", value="PEP").upper()  # Pepsi
with col3:
	timeframe = st.selectbox("Historie", ["1y", "2y", "5y"], index=1)
with col4:
	z_threshold = st.number_input("Z-Score Threshold (Signal)", value=2.0, step=0.1,
	                              help="Ab wie vielen Standardabweichungen traden wir?")

if st.button("Kointegration & Spread analysieren", type="primary"):
	with st.spinner("Analysiere Preis-Spreads und statistische Kointegration..."):

		# Daten laden (Preise, nicht Renditen!)
		data = yf.download([ticker_A, ticker_B], period=timeframe)['Close']
		data = data.dropna()

		if len(data.columns) != 2:
			st.error("Fehler beim Laden. Bitte prüfe die Ticker.")
		else:
			price_A = data[ticker_A]
			price_B = data[ticker_B]

			st.divider()

			# ==========================================
			# 3. Engle-Granger Cointegration Test
			# ==========================================
			st.header("1. Kointegrations-Test (Die 'Leine')")

			# Der Test prüft, ob die Linearkombination beider Preise stationär ist
			score, p_value, _ = coint(price_A, price_B)

			# Interpretation
			if p_value < 0.05:
				status = "Erfolgreich! Assets sind kointegriert ✅"
				status_color = "normal"
				st.success(
					f"**Bestätigt:** {ticker_A} und {ticker_B} sind kointegriert. Der Preisabstand ist mathematisch begrenzt (Mean Reversion). Perfekt für Pairs Trading!")
			else:
				status = "Fehlgeschlagen! Keine Kointegration ❌"
				status_color = "inverse"
				st.warning(
					f"**Achtung:** Der P-Value ({p_value:.3f}) ist zu hoch. Die Assets können endlos auseinanderdriften. Pairs Trading ist hier gefährlich!")

			c1, c2 = st.columns(2)
			c1.metric("Engle-Granger P-Value", f"{p_value:.4f}",
			          help="Muss kleiner als 0.05 sein, um Kointegration zu beweisen.")
			c2.metric("Test Status", status, delta_color=status_color)

			# ==========================================
			# 4. Spread & Z-Score Berechnung (OLS Regression)
			# ==========================================
			st.header("2. Spread & Trading Signale")

			# Ordinary Least Squares (OLS) Regression, um das Hedge-Ratio (Beta) zu finden
			# Preis_A = Beta * Preis_B + Alpha
			X = sm.add_constant(price_B)
			model = sm.OLS(price_A, X).fit()
			beta = model.params[ticker_B]  # Das Hedge-Ratio

			# Der Spread ist die Differenz der tatsächlichen Preise unter Berücksichtigung des Hedge-Ratios
			spread = price_A - (beta * price_B)

			# Z-Score Normalisierung: (Wert - Mittelwert) / Standardabweichung
			z_score = (spread - spread.mean()) / spread.std()

			st.info(
				f"**Hedge Ratio (Beta): {beta:.3f}** | Um marktneutral zu sein, kaufst du für jede Aktie von {ticker_A} exakt {beta:.3f} Aktien von {ticker_B} (oder andersherum).")

			# ==========================================
			# 5. Visualisierung: Z-Score Trading Bands
			# ==========================================
			fig_z = go.Figure()

			# Z-Score Linie
			fig_z.add_trace(go.Scatter(x=z_score.index, y=z_score, mode='lines', name='Z-Score (Abweichung)',
			                           line=dict(color='#00ccff')))

			# Mean (0)
			fig_z.add_hline(y=0, line_dash="solid", line_color="gray", annotation_text="Mittelwert (Take Profit)")

			# Upper Threshold (Short Spread)
			fig_z.add_hline(y=z_threshold, line_dash="dash", line_color="red",
			                annotation_text=f"Short Spread (+{z_threshold}σ)")

			# Lower Threshold (Long Spread)
			fig_z.add_hline(y=-z_threshold, line_dash="dash", line_color="green",
			                annotation_text=f"Long Spread (-{z_threshold}σ)")

			fig_z.update_layout(
				title=f"Normalisierter Spread (Z-Score) zwischen {ticker_A} und {ticker_B}",
				xaxis_title="Datum",
				yaxis_title="Standardabweichungen (Z-Score)",
				template="plotly_dark",
				height=450,
				hovermode="x unified"
			)
			st.plotly_chart(fig_z, use_container_width=True)

			# ==========================================
			# 6. Aktuelles Handelssignal
			# ==========================================
			current_z = z_score.iloc[-1]
			st.subheader("Aktuelles Markt-Signal")

			if current_z > z_threshold:
				st.error(
					f"📉 **SHORT SPREAD:** {ticker_A} ist relativ zu {ticker_B} historisch überbewertet. \n\n**Aktion:** Leerverkauf (Short) {ticker_A} und Kauf (Long) {ticker_B}.")
			elif current_z < -z_threshold:
				st.success(
					f"📈 **LONG SPREAD:** {ticker_A} ist relativ zu {ticker_B} historisch unterbewertet. \n\n**Aktion:** Kauf (Long) {ticker_A} und Leerverkauf (Short) {ticker_B}.")
			else:
				st.info(
					f"⏳ **HOLD / NO TRADE:** Der Spread ({current_z:.2f}σ) bewegt sich innerhalb der normalen historischen Grenzen. Kein klares Arbitrage-Signal.")