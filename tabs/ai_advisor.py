import streamlit as st
import pandas as pd
from utils import *

def render():
    st.markdown("<div id='chat-top-anchor'></div>", unsafe_allow_html=True)
    
    st.header("🤖 KI-Finanzberater")
    st.markdown("Dein persönlicher, KI-gestützter Finanzassistent.")
    
    # Berechne Metriken für den Kontext
    gesamtwert = 0
    if not st.session_state.portfolio_df.empty:
        gesamtwert, _, _ = berechne_portfolio_metriken(st.session_state.portfolio_df)
        
    # Construct llm_config from session state
    _provider = st.session_state.get("llm_provider_input", "Google Gemini")
    _api_key = ""
    _base_url = None
    if _provider == "Google Gemini":
        _api_key = st.session_state.get("_backup_gemini", "")
    elif _provider == "Anthropic Claude":
        _api_key = st.session_state.get("_backup_claude", "")
    else:
        _api_key = st.session_state.get("_backup_local_key", "")
        _base_url = st.session_state.get("_backup_url", "http://localhost:11434/v1")
        
    _model = st.session_state.get("llm_model_input", None)
    if not _model:
        if _provider == "Google Gemini": _model = "gemini-2.5-flash"
        elif _provider == "Anthropic Claude": _model = "claude-sonnet-4-6"
        else: _model = "llama3"
        
    llm_config = {"provider": _provider, "api_key": _api_key, "base_url": _base_url, "model": _model}
    
    is_generating = len(st.session_state.chat_history) > 0 and st.session_state.chat_history[-1]['role'] == 'user'

    is_ready = not st.session_state.portfolio_df.empty and (llm_config.get('api_key') or llm_config['provider'] != 'Google Gemini')
    
    if st.session_state.portfolio_df.empty:
        st.info("Füge im Positionen-Tab Positionen hinzu.")
    elif not (llm_config.get('api_key') or llm_config['provider'] != 'Google Gemini'):
        st.error("Bitte lege über ⚙️ Einstellungen einen API-Key fest!")
    else:
        # Placeholders for search status during prep
        cancel_placeholder = st.empty()
        status_container = st.empty()

        # --- SCROLLABLE CHAT CONTAINER ---
        chat_container = st.container(height=450)
        
        with chat_container:
            for i, msg in enumerate(st.session_state.chat_history):
                if i == 0 and msg['role'] == 'user' and 'display' not in msg:
                    with st.chat_message("user"):
                        st.write("*(Portfolio-Daten übergeben)*")
                else:
                    with st.chat_message(msg['role']):
                        if msg['role'] == 'user' and 'display' in msg:
                            st.markdown(msg['display'])
                        else:
                            if msg.get('reasoning'):
                                with st.expander("🤔 Gedankengang"):
                                    st.markdown(msg['reasoning'])
                            st.markdown(msg['content'])
                            
                            if msg['role'] == 'model':
                                try:
                                    from st_copy_to_clipboard import st_copy_to_clipboard
                                    st_copy_to_clipboard(msg['content'], before_copy_label="📋 Kopieren", after_copy_label="✅ Kopiert!", key=f"copy_{i}")
                                except ImportError:
                                    pass
                                
                                if i == len(st.session_state.chat_history) - 1 and "[Verbindung zur KI unterbrochen:" in msg['content']:
                                    if st.button("🔄 Neu generieren", key=f"retry_gen_{i}"):
                                        st.session_state.chat_history.pop()
                                        st.rerun()

            # Handle Model Response INSIDE the scrollable container
            if is_generating:
                with st.chat_message("model"):
                    with st.spinner(f"KI ({llm_config['model']}) bereitet Antwort vor..."):
                        answer_gen, err = get_llm_response_stream(llm_config, st.session_state.chat_history)
                        if answer_gen:
                            cancel_clicked = st.button("⏹ Abbrechen", key="cancel_gen")
                            if cancel_clicked:
                                st.session_state.chat_history.pop()
                                st.rerun()
                                    
                            answer = st.write_stream(answer_gen)
                            reasoning = None
                            if "\n\n---\n\n**Antwort:**\n\n" in answer:
                                parts = answer.split("\n\n---\n\n**Antwort:**\n\n", 1)
                                reasoning = parts[0].replace("🤔 **Gedankengang der KI:**\n\n", "").strip()
                                answer = parts[1].strip()
                            st.session_state.chat_history.append({"role": "model", "content": answer, "reasoning": reasoning})
                            st.session_state.gemini_error = False
                            st.rerun()
                        else:
                            st.error(err)
                            st.session_state.gemini_error = True

        # --- CONTROLS BELOW CONTAINER (always visible) ---
        trigger_auto = False
        use_web_search = False
        include_portfolio = False
        use_chat_search = False
        
        if not is_generating:
            with st.expander("⚙️ KI-Einstellungen", expanded=False):
                # Modelle laden
                if _provider in ["Google Gemini", "Anthropic Claude"]:
                    available_models = get_available_models(_provider, _api_key) if _api_key else (["gemini-2.5-flash"] if _provider == "Google Gemini" else ["claude-sonnet-4-6"])
                else:
                    available_models = get_available_models(_provider, _api_key, _base_url) if _base_url else ["llama3", "local-model"]
            
                if available_models:
                    llm_model = st.selectbox("Modell", available_models, index=0, label_visibility="collapsed", key="llm_model_input")
                else:
                    llm_model = st.selectbox("Modell", ["Keine Modelle gefunden"], disabled=True, label_visibility="collapsed", key="llm_model_input")
                
                llm_config["model"] = llm_model
        
                if is_ready:
                    if len(st.session_state.chat_history) == 0:
                        use_web_search = st.checkbox("🌐 News & Webdaten", value=True)
                        include_portfolio = st.checkbox("📊 Portfolio-Daten", value=True)
                        use_chat_search = use_web_search
                    else:
                        use_web_search = False
                        use_chat_search = st.toggle("🌐 Live-Websuche", value=True)
                        include_portfolio = st.toggle("📊 Portfolio anhängen", value=False)
                else:
                    use_web_search = False
                    include_portfolio = False
                    use_chat_search = False
                    st.checkbox("🌐 News & Webdaten", value=False, disabled=True)
            
            # --- ACTION BUTTONS ---
            if is_ready:
                if len(st.session_state.chat_history) == 0:
                    trigger_auto = st.button("Automatische Analyse", type="primary", use_container_width=True)
                else:
                    trigger_auto = False
            else:
                trigger_auto = False
                st.button("Automatische Analyse", type="primary", use_container_width=True, disabled=True)
                
            if len(st.session_state.chat_history) > 0:
                if st.button("🔄 Chat zurücksetzen", type="secondary", use_container_width=True):
                    st.session_state.chat_history = []
                    st.session_state.gemini_error = False
                    st.rerun()

        # Chat input (always visible at bottom)
        if len(st.session_state.chat_history) == 0:
            user_q = st.chat_input("Frage stellen...", key="main_chat", disabled=not is_ready)
        else:
            user_q = st.chat_input("Rückfrage stellen...", key="main_chat", disabled=not is_ready)
            
        if trigger_auto or user_q:
            with cancel_placeholder.container():
                if st.button("⏹ Vorbereitung Abbrechen", key="cancel_pre_search"):
                    st.rerun()
                    
            if trigger_auto:
                with status_container.container():
                    with st.status("Aktualisiere Yahoo Finance...", expanded=True) as status:
                        live_prices, updated_tickers = fetch_live_prices(st.session_state.portfolio_df)
                        st.session_state.portfolio_df['Ticker'] = updated_tickers
                        st.session_state.portfolio_df['Live_Kurs'] = live_prices
                        st.session_state.portfolio_df['Live_Gesamtwert'] = st.session_state.portfolio_df['St_Nom'] * st.session_state.portfolio_df['Live_Kurs']
                        st.session_state.live_data_fetched = True
                        gesamtwert, _, _ = berechne_portfolio_metriken(st.session_state.portfolio_df)
                        status.update(label="Portfolio-Kurse aktualisiert.", state="complete")
        
            portfolio_text = prepare_anonymized_portfolio_data(st.session_state.portfolio_df, gesamtwert)
            
            if trigger_auto:
                from prompts import get_auto_analysis_initial_prompt
                initial_prompt = get_auto_analysis_initial_prompt(portfolio_text if include_portfolio else "")
                display_q = "Portfolio automatisch analysieren"
                
                if use_web_search:
                    with status_container.container():
                        with st.status("Suche Marktdaten...", expanded=True) as status:
                            search_ctx = generate_search_context(llm_config, portfolio_text, is_portfolio_analysis=True)
                            queries = search_ctx["web_queries"]
                            tickers = search_ctx["tickers"]
                            
                            if queries or tickers:
                                st.write("**Websuche:**")
                                if queries: st.write(f"- `{', '.join(queries)}`")
                                if tickers: st.write(f"- `{', '.join(tickers)}`")
                                
                            status.update(label="Sammle News...", state="running")
                            
                            search_results = fetch_custom_web_search(queries, include_macro=True)
                            ticker_data = fetch_ticker_live_data(tickers) if tickers else ""
                            
                            market_context = ""
                            if search_results and search_results != "RATE_LIMIT": 
                                market_context += search_results
                                if ticker_data: 
                                    market_context += ("\n\n" if market_context else "") + ticker_data
                                    
                                if not market_context or search_results == "RATE_LIMIT":
                                    status.update(label="Fallback Websuche...", state="running")
                                    fallback_res = fetch_chat_search_context("aktuelle marktsituation aktien etfs")
                                    if not market_context: market_context = fallback_res if fallback_res != "RATE_LIMIT" else ""
                                
                        if market_context == "RATE_LIMIT":
                            market_context = "" # Fallback trigger
                            
                    if market_context:
                        initial_prompt += f"\n\nZusätzlicher Kontext aus aktuellen Nachrichten/Websuche:\n{market_context}\nNutze diese Informationen, falls sie für die Antwort relevant sind."
                    else:
                        initial_prompt += f"\n\nZusätzlicher Kontext: Die Live-APIs für Marktdaten (Websuche) sind blockiert. Bitte greife auf dein Wissen zurück."
                
                st.session_state.pdf_report_bytes = None
                st.session_state.chat_history.append({"role": "user", "content": initial_prompt, "display": display_q})
                
            else:
                display_q = user_q
                if include_portfolio:
                    user_q += f"\n\n---\n**Aktueller Portfolio-Stand zur Referenz:**\n{portfolio_text}\nNutze diese Daten für deine Antwort, falls sie relevant sind."
                    
                if use_chat_search:
                    with status_container.container():
                        with st.status("Suche Marktdaten...", expanded=True) as status:
                            search_ctx = generate_search_context(llm_config, user_q)
                            queries = search_ctx["web_queries"]
                            tickers = search_ctx["tickers"]
                                
                            if queries or tickers:
                                st.write("**Websuche:**")
                                if queries: st.write(f"- `{', '.join(queries)}`")
                                if tickers: st.write(f"- `{', '.join(tickers)}`")
                            
                            search_results = fetch_custom_web_search(queries) if queries else fetch_chat_search_context(user_q)
                            if search_results == "RATE_LIMIT":
                                search_results = ""
                                user_q += "\n\n(HINWEIS FÜR DIE KI: Live-Suche wurde blockiert. Nutze dein eigenes Wissen.)"
                                
                            ticker_data = fetch_ticker_live_data(tickers) if tickers else ""
                            
                            # Kombiniere beides
                            combined_context = ""
                            if search_results: combined_context += search_results
                            if ticker_data: combined_context += ("\n\n" if combined_context else "") + ticker_data
                                
                            if combined_context:
                                search_results = combined_context
                                
                            if search_results:
                                user_q += f"\n\n---\n**Zusätzlicher Kontext aus aktueller Websuche:**\n{search_results}\nNutze diese Informationen."
                
                st.session_state.pdf_report_bytes = None
                st.session_state.chat_history.append({"role": "user", "content": user_q, "display": display_q})
                
            # Rerun to show user message immediately
            st.rerun()

