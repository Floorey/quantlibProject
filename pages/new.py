import streamlit as st

# ==========================================
# Platzhalter-Variablen (falls nicht aus vorherigem Code vorhanden)
# ==========================================
# Diese Variablen sollten normalerweise aus Ihrem vollständigen Streamlit-Code kommen
interest_shock = 0.5  # Beispielwert
oil_shock = 10.0  # Beispielwert
weights = [0.4, 0.3, 0.3]  # Tech, Energy, Bonds
total_portfolio_value = 100000  # EUR
mean_val = 125000  # EUR
var_99 = -15.5  # Prozent

# ==========================================
# 5. Optional: AI Agent (Gemini Pro) Integration
# ==========================================
st.divider()
st.subheader("🤖 AI Quant Analyst (Powered by Gemini Pro)")
st.markdown("Enable the AI agent to interpret your simulation results and macro shocks.")

# User inputs their API key securely in the UI
gemini_api_key = st.text_input("Enter your Google Gemini API Key to activate", type="password")

if gemini_api_key:
    if st.button("Generate AI Risk Report"):
        try:
            import google.generativeai as genai
        except ImportError:
            st.error("❌ Die Bibliothek 'google-generativeai' ist nicht installiert. Bitte installieren Sie sie mit: pip install google-generativeai")
            st.stop()

        with st.spinner("Gemini Pro is analyzing the quantitative data..."):
            try:
                genai.configure(api_key=gemini_api_key)
                # Using the standard text model
                model = genai.GenerativeModel('gemini-pro')

                # We inject the hard data from QuantLib into the prompt
                ai_prompt = f"""
Act as an expert quantitative hedge fund manager. I have just run a Monte Carlo simulation.

Context & Macro Environment:
- Interest Rate Shock applied: {interest_shock}%
- Oil Price Shock applied: {oil_shock}%

Portfolio Allocation:
- Tech: {weights[0] * 100:.1f}%, Energy: {weights[1] * 100:.1f}%, Bonds: {weights[2] * 100:.1f}%

Simulation Results (5 Years, 10,000 paths):
- Initial Investment: {total_portfolio_value} EUR
- Expected Mean Value: {mean_val} EUR
- 99% Value at Risk (VaR): {var_99:.2f}%

Task:
Provide a concise, professional risk assessment of this portfolio. 
Explain WHY the specific macro shocks caused this specific VaR and Mean. 
Give one strategic recommendation on how to adjust the portfolio weights to reduce the VaR.
Keep the response professional, analytical, and under 250 words.
"""

                response = model.generate_content(ai_prompt)

                st.success("Analysis Complete")
                st.info(response.text)

            except Exception as e:
                st.error(f"API Error: {e}")