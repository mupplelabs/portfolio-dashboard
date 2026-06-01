import streamlit as st
import pandas as pd
import plotly.express as px
from utils import *

def render():
    st.title("📊 Portfolio Dashboard")
    st.markdown("Übersicht deiner aktuellen Anlagen und deren Performance.")
    
    # Live Daten Button
    if not st.session_state.portfolio_df.empty:
        if st.button("🔄 Live-Kurse abrufen (Yahoo Finance)", type="primary"):
            with st.spinner('Suche fehlende Ticker & Lade Live-Daten...'):
                live_prices, updated_tickers = fetch_live_prices(st.session_state.portfolio_df)
                
                # Ticker in df aktualisieren
                st.session_state.portfolio_df['Ticker'] = updated_tickers
                st.session_state.portfolio_df['Live_Kurs'] = live_prices
                
                # Berechne Live Gesamtwert (Stückzahl * Live_Kurs)
                st.session_state.portfolio_df['Live_Gesamtwert'] = st.session_state.portfolio_df['St_Nom'] * st.session_state.portfolio_df['Live_Kurs']
                st.session_state.live_data_fetched = True
                
                # Warnung falls Ticker fehlen/falsch sind
                missing_tickers = st.session_state.portfolio_df[st.session_state.portfolio_df['Live_Kurs'].isna()]['Wertpapier'].tolist()
                if missing_tickers:
                    st.warning(f"Für folgende Positionen konnten keine Live-Daten gefunden werden (Ticker prüfen): {', '.join(missing_tickers)}")
                else:
                    st.success("Live-Daten erfolgreich geladen!")
    
    # Metriken berechnen
    gesamtwert, gesamt_gewinn, gesamt_performance_prozent = berechne_portfolio_metriken(st.session_state.portfolio_df)
    
    # Metrik-Karten anzeigen
    col_m1, col_m2, col_m3 = st.columns(3)
    
    with col_m1:
        st.metric("Gesamtwert", f"{gesamtwert:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.'))
    
    with col_m2:
        st.metric("Gesamtgewinn / Verlust", f"{gesamt_gewinn:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.'), 
                  f"{gesamt_gewinn:,.2f} €", delta_color="normal" if gesamt_gewinn >= 0 else "inverse")
    
    with col_m3:
        st.metric("Performance (%)", f"{gesamt_performance_prozent:,.2f} %".replace('.', ','),
                  f"{gesamt_performance_prozent:,.2f} %", delta_color="normal" if gesamt_performance_prozent >= 0 else "inverse")
    
    
    st.divider()
    
    # Ticker-Editor Bereich
    st.subheader("Ticker-Symbole bearbeiten")
    st.markdown("Trage hier die Yahoo Finance Ticker-Symbole ein (z.B. `AAPL` oder `EUNL.DE`), um Live-Daten abrufen zu können.")
    if not st.session_state.portfolio_df.empty:
        edited_df = st.data_editor(
            st.session_state.portfolio_df[['Wertpapier', 'ISIN', 'Ticker']],
            use_container_width=True,
            disabled=['Wertpapier', 'ISIN'],
            num_rows="delete",
            key="ticker_editor"
        )
        
        # Update logic handling deletions
        if len(edited_df) != len(st.session_state.portfolio_df):
            valid_indices = [idx for idx in edited_df.index if idx in st.session_state.portfolio_df.index]
            st.session_state.portfolio_df = st.session_state.portfolio_df.loc[valid_indices].copy()
            st.session_state.portfolio_df['Ticker'] = edited_df.loc[valid_indices, 'Ticker']
            st.session_state.live_data_fetched = False
            st.rerun()
        elif not edited_df.equals(st.session_state.portfolio_df[['Wertpapier', 'ISIN', 'Ticker']]):
            st.session_state.portfolio_df['Ticker'] = edited_df['Ticker']
    
    st.divider()
    
    # Layout für Charts und Tabelle
    st.subheader("Asset Allocation & Positionsübersicht")
    col_chart, col_table = st.columns([1, 1.8])
    
    with col_chart:
        if not st.session_state.portfolio_df.empty and gesamtwert > 0:
            plot_val_col = 'Live_Gesamtwert' if st.session_state.live_data_fetched else 'Wert'
            # Fallback falls Live-Gesamtwert NaN ist
            st.session_state.portfolio_df['_Plot_Wert'] = st.session_state.portfolio_df.get(plot_val_col, st.session_state.portfolio_df['Wert']).fillna(st.session_state.portfolio_df['Wert'])
            
            fig = px.pie(
                st.session_state.portfolio_df, 
                values='_Plot_Wert', 
                names='Wertpapier', 
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig.update_layout(
                margin=dict(t=20, b=20, l=20, r=20),
                showlegend=True,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white')
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Keine Daten für Diagramm verfügbar.")
    
    with col_table:
        if not st.session_state.portfolio_df.empty:
            df_display = st.session_state.portfolio_df.copy()
            
            df_display['Kaufwert'] = df_display['Kaufpreis'] + df_display['Orderkost']
            
            # Durchschnittlicher Kaufkurs (Vermeide Division durch Null)
            df_display['Ø Kaufkurs'] = df_display.apply(lambda row: row['Kaufwert'] / row['St_Nom'] if row['St_Nom'] > 0 else 0, axis=1)
            
            if st.session_state.live_data_fetched and 'Live_Kurs' in df_display.columns:
                df_display['Aktueller Kurs'] = df_display['Live_Kurs']
                df_display['Akt. Wert'] = df_display['Live_Gesamtwert'].fillna(df_display['Wert'])
            else:
                df_display['Aktueller Kurs'] = df_display.apply(lambda row: row['Wert'] / row['St_Nom'] if row['St_Nom'] > 0 else 0, axis=1)
                df_display['Akt. Wert'] = df_display['Wert']
                
            df_display['Gewinn/Verlust'] = df_display['Akt. Wert'] - df_display['Kaufwert']
            df_display['Performance (%)'] = (df_display['Gewinn/Verlust'] / df_display['Kaufwert'] * 100).round(2)
            
            display_cols = ['Ticker', 'St_Nom', 'Ø Kaufkurs', 'Aktueller Kurs', 'Akt. Wert', 'Gewinn/Verlust', 'Performance (%)']
            
            st.dataframe(
                df_display[display_cols],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "St_Nom": st.column_config.NumberColumn("Anteile", format="%.2f"),
                    "Ø Kaufkurs": st.column_config.NumberColumn("Ø Kaufkurs (€)", format="%.2f"),
                    "Aktueller Kurs": st.column_config.NumberColumn("Akt. Kurs (€)", format="%.2f"),
                    "Akt. Wert": st.column_config.NumberColumn("Gesamtwert (€)", format="%.2f"),
                    "Gewinn/Verlust": st.column_config.NumberColumn("G/V (€)", format="%.2f"),
                    "Performance (%)": st.column_config.NumberColumn("Perf. (%)", format="%.2f")
                }
            )
            
            if st.button("Portfolio leeren", type="secondary"):
                st.session_state.portfolio_df = pd.DataFrame(columns=st.session_state.portfolio_df.columns)
                st.session_state.live_data_fetched = False
                st.session_state.uploader_key += 1
                st.session_state.last_uploaded_file_id = None
                st.rerun()
        else:
            st.info("Das Portfolio ist aktuell leer.")
    
    st.divider()
    
    # --- Portfolio Verlauf ---
    st.subheader("📈 Portfolio Verlauf")
    if not st.session_state.portfolio_df.empty:
        col_per, col_filt = st.columns([1, 2])
        with col_per:
            period = st.selectbox(
                "Zeitraum",
                ["1 Tag", "1 Woche", "1 Monat", "3 Monate", "1 Jahr", "10 Jahre", "Maximal"],
                index=4,
                key="history_period_select"
            )
        with col_filt:
            available_assets = st.session_state.portfolio_df['Wertpapier'].tolist()
            selected_assets = st.multiselect(
                "Einzelwerte anzeigen (leer = Gesamtwert)",
                options=available_assets,
                default=[],
                key="history_asset_filter"
            )
            
        with st.spinner('Lade historische Daten...'):
            fmp_key_for_history = st.session_state.get('fmp_api_key_input', '').strip()
            result_total, result_individual = fetch_portfolio_history(st.session_state.portfolio_df, period, fmp_key_for_history)
            
            if not result_total.empty:
                if selected_assets:
                    plot_df = result_individual[result_individual['Asset'].isin(selected_assets)]
                    color_col = 'Asset'
                    colors = px.colors.qualitative.Pastel
                else:
                    plot_df = result_total
                    color_col = None
                    colors = ['#4CAF50']
                    
                fig_hist = px.line(
                    plot_df, 
                    x='Datum', 
                    y='Wert',
                    color=color_col,
                    color_discrete_sequence=colors
                )
                fig_hist.update_layout(
                    margin=dict(t=20, b=20, l=20, r=20),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white'),
                    xaxis_title="",
                    yaxis_title="Wert (€)",
                    hovermode="x unified"
                )
                st.plotly_chart(fig_hist, use_container_width=True)
            else:
                st.info("Keine historischen Daten für die ausgewählten Anlagen verfügbar.")
    else:
        st.info("Füge dem Portfolio erst Positionen hinzu, um den Verlauf zu sehen.")
    

