import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
from transformers import pipeline
import logging

# Unterdrücke die nervigen Info- und Warnmeldungen von Hugging Face
logging.getLogger("transformers").setLevel(logging.ERROR)

# ==========================================
# 1. Page Configuration
# ==========================================
st.set_page_config(page_title="AI Sentiment Analysis", layout="wide")
st.title("🧠 AI News Sentiment (FinBERT)")
st.markdown(
	"Analysiere die Marktpsychologie in Echtzeit. Das FinBERT-Modell liest aktuelle Nachrichten und berechnet den Panik/Gier-Faktor.")


# ==========================================
# 2. KI Modell laden (Cached)
# ==========================================
# @st.cache_resource sorgt dafür, dass das Modell nur beim ersten Start geladen wird
@st.cache_resource
def load_sentiment_model():
	# Lädt das vortrainierte FinBERT Modell für Sentiment-Analyse
	return pipeline("sentiment-analysis", model="ProsusAI/finbert")


# ==========================================
# 3. Input & Parameter
# ==========================================
st.header("1. Asset auswählen")
ticker_input = st.text_input("Ticker-Symbol (z.B. AAPL, TSLA, NVDA)", value="TSLA").upper()
max_news = st.slider("Anzahl der zu analysierenden Nachrichten", min_value=5, max_value=20, value=10)

# Hier darf es nur EINEN Button mit diesem Namen geben!
if st.button("Live-Nachrichten mit KI analysieren", type="primary"):
	with st.spinner("Lade FinBERT KI-Modell und ziehe Live-News..."):

		try:
			# KI laden
			analyzer = load_sentiment_model()

			# News von Yahoo Finance ziehen
			stock = yf.Ticker(ticker_input)
			news_data = stock.news

			if not news_data:
				st.warning(f"Keine aktuellen Nachrichten für {ticker_input} gefunden.")
			else:
				# Wir begrenzen auf die ausgewählte Anzahl
				news_subset = news_data[:max_news]

				results = []
				# ==========================================
				# 4. NLP Pipeline ausführen (ROBUST)
				# ==========================================
				for item in news_subset:
					# Robustes Extrahieren: Prüft verschiedene Yahoo-Strukturen
					headline = item.get('title') or item.get('content', {}).get('title')
					link = item.get('link') or item.get('content', {}).get('clickThroughUrl') or ""

					# Falls Yahoo einen komplett leeren Datensatz schickt, überspringen wir ihn
					if not headline:
						continue

					# Die KI bewertet die Headline
					ai_result = analyzer(headline)[0]
					label = ai_result['label']  # 'positive', 'negative' oder 'neutral'
					score = ai_result['score']  # Konfidenz der KI (0 bis 1)

					# Sentiment-Score numerisch mappen (-1 bis +1)
					if label == "positive":
						numeric_score = score
					elif label == "negative":
						numeric_score = -score
					else:
						numeric_score = 0.0

					results.append({
						"Headline": headline,
						"Sentiment": label.upper(),
						"Confidence": score,
						"Numeric Score": numeric_score,
						"Link": link
					})

				if not results:
					st.error(
						"Nachrichtenstruktur von Yahoo Finance konnte nicht verarbeitet werden. Bitte anderen Ticker probieren.")
				else:
					df_results = pd.DataFrame(results)

					# Wandelt alle Einträge in der Spalte 'Link' in Strings um
					df_results['Link'] = df_results['Link'].astype(str)

					# ==========================================
					# 5. Sentiment Dashboard & KPIs
					# ==========================================
					st.divider()
					st.header(f"2. Sentiment-Dashboard für {ticker_input}")

					# Gesamt-Score berechnen (Durchschnitt)
					avg_sentiment = df_results['Numeric Score'].mean()

					# Kategorisierung des Gesamt-Scores
					if avg_sentiment > 0.2:
						mood = "🟢 Bullish (Gier)"
						delta_color = "normal"
					elif avg_sentiment < -0.2:
						mood = "🔴 Bearish (Panik)"
						delta_color = "inverse"
					else:
						mood = "⚪ Neutral (Unsicher)"
						delta_color = "off"

					c1, c2, c3 = st.columns(3)
					c1.metric("Gesamt-Sentiment Score", f"{avg_sentiment:.2f}", mood, delta_color=delta_color)
					c2.metric("Positive Nachrichten", len(df_results[df_results['Sentiment'] == 'POSITIVE']))
					c3.metric("Negative Nachrichten", len(df_results[df_results['Sentiment'] == 'NEGATIVE']))

					# ==========================================
					# 6. Visualisierung: Verteilung
					# ==========================================
					fig = px.pie(
						df_results,
						names='Sentiment',
						title="News Sentiment Verteilung",
						color='Sentiment',
						color_discrete_map={'POSITIVE': 'green', 'NEGATIVE': 'red', 'NEUTRAL': 'gray'},
						hole=0.4
					)
					fig.update_layout(template="plotly_dark", height=400)
					st.plotly_chart(fig, use_container_width=True)

					# ==========================================
					# 7. Detaillierte Nachrichten-Tabelle
					# ==========================================
					st.subheader("Rohdaten: KI-Analyse der Schlagzeilen")


					# Einfaches Farbsystem für den DataFrame
					def color_sentiment(val):
						color = 'red' if val == 'NEGATIVE' else 'green' if val == 'POSITIVE' else 'gray'
						return f'color: {color}'


					# Zeigt den DataFrame an (und nutzt das neue Argument für die Breite)
					st.dataframe(
						df_results[['Headline', 'Sentiment', 'Confidence', 'Link']].style.map(color_sentiment,
						                                                                      subset=['Sentiment']),
						use_container_width=True
					)

		except Exception as e:
			st.error(f"Fehler bei der KI-Analyse. Details: {e}")