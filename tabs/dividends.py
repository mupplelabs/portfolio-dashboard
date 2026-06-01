import streamlit as st
import pandas as pd
import plotly.express as px
from utils import fetch_dividend_data

def render():
    st.title("💸 Dividend Radar")
    st.markdown("Analysiere dein zu erwartendes passives Einkommen aus Dividenden und Ausschüttungen.")
    
    if st.session_state.portfolio_df.empty:
        st.info("Dein Portfolio ist leer. Füge zunächst im Dashboard Positionen hinzu.")
        return
        
    with st.spinner("Lade historische und erwartete Dividenden-Daten über Yahoo Finance..."):
        df_divs, df_hist = fetch_dividend_data(st.session_state.portfolio_df)
        
    if df_divs.empty:
        st.warning("Es konnten keine Daten abgerufen werden.")
        return
        
    # Filtere auf Assets, die auch wirklich Dividenden zahlen
    df_payers = df_divs[df_divs['Erwartet_pa'] > 0].copy()
    
    total_dividend_pa = df_divs['Erwartet_pa'].sum()
    total_portfolio_value = df_divs['Akt_Wert'].sum()
    
    avg_yield = (total_dividend_pa / total_portfolio_value * 100) if total_portfolio_value > 0 else 0.0
    
    st.divider()
    
    # 1. KPIs
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Erwartetes passives Einkommen (p.a.)", f"{total_dividend_pa:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.'))
    
    with col2:
        st.metric("Durchschnittliche Portfolio-Rendite", f"{avg_yield:,.2f} %".replace('.', ','))
        
    with col3:
        # Durchschnittlicher Ertrag pro Monat
        st.metric("Ø Einkommen pro Monat", f"{(total_dividend_pa / 12):,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.'))
        
    st.divider()
    
    # 3. Dividenden-Kalender (Option 3)
    st.subheader("📅 Dividenden-Historie (Letzte 12 Monate)")
    if not df_hist.empty:
        # Konvertiere Datum in Monat-Jahr für die Gruppierung
        df_hist['Monat'] = df_hist['Datum'].dt.to_period('M').astype(str)
        
        # Gruppiere nach Monat und Asset
        hist_grouped = df_hist.groupby(['Monat', 'Wertpapier'])['Ausschüttung'].sum().reset_index()
        
        fig = px.bar(
            hist_grouped,
            x='Monat',
            y='Ausschüttung',
            color='Wertpapier',
            title='Tatsächliche Ausschüttungen nach Monat (auf Basis aktueller Stückzahl)',
            labels={'Ausschüttung': 'Ausschüttung (€)', 'Monat': 'Monat'},
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        
        fig.update_layout(
            barmode='stack',
            xaxis={'type': 'category'}, # Erhält die zeitliche Reihenfolge der Strings
            margin=dict(t=40, b=20, l=20, r=20),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white')
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Keine ausreichende Historie bei Yahoo Finance gefunden, um ein Diagramm zu zeichnen.")
        
    st.divider()
    
    # 2. Aufschlüsselung pro Asset
    st.subheader("🏢 Aufschlüsselung pro Position")
    
    if not df_payers.empty:
        df_display = df_payers.sort_values(by='Erwartet_pa', ascending=False)
        st.dataframe(
            df_display[['Wertpapier', 'St_Nom', 'Dividende_pro_Stück', 'Erwartet_pa', 'Rendite_Prozent', 'Währung']],
            column_config={
                "St_Nom": st.column_config.NumberColumn("Anteile", format="%.2f"),
                "Dividende_pro_Stück": st.column_config.NumberColumn("Dividende / Anteil", format="%.2f"),
                "Erwartet_pa": st.column_config.NumberColumn("Erwartet Gesamt (p.a.)", format="%.2f"),
                "Rendite_Prozent": st.column_config.NumberColumn("Dividenden-Rendite (%)", format="%.2f")
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("Dein Portfolio enthält derzeit keine Positionen, die (laut Yahoo Finance) eine Dividende ausschütten.")
