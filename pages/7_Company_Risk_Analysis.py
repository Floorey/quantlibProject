import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ==========================================
# 1. Page Configuration
# ==========================================
st.set_page_config(page_title="Quantitative Company Risk", layout="wide")
st.title("🏢 Quantitative Unternehmensanalyse")
st.markdown("Analysiere das fundamentale Insolvenzrisiko (Altman Z-Score) und historische Drawdowns.")

# ==========================================
# 2. Ticker Input & Datenabruf
# ==========================================
col_input, col_empty = st.columns([1, 2])
with col_input:
	ticker_symbol = st.text_input("Ticker-Symbol eingeben (z.B. AAPL, TSLA, INTC):", value="INTC").upper()

if st.button("Analyse starten", type="primary"):
	with st.spinner(f"Lade Bilanz- und Marktdaten für {ticker_symbol}..."):
		ticker = yf.Ticker(ticker_symbol)

		# Versuche Daten zu laden
		info = ticker.info
		bs = ticker.balance_sheet
		fin = ticker.financials
		hist = ticker.history(period="5y")

		if bs.empty or fin.empty or hist.empty:
			st.error(
				"Fehler: Konnte nicht alle benötigten Bilanz- oder Marktdaten laden. Probier einen großen US-Ticker (z.B. MSFT).")
		else:
			# ==========================================
			# 3. Altman Z-Score Berechnung (Fundamental Risk)
			# ==========================================
			try:
				# Hole die aktuellsten Jahresdaten (erste Spalte)
				total_assets = bs.loc["Total Assets"].iloc[0]
				total_liabilities = bs.loc["Total Liabilities Net Minority Interest"].iloc[0]
				current_assets = bs.loc["Current Assets"].iloc[0]
				current_liabilities = bs.loc["Current Liabilities"].iloc[0]
				retained_earnings = bs.loc["Retained Earnings"].iloc[0]

				ebit = fin.loc["EBIT"].iloc[0] if "EBIT" in fin.index else fin.loc["Operating Income"].iloc[0]
				total_revenue = fin.loc["Total Revenue"].iloc[0]

				market_cap = info.get("marketCap", hist['Close'].iloc[-1] * info.get("sharesOutstanding", 1))

				# Die 5 Faktoren
				working_capital = current_assets - current_liabilities

				X1 = working_capital / total_assets
				X2 = retained_earnings / total_assets
				X3 = ebit / total_assets
				X4 = market_cap / total_liabilities
				X5 = total_revenue / total_assets

				# Die Z-Score Formel
				z_score = (1.2 * X1) + (1.4 * X2) + (3.3 * X3) + (0.6 * X4) + (0.99 * X5)

				# Klassifizierung
				if z_score > 2.99:
					z_status, z_color = "Safe Zone (Sicher)", "green"
				elif 1.81 <= z_score <= 2.99:
					z_status, z_color = "Grey Zone (Warnung)", "orange"
				else:
					z_status, z_color = "Distress Zone (Insolvenzgefahr)", "red"

			except Exception as e:
				st.warning(f"Z-Score konnte nicht berechnet werden (Fehlende Bilanzposten). Error: {e}")
				z_score, z_status, z_color = 0, "N/A", "gray"

			# ==========================================
			# 4. Maximum Drawdown Berechnung (Market Risk)
			# ==========================================
			# Drawdown ist der prozentuale Verlust vom bisherigen Höchststand
			cumulative_max = hist['Close'].cummax()
			drawdowns = (hist['Close'] / cumulative_max) - 1
			max_drawdown = drawdowns.min()

			# ==========================================
			# 5. UI Ausgabe
			# ==========================================
			st.divider()
			st.header(f"Risikoprofil: {info.get('shortName', ticker_symbol)}")

			col1, col2, col3 = st.columns(3)
			col1.metric("Beta (Systematisches Risiko)", info.get("beta", "N/A"),
			            help=">1 bedeutet volatiler als der Markt.")
			col2.metric("Max Drawdown (5 Jahre)", f"{max_drawdown * 100:.2f}%", delta_color="inverse")
			col3.metric("Debt-to-Equity Ratio", info.get("debtToEquity", "N/A"),
			            help="Gesamtschulden im Verhältnis zum Eigenkapital.")

			st.divider()

			c_gauge, c_drawdown = st.columns([1, 2])

			with c_gauge:
				st.subheader("Altman Z-Score (Credit Risk)")
				fig_gauge = go.Figure(go.Indicator(
					mode="gauge+number",
					value=z_score,
					domain={'x': [0, 1], 'y': [0, 1]},
					title={'text': f"Status: {z_status}", 'font': {'color': z_color}},
					gauge={
						'axis': {'range': [0, 5]},
						'bar': {'color': "white"},
						'steps': [
							{'range': [0, 1.81], 'color': "rgba(255, 0, 0, 0.4)"},  # Red
							{'range': [1.81, 2.99], 'color': "rgba(255, 165, 0, 0.4)"},  # Orange
							{'range': [2.99, 5], 'color': "rgba(0, 255, 0, 0.4)"}  # Green
						],
					}
				))
				fig_gauge.update_layout(height=350, margin=dict(l=10, r=10, t=50, b=10), template="plotly_dark")
				st.plotly_chart(fig_gauge, use_container_width=True)

				with st.expander("Z-Score Details anzeigen"):
					st.write(f"**X1 (Liquidität):** {X1:.2f}")
					st.write(f"**X2 (Profitabilität Historie):** {X2:.2f}")
					st.write(f"**X3 (Operative Effizienz):** {X3:.2f}")
					st.write(f"**X4 (Marktvertrauen):** {X4:.2f}")
					st.write(f"**X5 (Asset Turnover):** {X5:.2f}")

			with c_drawdown:
				st.subheader("Underwater Chart (Drawdown Risk)")
				fig_dd = go.Figure()
				fig_dd.add_trace(go.Scatter(
					x=drawdowns.index, y=drawdowns * 100,
					mode='lines', name='Drawdown',
					fill='tozeroy', fillcolor='rgba(255, 0, 0, 0.2)', line=dict(color='red', width=1)
				))
				fig_dd.update_layout(
					xaxis_title="Datum", yaxis_title="Verlust vom Höchststand (%)",
					template="plotly_dark", height=350, margin=dict(l=0, r=0, t=30, b=0),
					hovermode="x unified"
				)
				st.plotly_chart(fig_dd, use_container_width=True)