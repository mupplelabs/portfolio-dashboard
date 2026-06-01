import streamlit as st
import pandas as pd
import plotly.express as px
from utils import calculate_backtest

def render():
    st.title("📈 Backtesting Modul")
    st.markdown("Simuliere, wie sich dein aktuelles Portfolio in der Vergangenheit geschlagen hätte. **Buy & Hold Ansatz:** Wir nehmen deine *aktuelle prozentuale Allokation* und investieren virtuell dein gewähltes Startkapital am Anfang des Zeitraums.")
    
    if st.session_state.portfolio_df.empty:
        st.info("Dein Portfolio ist leer. Füge zunächst im Dashboard Positionen hinzu.")
        return
        
    st.divider()
    
    # 1. Konfiguration
    st.subheader("⚙️ Konfiguration")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        startkapital = st.number_input("Fiktives Startkapital (€)", min_value=100.0, value=10000.0, step=1000.0)
        
    with col2:
        period = st.selectbox(
            "Zeitraum",
            options=["1 Jahr", "3 Jahre", "5 Jahre", "10 Jahre", "Maximal"],
            index=2 # Default: 5 Jahre
        )
        
    with col3:
        benchmark_name = st.selectbox(
            "Benchmark (Vergleich)",
            options=["S&P 500", "MSCI World (iShares Core)", "Nasdaq 100", "Kein Vergleich"],
            index=0
        )
        
    # Mapping Benchmark Name -> Ticker
    benchmark_map = {
        "S&P 500": "^GSPC",
        "MSCI World (iShares Core)": "EUNL.DE",
        "Nasdaq 100": "^NDX",
        "Kein Vergleich": None
    }
    benchmark_ticker = benchmark_map[benchmark_name]
    
    if st.button("🚀 Simulation starten", type="primary"):
        with st.spinner(f"Simuliere Portfolio über {period} und lade Benchmark-Daten..."):
            pf_series, bm_series, pf_dd, bm_dd = calculate_backtest(
                st.session_state.portfolio_df, 
                startkapital, 
                period, 
                benchmark_ticker
            )
            
        if pf_series.empty:
            st.error("Simulation fehlgeschlagen. Es konnten nicht genügend historische Daten für die Wertpapiere deines Portfolios abgerufen werden.")
            return
            
        st.divider()
        st.subheader("📊 Ergebnisse")
        
        # Endwerte berechnen
        pf_endwert = pf_series.iloc[-1]
        pf_return_pct = ((pf_endwert / startkapital) - 1.0) * 100
        
        if not bm_series.empty:
            bm_endwert = bm_series.iloc[-1]
            bm_return_pct = ((bm_endwert / startkapital) - 1.0) * 100
        else:
            bm_endwert = 0
            bm_return_pct = 0.0
            
        # 2. Metriken
        m1, m2, m3 = st.columns(3)
        
        with m1:
            st.metric(
                "Dein Portfolio Endwert", 
                f"{pf_endwert:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.'),
                f"{pf_return_pct:+.2f} % Total Return"
            )
            
        with m2:
            if not bm_series.empty:
                delta = pf_return_pct - bm_return_pct
                st.metric(
                    f"{benchmark_name} Endwert", 
                    f"{bm_endwert:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.'),
                    f"{bm_return_pct:+.2f} % Total Return"
                )
            else:
                st.metric("Benchmark", "-", "-")
                
        with m3:
            # Max Drawdown
            st.metric(
                "Dein Max Drawdown (Risiko)", 
                f"{pf_dd:.2f} %".replace('.', ','),
                f"Benchmark: {bm_dd:.2f} %" if not bm_series.empty else None,
                delta_color="inverse"
            )
            
        st.markdown("*Der **Max Drawdown** zeigt den prozentual höchsten Verlust vom zwischenzeitlichen Hoch zum Tief. Ein niedrigerer Wert bedeutet weniger zwischenzeitlicher Schmerz.*")
            
        # 3. Chart
        st.markdown("### Wachstumsverlauf")
        
        # Bereite Daten für Plotly vor
        plot_df = pd.DataFrame({'Portfolio': pf_series})
        if not bm_series.empty:
            plot_df[benchmark_name] = bm_series
            
        plot_df = plot_df.reset_index()
        # Egal wie der Index heißt (Date, Datum, index), wir benennen die erste Spalte in 'Datum' um
        plot_df.rename(columns={plot_df.columns[0]: 'Datum'}, inplace=True)
        plot_df = plot_df.melt(id_vars=['Datum'], var_name='Strategie', value_name='Wert (€)')
        
        fig = px.line(
            plot_df, 
            x='Datum', 
            y='Wert (€)', 
            color='Strategie',
            color_discrete_sequence=['#ff9999', '#66b3ff']
        )
        
        fig.update_layout(
            margin=dict(t=20, b=20, l=20, r=20),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            hovermode='x unified',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
