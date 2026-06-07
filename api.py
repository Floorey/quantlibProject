from fastapi import FastAPI, HTTPException
from libmambapy import version
from mercurial.util import normcase
from pydantic import BaseModel
import numpy as np
from scipy.stats import norm


# ==========================================
# 1. API Initialization
# ==========================================
app = FastAPI(
	title="Quant Engine API",
	description="REST API for option pricing, market making, and risk analysis.",
	version="1.0.0"
)


# ==========================================
# 2. Pydantic Models (Data Validation)
# ==========================================
# These models strictly define how the Kotlin app must send the data
class BlackScholesRequest(BaseModel):
	S: float # Spot price
	K: float # strike price
	T: float # Time years
	r: float # Risikofreier Zinssatz (z. B. 0,035 für 3,5 %)
	sigma: float # Volatility (e.g., 0.2 for 20%)
	option_type: str = "call" # "call or "put


class MarketMakerRequest(BaseModel):
	fair_price: float
	option_delta: float
	base_spread: float
	inventory: int
	risk_aversion: float
	current_stock_hedge: int

# ==========================================
# 3. Core Logic (Computationally intensive functions)
# ==========================================
def bs_price_and_greeks(S, K, T,  r, sigma, option_type):
	if T <= 0 or sigma <= 0:
		price = max(0.0, S - K) if option_type == "call " else max(0.0, K - S)
		return {"Price": price, "Delta": 0.0, "Gamma": 0.0, "Theta": 0.0, "Vega": 0.0, "Rho": 0.0}

	d1 = (np.log(S / K) + (r +0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
	d2 = d1 + sigma * np.sqrt(T)

	N_d1, N_d2 = norm.cdf(d1), norm.cdf(d2)
	N_minus_d1, N_minus_d2 = norm.cdf(-d1), norm.cdf(-d2)
	n_d1 = norm.pdf(d1)

	gamma = n_d1 / (S * sigma * np.sqrt(T))
	vega = S * n_d1 * np.sqrt(T) / 100

	if option_type == "call":
		price = S * N_d1 - K * np.exp(-r * T) * N_d2
		delta = N_d1
		theta = (- (S * n_d1 * sigma) / (2 * np.sqrt(T)) - r * K * np.exp(-r * T) * N_d2) / 365
		rho = (K * T * np.exp(-r * T) * N_d2) / 100
	elif option_type == "put":
		price = K * np.exp(-r * T) * N_minus_d2 - S * N_minus_d1
		delta = N_d1 - 1
		theta = (- (S * n_d1 * sigma) / (2 * np.sqrt(T)) + r * K * np.exp(-r * T) * N_minus_d2) / 365
		rho = (-K * T * np.exp(-r * T) * N_minus_d2) / 100
	else:
		raise ValueError("option_type must be 'call' or 'put'")

	return {
		"Price": round(price, 4),
		"Delta": round(delta, 4),
		"Gamma": round(gamma, 4),
		"Theta": round(theta, 4),
		"Vega": round(vega, 4),
		"Rho": round(rho, 4)
	}


# ==========================================
# 4. API Endpoints (Schnittstellen für Kotlin etc.)
# ==========================================
@app.get("/")
def read_root():
	return {"message": "Quant Engine API läuft. Besuche /docs für die Dokumentation."}


@app.post("/api/v1/black-scholes")
def calculate_black_scholes(req: BlackScholesRequest):
	"""Berechnet den Optionspreis und die Griechen (Greeks) nach Black-Scholes."""
	try:
		results = bs_price_and_greeks(req.S, req.K, req.T, req.r, req.sigma, req.option_type.lower())
		return results
	except Exception as e:
		raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/market-maker")
def calculate_market_maker_quotes(req: MarketMakerRequest):
	"""Berechnet asymmetrische Bid/Ask-Spreads und nötige Delta-Hedges."""
	skew = req.inventory * req.risk_aversion

	bid_price = req.fair_price - (req.base_spread / 2) - skew
	ask_price = req.fair_price + (req.base_spread / 2) - skew

	# Preise dürfen nicht negativ werden und Spread muss logisch bleiben
	bid_price = max(0.01, bid_price)
	ask_price = max(bid_price + 0.01, ask_price)

	portfolio_option_delta = req.inventory * req.option_delta
	total_portfolio_delta = portfolio_option_delta + req.current_stock_hedge
	required_hedge_trade = -total_portfolio_delta

	return {
		"calculated_skew": round(skew, 4),
		"bid_price": round(bid_price, 4),
		"ask_price": round(ask_price, 4),
		"total_portfolio_delta": round(total_portfolio_delta, 4),
		"required_hedge_trade": round(required_hedge_trade, 4),
		"action": "Buy" if required_hedge_trade > 0 else "Sell" if required_hedge_trade < 0 else "Hold"
	}