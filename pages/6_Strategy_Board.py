import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import uuid
from datetime import datetime


# ==========================================
# 1. Page Configuration
# ==========================================
st.set_page_config(page_title="Strategy Whiteboard", layout="wide")
st.title("🧠 Strategy Planning Board")
st.markdown("The heart of your fund: Develop investment theses, allocate capital, and manage your alpha strategies.")

# ==========================================
# 2. Session State Initialization (Memory)
# ==========================================
# We use the session state as a temporary database for the whiteboard
if 'strategies' not in st.session_state:
	st.session_state.strategies = []

# ==========================================
# 3. Sidebar: Designing a New Strategy
# ==========================================
st.sidebar.header("Create new strategy")

with st.sidebar.form("new_strategy_form"):
	strat_name = st.text_input("Strategy name", placeholder="e.g. Asia/Semi Long Bias")
	strat_theme = st.selectbox("Asset Class / Focus", ["Equities (Tech)", "Equities (Macro)", "Fixed Income", "FX/Währungen", "Multi-Asset", "Arbitrage"])
	strat_tickers = st.text_input("Planned Instruments (Tickers)", placeholder="TSM, ASML, NVDA, JPY=X")
	strat_alloc = st.slider("Planned Fund Allocation (%)", 1, 100, 10)
	strat_thesis = st.text_area("Investment Thesis", placeholder="Why will this strategy generate alpha?")

	submitted = st.form_submit_button("Pin the strategy to the board 📌")

	if submitted and strat_name:
		new_strat = {
			"id": str(uuid.uuid4()[:8]),
			"date": datetime.now().strftime("%Y-%m-%d"),
			"name": strat_name,
			"theme": strat_theme,
			"tickers": [t.strip().upper() for t in strat_tickers.split(",") if t.strip()],
			"allocation": strat_alloc,
			"thesis": strat_thesis,
			"status": "In Planung 📝"
		}
		st.session_state.strategies.append(new_strat)
		st.toast("Strategy '{strat_name}' has been pinned to the board!")

# ==========================================
# 4. Top Section: Fund Allocation Visualization
# ==========================================
if st.session_state.strategies:
	st.subheader("Global Fund Allocation")

	# Calculate the total allocation
	total_allocated = sum(s['allocation'] for s in st.session_state.strategies)
	cash_drag = max(0, 100 - total_allocated)

	# Preparing data for the plot
	labels = [s['name'] for s in st.session_state.strategies] + ["Unallocated Cash"]
	values = [s['allocation'] for s in st.session_state.strategies] + [cash_drag]

	fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4, textinfo='label+percent',
	                             marker=dict(colors=['#00ccff', '#ff00ff', '#00ff00', '#ffff00', '#333333']))])
	fig.update_layout(template="plotly_dark", height=300, margin=dict(t=0, b=0, l=0, r=0))
	st.plotly_chart(fig, use_container_width=True)

	if total_allocated > 100:
		st.error(f"⚠️ Achtung: Dein Fonds ist mit {total_allocated}% überhebelt (Leveraged)!")

st.divider()

# ==========================================
# 5. Main Whiteboard: Strategy Cards (Kanban)
# ==========================================
st.subheader("📋 Active Strategy Board")


if not st.session_state.strategies:
	st.info("Your whiteboard is still blank. Use the sidebar to design your first investment strategy.")
else:
	cols = st.columns(3)

	for index, strat in enumerate(st.session_state.strategies):
		with cols[index % 3]:
			with st.container(border=True):
				st.markdown(f"### {strat['name']}")
				st.caption(f"ID: {strat['id']} | Erstellt: {strat['date']}")

				st.markdown(f"**Fokus:** `{strat['theme']}`")
				st.markdown(f"**Target Alloc:** `{strat['allocation']}%`")

			# Display instruments as small "tags"
			if strat['tickers']:
				st.markdown("**Assets:** " + " · ".join(f"*{t}*" for t in strat['tickers']))
			else:
				st.markdown("**Assets:** *Noch keine definiert*")

			# Thesis in a drop-down menu (so the page doesn't get too big)
			with st.expander("Read the Investment Thesis"):
				st.write(strat['thesis'] if strat['thesis'] else "No thesis has been submitted")

			st.divider()

		# Action Buttons for the Workflow
		b1, b2, b3 = st.columns(3)
		with b1:
			if st.button("📈 Sim", key=f"sim_{strat['id']}", help="Starte Monte Carlo für diese Assets"):
				st.toast("Würde jetzt die Simulation starten...")
			with b2:
				if st.button("📄 Report", key=f"rep_{strat['id']}"):
					st.toast("Generiere PDF Report...")
			with b3:
				if st.button("🗑️ Del", key=f"del_{strat['id']}", type="secondary"):
					# Lösche die Strategie und lade die Seite neu
					st.session_state.strategies = [s for s in st.session_state.strategies if s['id'] != strat['id']]
					st.rerun()

