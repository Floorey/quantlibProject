import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ==========================================
# 1. Page Configuration
# ==========================================
st.set_page_config(page_title="Backtesting Engine", layout="wide")
st.title("⏱️ Vectorized Backtesting Engine")
st.markdown(
	"Simuliere historische Trades ohne Look-Ahead Bias und generiere echte Performance-Metriken (Sharpe, Drawdown).")

# ==========================================
# 2. Input Parameter
# ==========================================
st.header("1. Strategie-Parameter (Pairs Trading)")

col1, col2, col3, col4 = st.columns(4)
with col1:
	ticker_A = st.text_input("Asset A", value="AMD").upper()
	ticker_B = st.text_input("Asset B", value="NVDA").upper()
with col2:
	timeframe = st.selectbox("Historie", ["2y", "5y", "10y"], index=1)
	rolling_window = st.number_input("Rolling Window (Tage)", min_value=10, max_value=100, value=30,
	                                 help="Zeitraum für den gleitenden Mittelwert")
with col3:
	entry_z = st.number_input("Z-Score Entry (Signal)", value=2.0, step=0.1)
	exit_z = st.number_input("Z-Score Exit (Take Profit)", value=0.0, step=0.1)
with col4:
	initial_capital = st.number_input("Startkapital ($)", value=100000, step=10000)

if st.button("Backtest Starten", type="primary"):
	with st.spinner(f"Simuliere Handelsstrategie für {ticker_A} vs {ticker_B} über {timeframe}..."):

		# Daten laden
		data = yf.download([ticker_A, ticker_B], period=timeframe)['Close'].dropna()

		if len(data.columns) != 2:
			st.error("Fehler beim Laden der Ticker.")
		else:
			price_A = data[ticker_A]
			price_B = data[ticker_B]

			# ==========================================
			# 3. Rolling Z-Score Berechnung
			# ==========================================
			# Preis-Ratio (Einfacher als OLS für Rolling Backtests)
			ratio = price_A / price_B

			# Rolling Metrics (Verhindert Look-Ahead Bias)
			rolling_mean = ratio.rolling(window=rolling_window).mean()
			rolling_std = ratio.rolling(window=rolling_window).std()
			z_score = (ratio - rolling_mean) / rolling_std

			# Tägliche Renditen der Assets
			ret_A = price_A.pct_change().fillna(0)
			ret_B = price_B.pct_change().fillna(0)

			# ==========================================
			# 4. State-Machine Backtester
			# ==========================================
			position = 0  # 0: flat, 1: long spread, -1: short spread
			equity = initial_capital
			equity_curve = [initial_capital] * rolling_window  # Auffüllen für das Rolling Window

			trade_log = []

			# Wir starten erst nach dem ersten Rolling Window
			for i in range(rolling_window, len(data)):
				current_z = z_score.iloc[i - 1]  # Wir agieren auf dem Signal von gestern
				date = data.index[i]

				# PnL des aktuellen Tages basierend auf der Position
				if position == 1:
					# Long Spread: Wir sind Long A und Short B (50/50 Kapitalallokation)
					daily_pnl = equity * (ret_A.iloc[i] * 0.5 - ret_B.iloc[i] * 0.5)
					equity += daily_pnl
				elif position == -1:
					# Short Spread: Wir sind Short A und Long B
					daily_pnl = equity * (-ret_A.iloc[i] * 0.5 + ret_B.iloc[i] * 0.5)
					equity += daily_pnl

				equity_curve.append(equity)

				# Trading Logik (Entry & Exit)
				if position == 0:
					if current_z < -entry_z:
						position = 1
						trade_log.append({"Datum": date, "Aktion": "Long Spread", "Z-Score": round(current_z, 2)})
					elif current_z > entry_z:
						position = -1
						trade_log.append({"Datum": date, "Aktion": "Short Spread", "Z-Score": round(current_z, 2)})
				elif position == 1:
					if current_z >= -exit_z:  # Take Profit erreicht
						position = 0
						trade_log.append({"Datum": date, "Aktion": "Close Trade", "Z-Score": round(current_z, 2)})
				elif position == -1:
					if current_z <= exit_z:  # Take Profit erreicht
						position = 0
						trade_log.append({"Datum": date, "Aktion": "Close Trade", "Z-Score": round(current_z, 2)})

			# ==========================================
			# 5. Performance Kennzahlen (KPIs) berechnen
			# ==========================================
			st.divider()
			st.header("2. Performance Dashboard")

			equity_series = pd.Series(equity_curve, index=data.index)
			total_return = (equity - initial_capital) / initial_capital

			# Max Drawdown
			roll_max = equity_series.cummax()
			drawdown = (equity_series - roll_max) / roll_max
			max_drawdown = drawdown.min()

			# Sharpe Ratio (Annually, Risk Free Rate ~ 0 für Simplifizierung)
			daily_returns = equity_series.pct_change().dropna()
			sharpe_ratio = np.sqrt(252) * (
						daily_returns.mean() / daily_returns.std()) if daily_returns.std() != 0 else 0

			kpi1, kpi2, kpi3, kpi4 = st.columns(4)
			kpi1.metric("Endkapital", f"${equity:,.2f}", f"{total_return * 100:.2f}%")
			kpi2.metric("Sharpe Ratio", f"{sharpe_ratio:.2f}", help="> 1.0 ist gut, > 2.0 ist fantastisch")
			kpi3.metric("Max Drawdown", f"{max_drawdown * 100:.2f}%", delta_color="inverse")
			kpi4.metric("Anzahl Trades", len(trade_log))

			# ==========================================
			# 6. Visualisierung (Equity Curve)
			# ==========================================
			fig = go.Figure()

			# Equity Curve
			fig.add_trace(go.Scatter(x=equity_series.index, y=equity_series, mode='lines', name='Portfolio Wert',
			                         line=dict(color='#00ccff', width=2)))

			# Buy & Hold Benchmark (50/50 Portfolio ohne Trading)
			bh_A = (price_A / price_A.iloc[0]) * (initial_capital / 2)
			bh_B = (price_B / price_B.iloc[0]) * (initial_capital / 2)
			bh_portfolio = bh_A + bh_B
			fig.add_trace(
				go.Scatter(x=bh_portfolio.index, y=bh_portfolio, mode='lines', name='Buy & Hold (50/50 Benchmark)',
				           line=dict(color='gray', dash='dash')))

			fig.update_layout(title="Equity Curve vs Benchmark", xaxis_title="Datum", yaxis_title="Kapital in $",
			                  template="plotly_dark", hovermode="x unified", height=500)
			st.plotly_chart(fig, use_container_width=True)

			# Trade Historie
			with st.expander("📝 Trade-Historie ansehen"):
				if trade_log:
					st.dataframe(pd.DataFrame(trade_log), use_container_width=True)
				else:
					st.info("Keine Trades in diesem Zeitraum ausgelöst.")