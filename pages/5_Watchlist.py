import streamlit as st
import sqlite3
import pandas as pd
import yfinance as yf
from datetime import datetime

# ==========================================
# 1. Page Configuration
# ==========================================
st.set_page_config(page_title="Watchlist & DB", layout="wide")
st.title("📌 Live Watchlist")
st.markdown("Deine persönliche Watchlist. Die Ticker werden persistent in einer lokalen SQLite-Datenbank gespeichert.")

# ==========================================
# 2. Datenbank Setup (SQLite)
# ==========================================
# Verbinde dich mit der DB (die Datei 'quant_data.db' wird erstellt, falls sie nicht existiert)
# check_same_thread=False ist wichtig, da Streamlit im Hintergrund mit Threads arbeitet
conn = sqlite3.connect('quant_data.db', check_same_thread=False)
c = conn.cursor()

# Tabelle erstellen, falls sie noch nicht existiert
c.execute('''
    CREATE TABLE IF NOT EXISTS watchlist (
        ticker TEXT PRIMARY KEY,
        added_date TEXT
    )
''')
conn.commit()


# ==========================================
# 3. Hilfsfunktionen für die Datenbank
# ==========================================
def add_ticker(ticker):
	ticker = ticker.upper().strip()
	if ticker:
		try:
			# Versuche, den Ticker über Yahoo Finance zu verifizieren
			test = yf.Ticker(ticker).history(period="1d")
			if test.empty:
				st.error(f"❌ Ticker '{ticker}' nicht gefunden (Yahoo Finance).")
				return

			# In die Datenbank schreiben
			now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
			c.execute('INSERT INTO watchlist (ticker, added_date) VALUES (?, ?)', (ticker, now))
			conn.commit()
			st.success(f"✅ {ticker} zur Watchlist hinzugefügt!")
		except sqlite3.IntegrityError:
			st.warning(f"⚠️ {ticker} ist bereits auf deiner Watchlist.")
		except Exception as e:
			st.error(f"Ein Fehler ist aufgetreten: {e}")


def delete_ticker(ticker):
	c.execute('DELETE FROM watchlist WHERE ticker = ?', (ticker,))
	conn.commit()
	st.success(f"🗑️ {ticker} wurde entfernt.")


def get_all_tickers():
	c.execute('SELECT ticker FROM watchlist')
	return [row[0] for row in c.fetchall()]


# ==========================================
# 4. Sidebar: Verwaltung der Watchlist
# ==========================================
st.sidebar.header("Watchlist verwalten")

# Ticker hinzufügen
new_ticker = st.sidebar.text_input("Neuen Ticker hinzufügen (z.B. MSFT, TSLA):")
if st.sidebar.button("➕ Hinzufügen", type="primary"):
	add_ticker(new_ticker)

st.sidebar.divider()

# Ticker löschen
saved_tickers = get_all_tickers()
if saved_tickers:
	ticker_to_delete = st.sidebar.selectbox("Ticker zum Löschen auswählen:", saved_tickers)
	if st.sidebar.button("❌ Entfernen"):
		delete_ticker(ticker_to_delete)
		st.rerun()  # Aktualisiert die Seite sofort nach dem Löschen

# ==========================================
# 5. Main UI: Live-Daten laden & anzeigen
# ==========================================
if not saved_tickers:
	st.info("Deine Watchlist ist noch leer. Füge links über die Sidebar Ticker hinzu!")
else:
	st.header("📊 Aktuelle Marktdaten")

	# Einen "Refresh"-Button für manuelle Updates
	if st.button("🔄 Kurse aktualisieren"):
		st.toast("Lade frische Daten von Yahoo Finance...")

	# CSS Grid via Streamlit Columns
	cols = st.columns(4)

	# Wir iterieren durch alle gespeicherten Ticker
	for i, ticker in enumerate(saved_tickers):
		with cols[i % 4]:  # Verteilt die Metriken gleichmäßig auf 4 Spalten
			try:
				# Hole die letzten 2 Tage, um die Veränderung zu berechnen
				df = yf.Ticker(ticker).history(period="2d")
				if len(df) >= 2:
					current_price = df['Close'].iloc[-1]
					prev_price = df['Close'].iloc[-2]
					pct_change = ((current_price / prev_price) - 1) * 100
					abs_change = current_price - prev_price

					st.metric(
						label=ticker,
						value=f"${current_price:.2f}",
						delta=f"${abs_change:.2f} ({pct_change:.2f}%)"
					)
				elif len(df) == 1:
					# Fallback, falls nur ein Tag verfügbar ist
					current_price = df['Close'].iloc[0]
					st.metric(label=ticker, value=f"${current_price:.2f}")
				else:
					st.metric(label=ticker, value="Keine Daten")
			except Exception:
				st.metric(label=ticker, value="API Fehler")