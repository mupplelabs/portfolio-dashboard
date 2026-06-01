import streamlit as st
import pandas as pd

def render():
    st.header("📂 Positionen")
    st.markdown("Lade deine Portfolio-CSV hoch oder füge Positionen manuell hinzu.")
    
    col_upload, col_manual = st.columns(2)
    
    with col_upload:
        st.subheader("📄 CSV hochladen")
        uploaded_file = st.file_uploader("Wähle deine Portfolio CSV-Datei", type=['csv'], key=f"uploader_setup_{st.session_state.uploader_key}")
        
        if uploaded_file is not None:
            current_file_id = getattr(uploaded_file, "file_id", uploaded_file.name + str(uploaded_file.size))
            if st.session_state.get('last_uploaded_file_id') != current_file_id:
                try:
                    try:
                        df_upload = pd.read_csv(uploaded_file, sep=None, engine='python', encoding='utf-8')
                    except UnicodeDecodeError:
                        uploaded_file.seek(0)
                        df_upload = pd.read_csv(uploaded_file, sep=None, engine='python', encoding='latin1')
                        
                    required_cols = ['Wertpapier', 'Boersenpl', 'St_Nom', 'St_NomW', 'Wert', 'WertW', 'Orderkost', 'OrderkostW', 'Kaufpreis', 'ISIN']
                    if all(col in df_upload.columns for col in required_cols):
                        num_cols = ['St_Nom', 'Kaufpreis', 'Orderkost', 'Wert']
                        for c in num_cols:
                            if not pd.api.types.is_numeric_dtype(df_upload[c]):
                                cleaned = df_upload[c].astype(str).str.replace(r'[^\d,.-]', '', regex=True)
                                def convert_to_float(val):
                                    if pd.isna(val) or val == '' or str(val).lower() == 'nan': return 0.0
                                    if ',' in str(val):
                                        val = str(val).replace('.', '')
                                        val = str(val).replace(',', '.')
                                    try:
                                        return float(val)
                                    except ValueError:
                                        return 0.0
                                df_upload[c] = cleaned.apply(convert_to_float)
                            else:
                                df_upload[c] = df_upload[c].fillna(0.0)

                        if 'Ticker' not in df_upload.columns:
                            df_upload.insert(1, 'Ticker', "")

                        st.session_state.portfolio_df = df_upload
                        st.session_state.live_data_fetched = False
                        st.session_state.last_uploaded_file_id = current_file_id
                        st.success("CSV erfolgreich geladen!")
                    else:
                        missing_cols = [col for col in required_cols if col not in df_upload.columns]
                        st.error(f"Fehlende Spalten in der CSV: {', '.join(missing_cols)}")
                except Exception as e:
                    st.error(f"Fehler beim Lesen der Datei: {e}")
                
    with col_manual:
        st.subheader("➕ Position manuell hinzufügen")
        with st.form("add_position_form_setup"):
            c1, c2 = st.columns(2)
            with c1:
                wertpapier = st.text_input("Wertpapier Name")
                isin = st.text_input("ISIN")
                ticker = st.text_input("Yahoo Ticker (z.B. AAPL)")
                st_nom = st.number_input("Stück/Nominal", min_value=0.0, format="%.4f")
                kaufpreis = st.number_input("Kaufwert (Gesamt)", min_value=0.0, format="%.2f")
                boersenpl = st.text_input("Börsenplatz", value="XETRA")
            with c2:
                wert = st.number_input("Aktueller Wert (Gesamt)", min_value=0.0, format="%.2f")
                orderkost = st.number_input("Orderkosten", min_value=0.0, format="%.2f")
                st_nom_w = st.selectbox("Einheit (St/Nom)", ["Stk", "Nominal"])
                wert_w = st.selectbox("Währung Wert", ["EUR", "USD", "CHF"])
                orderkost_w = st.selectbox("Währung Order", ["EUR", "USD", "CHF"])
                
            submitted = st.form_submit_button("Hinzufügen")
            
            if submitted:
                if ticker and st_nom > 0 and (not wertpapier or not isin):
                    import yfinance as yf
                    try:
                        t_obj = yf.Ticker(ticker)
                        info = t_obj.info
                        if not wertpapier:
                            wertpapier = info.get('shortName', info.get('longName', ticker))
                        if not isin:
                            isin = info.get('isin', ticker)
                        if wert == 0.0:
                            price = t_obj.fast_info.get('lastPrice', 0)
                            if price == 0:
                                hist = t_obj.history(period="1d")
                                if not hist.empty:
                                    price = hist['Close'].iloc[-1]
                            wert = price * st_nom
                            kaufpreis = wert if kaufpreis == 0.0 else kaufpreis
                    except Exception:
                        pass
                        
                if wertpapier and isin and st_nom > 0:
                    new_row = pd.DataFrame([{
                        'Wertpapier': wertpapier,
                        'Ticker': ticker,
                        'Boersenpl': boersenpl,
                        'St_Nom': st_nom,
                        'St_NomW': st_nom_w,
                        'Wert': wert,
                        'WertW': wert_w,
                        'Orderkost': orderkost,
                        'OrderkostW': orderkost_w,
                        'Kaufpreis': kaufpreis,
                        'ISIN': isin
                    }])
                    st.session_state.portfolio_df = pd.concat([st.session_state.portfolio_df, new_row], ignore_index=True)
                    st.session_state.live_data_fetched = False
                    st.success(f"{wertpapier} hinzugefügt!")
                else:
                    st.warning("Bitte entweder den Yahoo Ticker oder Name & ISIN angeben (sowie eine Stückzahl > 0).")
