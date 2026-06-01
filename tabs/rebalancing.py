import streamlit as st
import pandas as pd
import plotly.express as px

def render():
    st.title("⚖️ Rebalancing Rechner")
    st.markdown("Stelle dein Portfolio wieder auf die gewünschte Ziel-Allokation ein, ohne Positionen verkaufen zu müssen. Ideal für das Investieren von neuem Kapital.")
    
    if st.session_state.portfolio_df.empty:
        st.info("Dein Portfolio ist leer. Füge zunächst im Dashboard Positionen hinzu.")
        return
        
    df = st.session_state.portfolio_df.copy()
    
    # Nutze Live_Gesamtwert wenn vorhanden, ansonsten Wert
    if 'Live_Gesamtwert' in df.columns and st.session_state.live_data_fetched:
        df['Akt. Wert'] = df['Live_Gesamtwert'].fillna(df['Wert'])
    else:
        df['Akt. Wert'] = df['Wert']
        
    aktueller_gesamtwert = df['Akt. Wert'].sum()
    
    if aktueller_gesamtwert <= 0:
        st.warning("Dein Portfolio hat aktuell keinen Wert. Bitte füge Positionen mit Werten hinzu.")
        return
        
    st.divider()
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("1. Frisches Kapital")
        neues_kapital = st.number_input("Wie viel neues Kapital möchtest du investieren? (€)", min_value=0.0, value=0.0, step=100.0)
        
    with col2:
        st.subheader("2. Portfolio-Zustand")
        st.metric("Aktueller Gesamtwert", f"{aktueller_gesamtwert:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.'))
        ziel_gesamtwert = aktueller_gesamtwert + neues_kapital
        st.metric("Gesamtwert nach Investition", f"{ziel_gesamtwert:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.'))
        
    st.divider()
    st.subheader("3. Ziel-Allokation definieren")
    
    st.markdown("Trage hier ein, wie viel Prozent jedes Asset zukünftig in deinem Portfolio ausmachen soll.")
    
    # DataFrame für Eingabe vorbereiten
    if 'rebalancing_targets' not in st.session_state:
        # Initialisierung: Aktuelle Allokation als Vorschlag
        targets = []
        for _, row in df.iterrows():
            akt_wert = row['Akt. Wert']
            akt_prozent = (akt_wert / aktueller_gesamtwert) * 100 if aktueller_gesamtwert > 0 else 0
            targets.append({
                'Wertpapier': row['Wertpapier'],
                'ISIN': row.get('ISIN', ''),
                'Aktuell (%)': round(akt_prozent, 2),
                'Ziel (%)': round(akt_prozent, 2)
            })
        st.session_state.rebalancing_targets = pd.DataFrame(targets)
        
    # Wenn sich das Portfolio geändert hat, füge neue Assets hinzu oder lösche fehlende
    current_assets = set(df['Wertpapier'].tolist())
    stored_assets = set(st.session_state.rebalancing_targets['Wertpapier'].tolist())
    
    if current_assets != stored_assets:
        # Einfach neu initialisieren bei Änderung
        targets = []
        for _, row in df.iterrows():
            akt_wert = row['Akt. Wert']
            akt_prozent = (akt_wert / aktueller_gesamtwert) * 100 if aktueller_gesamtwert > 0 else 0
            targets.append({
                'Wertpapier': row['Wertpapier'],
                'ISIN': row.get('ISIN', ''),
                'Aktuell (%)': round(akt_prozent, 2),
                'Ziel (%)': round(akt_prozent, 2)
            })
        st.session_state.rebalancing_targets = pd.DataFrame(targets)
        
    # Data Editor für die Ziel-Prozente
    edited_targets = st.data_editor(
        st.session_state.rebalancing_targets,
        column_config={
            "Wertpapier": st.column_config.TextColumn("Wertpapier", disabled=True),
            "ISIN": st.column_config.TextColumn("ISIN", disabled=True),
            "Aktuell (%)": st.column_config.NumberColumn("Aktuell (%)", disabled=True, format="%.2f"),
            "Ziel (%)": st.column_config.NumberColumn("Ziel (%)", format="%.2f", min_value=0.0, max_value=100.0, step=1.0)
        },
        hide_index=True,
        use_container_width=True
    )
    
    total_target = edited_targets['Ziel (%)'].sum()
    
    # Fortschrittsbalken für 100% Validierung
    if abs(total_target - 100.0) < 0.01:
        st.success(f"Summe der Ziel-Allokation: {total_target:.2f}% ✅")
        can_calculate = True
    else:
        st.error(f"Summe der Ziel-Allokation muss genau 100% ergeben. Aktuell: {total_target:.2f}%")
        can_calculate = False
        
    # Save the edited targets back to session state
    st.session_state.rebalancing_targets = edited_targets
    
    if can_calculate and neues_kapital > 0:
        st.divider()
        st.subheader("4. Rebalancing Ergebnis")
        
        results = []
        rest_kapital = neues_kapital
        
        # 1. Schritt: Zielwert pro Asset berechnen und Differenz ermitteln
        calc_df = pd.merge(df[['Wertpapier', 'Akt. Wert']], edited_targets[['Wertpapier', 'Aktuell (%)', 'Ziel (%)']], on='Wertpapier')
        calc_df['Ziel_Wert_Euros'] = ziel_gesamtwert * (calc_df['Ziel (%)'] / 100.0)
        calc_df['Differenz'] = calc_df['Ziel_Wert_Euros'] - calc_df['Akt. Wert']
        
        # 2. Schritt: Wir wollen nur nachkaufen, nichts verkaufen.
        # Negative Differenzen (Asset ist übergewichtet) werden auf 0 gesetzt (kein Nachkauf).
        calc_df['Benötigter_Kauf'] = calc_df['Differenz'].apply(lambda x: x if x > 0 else 0)
        
        total_benoetigt = calc_df['Benötigter_Kauf'].sum()
        
        if total_benoetigt <= 0:
            st.info("Dein Portfolio entspricht bereits exakt deiner Ziel-Allokation! Es sind keine Zukäufe nötig.")
        else:
            # 3. Schritt: Das neue Kapital auf die zu kaufenden Assets verteilen
            if neues_kapital >= total_benoetigt:
                # Wir haben genug Kapital, um die Zielallokation exakt zu erreichen
                calc_df['Empfohlener_Kauf'] = calc_df['Benötigter_Kauf']
                rest_kapital = neues_kapital - total_benoetigt
            else:
                # Wir haben nicht genug Kapital. Wir verteilen es proportional zu den benötigten Käufen.
                calc_df['Kauf_Anteil'] = calc_df['Benötigter_Kauf'] / total_benoetigt
                calc_df['Empfohlener_Kauf'] = calc_df['Kauf_Anteil'] * neues_kapital
                rest_kapital = 0.0
                
            calc_df['Neuer_Gesamtwert'] = calc_df['Akt. Wert'] + calc_df['Empfohlener_Kauf']
            calc_df['Neue_Allokation (%)'] = (calc_df['Neuer_Gesamtwert'] / (ziel_gesamtwert - rest_kapital)) * 100
            
            # Ergebnis Tabelle anzeigen
            res_display = calc_df[calc_df['Empfohlener_Kauf'] > 0].copy()
            res_display = res_display.sort_values(by='Empfohlener_Kauf', ascending=False)
            
            st.markdown("### 🛒 Einkaufsliste")
            st.dataframe(
                res_display[['Wertpapier', 'Empfohlener_Kauf', 'Neue_Allokation (%)']],
                column_config={
                    "Empfohlener_Kauf": st.column_config.NumberColumn("Zu investieren (€)", format="%.2f"),
                    "Neue_Allokation (%)": st.column_config.NumberColumn("Neue Allokation (%)", format="%.2f")
                },
                hide_index=True,
                use_container_width=True
            )
            
            if rest_kapital > 0.01:
                st.info(f"💡 Du hast die Ziel-Allokation erreicht und es sind noch **{rest_kapital:,.2f} €** übrig!")
            elif neues_kapital < total_benoetigt:
                st.warning(f"⚠️ Um die Ziel-Allokation exakt zu erreichen, bräuchtest du eigentlich **{total_benoetigt:,.2f} €** neues Kapital. Das verfügbare Kapital wurde bestmöglich proportional aufgeteilt, um sich dem Ziel anzunähern.")
                
            # Chart Vergleich (Aktuell vs Neu)
            st.markdown("### 📊 Allokations-Vergleich")
            
            plot_df = pd.DataFrame({
                'Wertpapier': calc_df['Wertpapier'].tolist() * 2,
                'Prozent': calc_df['Aktuell (%)'].tolist() + calc_df['Neue_Allokation (%)'].tolist(),
                'Zustand': ['Aktuell'] * len(calc_df) + ['Nach Rebalancing'] * len(calc_df)
            })
            
            fig = px.bar(
                plot_df,
                x='Wertpapier',
                y='Prozent',
                color='Zustand',
                barmode='group',
                color_discrete_sequence=['#ff9999', '#66b3ff']
            )
            fig.update_layout(
                margin=dict(t=20, b=20, l=20, r=20),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                yaxis_title="Anteil am Portfolio (%)"
            )
            st.plotly_chart(fig, use_container_width=True)
