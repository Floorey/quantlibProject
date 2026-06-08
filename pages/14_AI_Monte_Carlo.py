import streamlit as st
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="AI-Driven Monte Carlo", layout="wide")
st.title("🎲 AI-Adjusted Monte Carlo Simulation")
st.markdown("Verbindet Geometrische Brownsche Bewegung mit Echtzeit-KI-Sentiment zur dynamischen Risikoanpassung.")

# ==========================================
# 1. Globale Daten abrufen (Session State)
# ==========================================
# Prüfen, ob die KI vorher schon etwas analysiert hat
ai_ticker = st.session_state.get('ai_ticker', 'Asset')
ai_score = st.session_state.get('ai_sentiment_score', 0.0)

st.header(f"Simulation für: {ai_ticker}")

if ai_score == 0.0:
	st.warning(
		"Kein aktuelles KI-Sentiment gefunden. Die Simulation läuft im neutralen Standard-Modus. Nutze das Modul '13 AI Sentiment', um Live-Daten zu laden.")
else:
	st.success(f"Aktives KI-Sentiment erkannt: **{ai_score:.2f}**")

# ==========================================
# 2. Parameter-Setup
# ==========================================
col1, col2, col3 = st.columns(3)

with col1:
	S0 = st.number_input("Aktueller Preis ($)", value=100.0, step=1.0)
	days = st.number_input("Simulationszeitraum (Tage)", value=90, step=1)
	simulations = st.number_input("Anzahl der Pfade", value=100, step=10)

with col2:
	st.markdown("**Basis-Annahmen (Ohne KI)**")
	base_mu = st.number_input("Erwartete Rendite p.a. (%)", value=10.0, step=1.0) / 100
	base_vol = st.number_input("Historische Volatilität p.a. (%)", value=20.0, step=1.0) / 100

with col3:
	st.markdown("**KI-Sensitivität (Wie stark reagiert das Modell?)**")
	drift_sens = st.slider("Drift-Sensitivität (Richtung)", min_value=0.0, max_value=0.5, value=0.15)
	vol_sens = st.slider("Volatilitäts-Sensitivität (Panik/Gier)", min_value=0.0, max_value=1.0, value=0.50)

# ==========================================
# 3. Die Quant-Mathematik (KI-Fusion)
# ==========================================
# Tägliche Umrechnung
dt = 1 / 252

# Schritt 1: Drift (Richtung) anpassen
# Ein positives Sentiment schiebt die Renditeerwartung hoch
adj_mu = base_mu + (ai_score * drift_sens)

# Schritt 2: Volatilität (Risiko) anpassen
# JEDES starke Sentiment (egal ob extreme Panik oder extremer Hype) erhöht die Unsicherheit/Volatilität
adj_vol = base_vol * (1 + abs(ai_score) * vol_sens)

# Tägliche Parameter
daily_mu = adj_mu * dt
daily_vol = adj_vol * np.sqrt(dt)

st.divider()

# Dashboard für die veränderten Metriken
c1, c2 = st.columns(2)
c1.metric("Angepasste Erwartete Rendite p.a.", f"{adj_mu * 100:.2f}%", f"{(adj_mu - base_mu) * 100:.2f}% durch KI")
c2.metric("Angepasste Volatilität p.a.", f"{adj_vol * 100:.2f}%", f"{(adj_vol - base_vol) * 100:.2f}% durch KI",
          delta_color="inverse")

if st.button("Simulation Starten", type="primary"):
	with st.spinner("Berechne stochastische Pfade..."):

		# Matrix für die Preise erstellen (Zeilen = Tage, Spalten = Pfade)
		price_matrix = np.zeros((days, simulations))
		price_matrix[0] = S0

		# Geometrische Brownsche Bewegung (vektorisiert für Geschwindigkeit)
		for t in range(1, days):
			# Zufallsschock (Z ~ N(0,1))
			Z = np.random.standard_normal(simulations)
			# GBM Formel: S_t = S_{t-1} * exp((mu - 0.5 * sigma^2)*dt + sigma * sqrt(dt) * Z)
			price_matrix[t] = price_matrix[t - 1] * np.exp((daily_mu - 0.5 * daily_vol ** 2) + daily_vol * Z)

		# ==========================================
		# 4. Visualisierung
		# ==========================================
		fig = go.Figure()

		# Alle Pfade zeichnen (leicht transparent)
		for i in range(simulations):
			fig.add_trace(go.Scatter(x=np.arange(days), y=price_matrix[:, i], mode='lines', opacity=0.1,
			                         line=dict(color='#00ccff'), showlegend=False))

		# Median-Pfad zeichnen
		median_path = np.median(price_matrix, axis=1)
		fig.add_trace(go.Scatter(x=np.arange(days), y=median_path, mode='lines', name='Median Pfad',
		                         line=dict(color='yellow', width=3)))

		fig.update_layout(title=f"{days}-Tage Projektion für {ai_ticker} (KI-Adjustiert)", xaxis_title="Handelstage",
		                  yaxis_title="Preis in $", template="plotly_dark", height=600)
		st.plotly_chart(fig, use_container_width=True)