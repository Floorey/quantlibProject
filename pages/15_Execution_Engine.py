import streamlit as st
import os
import pandas as pd
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

# ==========================================
# 1. Page Config & API Setup
# ==========================================
st.set_page_config(page_title="Execution Engine", layout="wide")
st.title("⚡ Execution Engine (Paper Trading)")
st.markdown(
	"Direkte Anbindung an den Alpaca Broker. Alle Orders werden live mit Marktdaten, aber virtuellem Kapital ausgeführt.")

# Lade die Umgebungsvariablen aus der .env Datei
load_dotenv()
API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")


# ==========================================
# 2. Broker Verbindung herstellen
# ==========================================
@st.cache_resource
def get_trading_client():
	if not API_KEY or not SECRET_KEY:
		return None
	# paper=True ist extrem wichtig!
	return TradingClient(API_KEY, SECRET_KEY, paper=True)


client = get_trading_client()

if not client:
	st.error("🚨 API Keys nicht gefunden! Bitte überprüfe deine .env Datei.")
	st.stop()

try:
	# Account-Daten abrufen
	account = client.get_account()

	# ==========================================
	# 3. Portfolio Dashboard
	# ==========================================
	st.header("1. Portfolio Übersicht")

	# Werte formatieren
	equity = float(account.equity)
	buying_power = float(account.buying_power)
	initial_margin = float(account.initial_margin)

	c1, c2, c3 = st.columns(3)
	c1.metric("Gesamtwert (Equity)", f"${equity:,.2f}")
	c2.metric("Kaufkraft (Buying Power)", f"${buying_power:,.2f}")

	# Wenn wir unter 100k fallen, ist es ein Verlust, sonst Gewinn (Annahme: 100k Startkapital)
	pnl = equity - 100000.0
	c3.metric("Profit & Loss (seit Start)", f"${pnl:,.2f}", f"{(pnl / 100000) * 100:.2f}%")

	st.divider()

	# ==========================================
	# 4. Order Terminal (Mission Control)
	# ==========================================
	st.header("2. Manuelles Order Terminal")

	with st.form("order_form"):
		col1, col2, col3 = st.columns(3)
		with col1:
			symbol = st.text_input("Ticker Symbol", value="AAPL").upper()
		with col2:
			qty = st.number_input("Anzahl (Shares)", min_value=1, value=10)
		with col3:
			side = st.selectbox("Aktion", ["KAUFEN (Long)", "VERKAUFEN (Short)"])

		submit_order = st.form_submit_button("🚀 Market Order ausführen", type="primary")

		if submit_order:
			with st.spinner(f"Sende Order für {qty}x {symbol} an Alpaca..."):
				try:
					# Order parametrisieren
					order_side = OrderSide.BUY if "KAUFEN" in side else OrderSide.SELL

					market_order_data = MarketOrderRequest(
						symbol=symbol,
						qty=qty,
						side=order_side,
						time_in_force=TimeInForce.GTC  # Good Till Cancelled
					)

					# Order abschicken
					order = client.submit_order(order_data=market_order_data)
					st.success(f"Erfolg! Order-ID: {order.id}. Status: {order.status.name}")

				except Exception as e:
					st.error(f"Order fehlgeschlagen: {e}")

	st.divider()

	# ==========================================
	# 5. Offene Positionen (Inventar)
	# ==========================================
	st.header("3. Aktuelle Positionen")
	positions = client.get_all_positions()

	if not positions:
		st.info("Keine offenen Positionen. Dein Portfolio ist flach.")
	else:
		pos_data = []
		for p in positions:
			pos_data.append({
				"Symbol": p.symbol,
				"Anzahl": p.qty,
				"Einstiegspreis": f"${float(p.avg_entry_price):.2f}",
				"Aktueller Preis": f"${float(p.current_price):.2f}",
				"Unrealisierter PnL": float(p.unrealized_pl),
				"PnL %": f"{float(p.unrealized_plpc) * 100:.2f}%"
			})

		df_pos = pd.DataFrame(pos_data)


		# PnL farblich markieren
		def color_pnl(val):
			color = 'green' if val > 0 else 'red' if val < 0 else 'gray'
			return f'color: {color}'


		st.dataframe(df_pos.style.map(color_pnl, subset=['Unrealisierter PnL']), use_container_width=True)

except Exception as e:
	st.error(f"Fehler bei der Verbindung zu Alpaca: {e}")