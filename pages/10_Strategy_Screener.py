import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import itertools
from statsmodels.tsa.stattools import coint

# ==========================================
# 1. Page Configuration
# ==========================================
st.set_page_config(page_title="Strategy Screener", layout="wide")
st.title("🔎 Universe Screener & Strategy Discovery")
st.markdown("Scanne ganze Sektoren oder Watchlists vollautomatisch nach versteckten Kointegrationen und Korrelationen.")

# ==========================================
# 2. Input: Das Anlage-Universum (mit Presets)
# ==========================================
st.header("1. Definiere dein Anlage-Universum")
st.markdown("Wähle einen Sektor aus den Vorlagen oder gib eine eigene Liste von Tickern ein.")

# Vordefinierte Watchlists (Presets)
presets = {
    "AI & Halbleiter": "MSFT, MU, NVDA, ORCL, TSM, INTC, AMD, QCOM",
    "Big Tech (FAANG+)": "AAPL, MSFT, GOOGL, AMZN, META, NFLX",
    "Krypto & Blockchain": "MSTR, COIN, MARA, RIOT, SQ, HOOD",
    "Energie & Öl": "XOM, CVX, COP, SLB, BP, SHEL",
    "Finanzen & Banken": "JPM, BAC, WFC, C, GS, MS",
    "Eigene Eingabe (Custom)": ""
}

col_preset, col_time = st.columns([2, 1])

with col_preset:
    # Dropdown-Menü für die Presets
    selected_preset = st.selectbox("Sektor-Vorlage wählen:", list(presets.keys()))

with col_time:
    timeframe = st.selectbox("Historie für den Scan", ["1y", "2y", "5y"], index=1)

# Das Textfeld übernimmt automatisch den Text aus dem Dropdown
tickers_input = st.text_input("Ticker-Universum bearbeiten (kommasepariert):", value=presets[selected_preset])

if st.button("Universum scannen & Paare finden", type="primary"):
    ticker_list = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

    if len(ticker_list) < 2:
        st.error("Du brauchst mindestens 2 Ticker für einen Paar-Vergleich.")
    else:
        with st.spinner(
                f"Lade Daten für {len(ticker_list)} Assets und berechne {len(ticker_list) * (len(ticker_list) - 1) // 2} Kombinationen..."):

            # Daten laden
            data = yf.download(ticker_list, period=timeframe)['Close']
            data = data.dropna()

            if data.empty:
                st.error("Keine Daten gefunden. Prüfe die Ticker.")
            else:
                # ==========================================
                # 3. Korrelations-Matrix (Heatmap)
                # ==========================================
                st.divider()
                st.header("2. Sektor-Korrelation (Renditen)")

                # Für Korrelation nehmen wir tägliche prozentuale Renditen
                returns = data.pct_change().dropna()
                corr_matrix = returns.corr()

                fig_corr = px.imshow(
                    corr_matrix,
                    text_auto=".2f",
                    color_continuous_scale="RdBu_r",
                    zmin=-1, zmax=1,
                    template="plotly_dark",
                    title="Pearson Korrelations-Heatmap"
                )
                fig_corr.update_layout(height=500)
                st.plotly_chart(fig_corr, use_container_width=True)

                # ==========================================
                # 4. Kointegrations-Scanner (Mean Reversion)
                # ==========================================
                st.divider()
                st.header("3. Kointegrations-Scanner (Die besten Paare)")
                st.markdown("Welche Aktien laufen an der Leine? (P-Value < 0.05 ist ein Treffer)")

                coint_results = []
                # itertools.combinations generiert alle einzigartigen Paare
                pairs = list(itertools.combinations(data.columns, 2))

                # Ladebalken für die Schleife
                progress_bar = st.progress(0)

                for i, (t1, t2) in enumerate(pairs):
                    # Engle-Granger Test
                    score, p_value, _ = coint(data[t1], data[t2])

                    # Umgedrehter Test (Manchmal ist A -> B anders als B -> A)
                    score_rev, p_value_rev, _ = coint(data[t2], data[t1])

                    # Nimm den besseren (niedrigeren) P-Value
                    best_p = min(p_value, p_value_rev)

                    coint_results.append({
                        "Asset 1": t1,
                        "Asset 2": t2,
                        "P-Value": round(best_p, 4),
                        "Cointegrated": "✅ Ja" if best_p < 0.05 else "❌ Nein"
                    })

                    progress_bar.progress((i + 1) / len(pairs))

                progress_bar.empty()

                # Ergebnisse in einen DataFrame packen und nach P-Value sortieren
                df_coint = pd.DataFrame(coint_results)
                df_coint = df_coint.sort_values("P-Value")

                # Zeige die Top Ergebnisse (Hier ist das korrigierte .map)
                st.dataframe(
                    df_coint.style.map(
                        lambda x: 'background-color: rgba(0, 255, 0, 0.2)' if x == '✅ Ja' else '',
                        subset=['Cointegrated']
                    ),
                    use_container_width=True,
                    hide_index=True
                )

                # Automatisches Fazit
                valid_pairs = df_coint[df_coint["P-Value"] < 0.05]
                if not valid_pairs.empty:
                    best_pair = valid_pairs.iloc[0]
                    st.success(
                        f"🎯 **Scanner-Ergebnis:** Wir haben {len(valid_pairs)} kointegrierte Paare gefunden! Das absolut beste Setup für Pairs Trading ist aktuell **{best_pair['Asset 1']} vs. {best_pair['Asset 2']}** (P-Value: {best_pair['P-Value']:.4f}).")
                    st.info(
                        "👉 **Nächster Schritt:** Gehe jetzt in dein Tool **'9_Pairs_Trading.py'**, gib dieses Paar ein und suche nach dem optimalen Z-Score Einstieg!")
                else:
                    st.warning(
                        "Keine kointegrierten Paare in diesem Universum gefunden. Probier andere Ticker oder einen anderen Zeitraum.")