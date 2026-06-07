import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import scipy.stats as stats
import statsmodels.api as sm
from statsmodels.tsa.stattools import ccf

# ==========================================
# 1. Page Configuration
# ==========================================
st.set_page_config(page_title="Advanced Correlation", layout="wide")
st.title("🔗 Deep Correlation & Lead-Lag Analysis")
st.markdown(
	"Untersuche, ob zwei Assets wirklich zusammenhängen, oder ob es sich nur um eine Scheinkorrelation handelt.")

# ==========================================
# 2. Input & Daten-Download
# ==========================================
st.header("1. Asset Auswahl")
col1, col2, col3 = st.columns([1, 1, 2])
with col1:
	ticker_A = st.text_input("Asset A (Leader/Signal)", value="QQQ").upper()
with col2:
	ticker_B = st.text_input("Asset B (Follower/Target)", value="AAPL").upper()
with col3:
	timeframe = st.selectbox("Zeitraum", ["1y", "2y", "5y", "10y"], index=1)

if st.button("Korrelation analysieren", type="primary"):
	with st.spinner("Lade historische Daten und berechne Statistiken..."):
		# Daten laden
		data = yf.download([ticker_A, ticker_B], period=timeframe)['Close']

		# Daten bereinigen (Drop NaN)
		data = data.dropna()

		if len(data.columns) != 2:
			st.error("Fehler beim Laden der Daten. Bitte Ticker prüfen.")
		else:
			# Renditen berechnen (Korrelation von Preisen ist oft ungenau wegen Trends, Renditen sind besser!)
			returns = data.pct_change().dropna()
			ret_A = returns[ticker_A]
			ret_B = returns[ticker_B]

			st.divider()

			# ==========================================
			# 3. Statische Korrelation & Signifikanz (P-Value)
			# ==========================================
			st.header("2. Statistische Signifikanz")

			corr_pearson, p_value = stats.pearsonr(ret_A, ret_B)

			# Interpretation des P-Values
			if p_value < 0.01:
				sig_text = "Sehr Hoch (p < 0.01) ✅"
				sig_color = "normal"
			elif p_value < 0.05:
				sig_text = "Signifikant (p < 0.05) ✅"
				sig_color = "normal"
			else:
				sig_text = "Nicht Signifikant (Zufall möglich) ❌"
				sig_color = "inverse"

			m1, m2, m3 = st.columns(3)
			m1.metric("Pearson Korrelation (Renditen)", f"{corr_pearson:.3f}",
			          help="1 = Perfekter Gleichlauf, -1 = Perfekt gegenläufig, 0 = Kein Zusammenhang")
			m2.metric("Signifikanz (Sicherheit)", sig_text, delta_color=sig_color)
			m3.metric("Erklärte Varianz (R²)", f"{(corr_pearson ** 2) * 100:.1f}%",
			          help="So viel % der Bewegung von B wird durch A erklärt.")

			if p_value >= 0.05:
				st.warning(
					"⚠️ **Achtung:** Der P-Value ist zu hoch. Die gemessene Korrelation ist statistisch nicht signifikant und könnte reiner Zufall sein (Spurious Correlation).")

			st.divider()

			# ==========================================
			# 4. Rolling Correlation (Stabilität über Zeit)
			# ==========================================
			st.header("3. Rolling Correlation (60 Tage)")
			st.markdown("Ist die Beziehung stabil oder bricht sie in Krisen zusammen?")

			rolling_corr = ret_A.rolling(window=60).corr(ret_B).dropna()

			fig_roll = go.Figure()
			fig_roll.add_trace(go.Scatter(x=rolling_corr.index, y=rolling_corr, mode='lines', name='60d Korrelation',
			                              line=dict(color='#00ccff')))
			fig_roll.add_hline(y=0, line_dash="dash", line_color="red")
			fig_roll.add_hline(y=corr_pearson, line_dash="dot", line_color="gray", annotation_text="Durchschnitt")
			fig_roll.update_layout(yaxis_title="Korrelations-Koeffizient", xaxis_title="Datum", template="plotly_dark",
			                       height=350, yaxis=dict(range=[-1.1, 1.1]))
			st.plotly_chart(fig_roll, use_container_width=True)

			st.divider()

			# ==========================================
			# 5. Cross-Correlation (Lead / Lag)
			# ==========================================
			st.header("4. Cross-Correlation (Lead-Lag Analyse)")
			st.markdown(
				f"Gibt es ein zeitversetztes Muster? Reagiert **{ticker_B}** vielleicht erst Tage nach **{ticker_A}**?")

			# Berechne Cross-Correlation für Lags von -10 bis +10 Tagen
			lags = 10
			# ccf berechnet die Korrelation zwischen ret_A und verschobenem ret_B
			cross_corrs = ccf(ret_A, ret_B, adjusted=False)[:lags + 1]

			# Wir machen es manuell für beide Richtungen, um es sauberer für Aktien zu haben
			lag_range = range(-lags, lags + 1)
			cross_corr_values = []

			for lag in lag_range:
				if lag == 0:
					cross_corr_values.append(corr_pearson)
				elif lag > 0:
					# A führt B (B reagiert später)
					cross_corr_values.append(ret_A.shift(lag).corr(ret_B))
				else:
					# B führt A (A reagiert später)
					cross_corr_values.append(ret_A.corr(ret_B.shift(-lag)))

			# Finde den stärksten Lag
			best_lag = lag_range[np.argmax(np.abs(cross_corr_values))]
			best_corr = cross_corr_values[np.argmax(np.abs(cross_corr_values))]

			fig_ccf = go.Figure()

			# Farben: Lag 0 grau, der stärkste grün, der Rest blau
			colors = ['#00ccff' if l != best_lag and l != 0 else ('gray' if l == 0 else '#00ff00') for l in lag_range]

			fig_ccf.add_trace(go.Bar(
				x=list(lag_range),
				y=cross_corr_values,
				marker_color=colors,
				text=[f"{v:.2f}" for v in cross_corr_values],
				textposition='outside'
			))

			fig_ccf.update_layout(
				xaxis_title="Zeitversatz in Tagen (Negative = B führt A | Positive = A führt B)",
				yaxis_title="Korrelation",
				template="plotly_dark",
				height=400,
				xaxis=dict(tickmode='linear', tick0=-lags, dtick=1)
			)
			st.plotly_chart(fig_ccf, use_container_width=True)

			if best_lag > 0:
				st.success(
					f"💡 **Signal-Theorie:** {ticker_A} scheint ein Frühindikator für {ticker_B} zu sein. Die stärkste Korrelation ({best_corr:.2f}) tritt auf, wenn man {ticker_B} um **{best_lag} Tage in die Zukunft** verschiebt.")
			elif best_lag < 0:
				st.info(
					f"💡 **Signal-Theorie:** {ticker_B} ist der eigentliche Leader! Die stärkste Korrelation ({best_corr:.2f}) liegt bei **{abs(best_lag)} Tagen Versatz** zugunsten von {ticker_B}.")
			else:
				st.info(
					"💡 **Gleichlauf:** Die höchste Korrelation findet am selben Tag statt (Lag 0). Es gibt keinen offensichtlichen zeitlichen Informationsvorsprung.")