import streamlit as st
import QuantLib as ql
import numpy as np
import pandas as pd
import plotly.graph_objects as go

# ==========================================
# 1. Page Configuration
# ==========================================
st.set_page_config(page_title="Quant Portfolio Simulator", layout="wide")
st.title("Monte Carlo Portfolio Risk Simulator")
st.markdown("Simulate risk and returns for customized portfolios using QuantLib.")

# ==========================================
# 2. Sidebar: Asset Configuration & Inputs
# ==========================================
st.sidebar.header("1. Load Assets & Parameters")

# Asset A Configuration
st.sidebar.subheader("Asset A (e.g., AI/Tech)")
asset_a_name = st.sidebar.text_input("Name Asset A", value="SoftBank")
spot_a = st.sidebar.number_input("Initial Price A (€)", value=100.0, step=10.0)
vol_a = st.sidebar.slider("Volatility A (%)", 10, 100, 35) / 100.0

# Asset B Configuration
st.sidebar.subheader("Asset B (e.g., Energy/Utility)")
asset_b_name = st.sidebar.text_input("Name Asset B", value="Energy Provider")
spot_b = st.sidebar.number_input("Initial Price B (€)", value=100.0, step=10.0)
vol_b = st.sidebar.slider("Volatility B (%)", 10, 100, 20) / 100.0
div_b = st.sidebar.slider("Dividend Yield B (%)", 0.0, 10.0, 4.0) / 100.0

st.sidebar.header("2. Simulation Settings")
correlation_input = st.sidebar.slider("Correlation (A & B)", -1.0, 1.0, 0.3, 0.1)
duration_years = st.sidebar.slider("Time Horizon (Years)", 1, 10, 5)
num_paths = st.sidebar.selectbox("Number of Scenarios", [1000, 5000, 10000], index=2)


# ==========================================
# 3. Core QuantLib Simulation Function
# ==========================================
def run_simulation(spot_a, vol_a, spot_b, vol_b, div_b, correlation, years, paths):
	today = ql.Date(1, 6, 2026)
	ql.Settings.instance().evaluationDate = today
	day_count = ql.Actual365Fixed()
	calendar = ql.TARGET()
	risk_free_rate = 0.035

	def create_process(spot, vol, rate, div=0.0):
		spot_handle = ql.QuoteHandle(ql.SimpleQuote(spot))
		rate_handle = ql.YieldTermStructureHandle(ql.FlatForward(today, rate, day_count))
		div_handle = ql.YieldTermStructureHandle(ql.FlatForward(today, div, day_count))
		vol_handle = ql.BlackVolTermStructureHandle(ql.BlackConstantVol(today, calendar, vol, day_count))
		return ql.BlackScholesMertonProcess(spot_handle, div_handle, rate_handle, vol_handle)

	process_a = create_process(spot_a, vol_a, risk_free_rate, 0.0)
	process_b = create_process(spot_b, vol_b, risk_free_rate, div_b)

	matrix = ql.Matrix(2, 2)
	matrix[0][0], matrix[1][1] = 1.0, 1.0
	matrix[0][1], matrix[1][0] = correlation, correlation

	process_array = ql.StochasticProcessArray([process_a, process_b], matrix)

	steps = int(years * 12)  # Monthly steps
	time_grid = ql.TimeGrid(years, steps)
	rsg = ql.GaussianRandomSequenceGenerator(
		ql.UniformRandomSequenceGenerator(2 * steps, ql.UniformRandomGenerator(42))
	)
	path_generator = ql.GaussianMultiPathGenerator(process_array, time_grid, rsg, False)

	results = []
	visual_paths = []  # Store a subset for the line chart

	for i in range(paths):
		sample = path_generator.next()
		multi_path = sample.value()

		if i < 100:  # Only save first 100 full paths for visualization performance
			path_a = np.array([multi_path[0][j] for j in range(steps + 1)])
			path_b = np.array([multi_path[1][j] for j in range(steps + 1)])
			visual_paths.append(path_a + path_b)

		end_val_a = multi_path[0][steps]
		end_val_b = multi_path[1][steps]
		total_end_val = end_val_a + end_val_b

		results.append({
			"Scenario ID": i + 1,
			f"{asset_a_name} Final (€)": round(end_val_a, 2),
			f"{asset_b_name} Final (€)": round(end_val_b, 2),
			"Total Portfolio (€)": round(total_end_val, 2)
		})

	return pd.DataFrame(results), visual_paths, steps


# ==========================================
# 4. Main Execution & UI Output
# ==========================================
if st.sidebar.button("Run Simulation", type="primary"):
	with st.spinner('Running QuantLib Monte Carlo Simulation...'):
		df_results, visual_paths, steps = run_simulation(
			spot_a, vol_a, spot_b, vol_b, div_b, correlation_input, duration_years, num_paths
		)

		initial_portfolio = spot_a + spot_b
		portfolio_returns = (df_results["Total Portfolio (€)"] / initial_portfolio) - 1.0
		var_99 = np.percentile(portfolio_returns, 1) * 100
		mean_val = df_results["Total Portfolio (€)"].mean()

		# --- Dashboard Metrics ---
		col1, col2, col3 = st.columns(3)
		col1.metric("Initial Investment", f"€{initial_portfolio:.2f}")
		col2.metric("Expected Mean Value", f"€{mean_val:.2f}", f"{(mean_val / initial_portfolio - 1) * 100:.2f}%")
		col3.metric("99% Value at Risk (VaR)", f"{var_99:.2f}%", delta_color="inverse")

		# --- Interactive Plotly Chart ---
		st.subheader("Monte Carlo Path Simulation (100 Samples)")
		fig = go.Figure()
		time_axis = np.linspace(0, duration_years, steps + 1)

		for p in visual_paths:
			fig.add_trace(go.Scatter(x=time_axis, y=p, mode='lines', line=dict(width=1), opacity=0.3, showlegend=False))

		fig.add_hline(y=initial_portfolio, line_dash="dash", line_color="white", annotation_text="Initial Investment")
		fig.update_layout(xaxis_title="Years", yaxis_title="Portfolio Value (€)", height=500, template="plotly_dark")
		st.plotly_chart(fig, use_container_width=True)

		# --- Data Table & CSV Export ---
		st.subheader("Simulation Results Data")
		st.dataframe(df_results, use_container_width=True)

		csv_data = df_results.to_csv(index=False).encode('utf-8')
		st.download_button(
			label="Download Data as CSV",
			data=csv_data,
			file_name='monte_carlo_results.csv',
			mime='text/csv',
		)
else:
	st.info("Configure your assets in the sidebar and click 'Run Simulation' to start.")