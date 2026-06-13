import streamlit as st
import plotly.graph_objects as go
import numpy as np

# ==========================================
# 1. Page Config
# ==========================================
st.set_page_config(page_title="CFD Cost Analyzer", layout="wide")
st.title("🔎 CFD Cost Analyzer & Break-Even Rechner")
st.markdown(
	"Berechnet die versteckten Haltekosten (Swaps) und den tatsächlichen Break-Even-Point bei CFDs. Entlarvt den 'Cost Drag' über die Zeit.")

# ==========================================
# 2. Input & Parameter
# ==========================================
st.header("1. Trade-Details eingeben")

col1, col2, col3, col4 = st.columns(4)

with col1:
	direction = st.selectbox("Richtung", ["LONG (Kaufen)", "SHORT (Verkaufen)"])
	asset_price = st.number_input("Aktueller Kurs ($)", value=150.0, step=1.0)

with col2:
	position_size = st.number_input("Anzahl CFDs (Stück)", value=100, step=10)
	leverage = st.selectbox("Hebel (Leverage)", [1, 2, 5, 10, 20, 30], index=2,
	                        help="Bsp: Hebel 5 bedeutet 20% Margin-Anforderung.")

with col3:
	spread = st.number_input("Spread pro CFD ($)", value=0.05, step=0.01, format="%.3f")
	holding_days = st.number_input("Geplante Haltedauer (Tage)", value=14, step=1)

with col4:
	st.markdown("**Finanzierungskosten p.a.**")
	base_rate = st.number_input("Basis-Zins (z.B. SOFR) %", value=5.3, step=0.1)
	broker_markup = st.number_input("Broker Aufschlag %", value=2.5, step=0.1)

st.divider()

# ==========================================
# 3. Die harte Mathematik (Kostenberechnung)
# ==========================================
# 1. Position & Margin
total_exposure = asset_price * position_size
margin_required = total_exposure / leverage

# 2. Spread (Einmalige Kosten beim Öffnen UND Schließen - wir nehmen hier vereinfacht den Spread beim Öffnen als Gesamtkosten an)
spread_cost = spread * position_size

# 3. Finanzierungskosten (Overnight Swaps)
# Long: Du zahlst (Basis + Markup). Short: Du bekommst Basis, zahlst aber Markup (oft negativ unterm Strich)
if "LONG" in direction:
	annual_rate = (base_rate + broker_markup) / 100
else:
	annual_rate = (broker_markup - base_rate) / 100  # Short-Rate ist oft (Markup - Base) oder ähnliches, je nach Broker

# Tägliche Kosten (Total Exposure wird finanziert, nicht nur die Margin!)
daily_swap_cost = (total_exposure * annual_rate) / 365
total_swap_cost = daily_swap_cost * holding_days

# 4. Gesamtkosten & Break-Even
total_costs = spread_cost + total_swap_cost
break_even_move = total_costs / position_size
break_even_pct = (break_even_move / asset_price) * 100

# ==========================================
# 4. Analyse & Dashboard
# ==========================================
st.header("2. Kostenanalyse & Break-Even")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Bewegtes Volumen (Exposure)", f"${total_exposure:,.2f}")
c2.metric("Eingesetzte Margin (Dein Geld)", f"${margin_required:,.2f}")
c3.metric("Feste Spread-Kosten", f"${spread_cost:.2f}")
c4.metric(f"Swap-Kosten ({holding_days} Tage)", f"${total_swap_cost:.2f}", f"${daily_swap_cost:.2f} / Tag",
          delta_color="inverse")

st.markdown("### 🎯 Die Break-Even Hürde")
st.info(
	f"Damit dieser Trade auf **Null** herauskommt (ohne 1 Cent Gewinn), muss sich die Aktie in den nächsten {holding_days} Tagen um **${break_even_move:.3f} ({break_even_pct:.2f}%)** in deine Richtung bewegen. Alles darunter ist ein Verlust durch Broker-Gebühren.")

# Warnsystem für Margin-Erosion
cost_to_margin_ratio = (total_costs / margin_required) * 100
if cost_to_margin_ratio > 10:
	st.error(
		f"⚠️ **Achtung:** Die simulierten Haltekosten fressen bereits **{cost_to_margin_ratio:.1f}%** deiner eingesetzten Margin auf. CFDs sind für diese Haltedauer ineffizient.")
elif cost_to_margin_ratio > 5:
	st.warning(
		f"⚡ Die Kosten belaufen sich auf **{cost_to_margin_ratio:.1f}%** deiner Margin. Behalte das Zeitlimit im Auge.")

# ==========================================
# 5. Visualisierung: Der "Cost Drag" über die Zeit
# ==========================================
st.subheader("Zeitverlauf der Gebühren (Cost Drag)")

# Wir berechnen die kumulierten Kosten für jeden Tag
days_array = np.arange(1, holding_days + 2)
accumulated_costs = spread_cost + (daily_swap_cost * days_array)

fig = go.Figure()

# Kostenkurve
fig.add_trace(go.Bar(
	x=days_array,
	y=accumulated_costs,
	name="Kumulierte Kosten ($)",
	marker_color='rgba(255, 50, 50, 0.7)'
))

# Referenzlinie: Spread-Kosten (Tag 1)
fig.add_hline(y=spread_cost, line_dash="dash", line_color="white", annotation_text="Initialer Spread")

fig.update_layout(
	title=f"Kapitalverzehr durch CFD-Gebühren über {holding_days} Tage",
	xaxis_title="Haltedauer (Tage)",
	yaxis_title="Gesamtkosten in $",
	template="plotly_dark",
	hovermode="x unified"
)

# Nutze width='stretch' wie in der Warnung angemerkt, oder verzichte auf kwargs.
st.plotly_chart(fig)