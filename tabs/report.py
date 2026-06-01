import streamlit as st
from utils import *

def render():
    st.header("📄 Report")
    st.markdown("Erstelle einen KI-gestützten Gesamtreport deines Portfolios. Der Report wird hier angezeigt und kann als PDF exportiert werden.")
    
    # Init session state
    if 'pdf_report_bytes' not in st.session_state:
        st.session_state.pdf_report_bytes = None
    if 'report_summary_text' not in st.session_state:
        st.session_state.report_summary_text = None
    
    # Berechne Metriken
    gesamtwert = 0
    if not st.session_state.portfolio_df.empty:
        gesamtwert, _, _ = berechne_portfolio_metriken(st.session_state.portfolio_df)
    
    # LLM config (same as ai_advisor)
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
    
    is_ready = not st.session_state.portfolio_df.empty and (llm_config.get('api_key') or llm_config['provider'] != 'Google Gemini')
    has_chat = len(st.session_state.chat_history) > 0
    
    if st.session_state.portfolio_df.empty:
        st.info("Füge im Positionen-Tab erst Positionen hinzu, um einen Report zu erstellen.")
        return
    
    if not is_ready:
        st.warning("Bitte lege über ⚙️ Einstellungen in der Sidebar einen API-Key fest.")
        return
        
    # --- Controls ---
    col1, col2 = st.columns([0.6, 0.4])
    
    with col1:
        include_full_chat = st.checkbox("💬 Kompletten Chat-Verlauf anhängen", value=False, key="pdf_full_chat_report")
    
    with col2:
        if not has_chat:
            st.caption("💡 Tipp: Starte erst eine Analyse im KI-Berater für einen reichhaltigeren Report.")
    
    col_gen, col_reset = st.columns(2)
    
    with col_gen:
        generate_clicked = st.button(
            "🤖 Report generieren" if not st.session_state.report_summary_text else "🔄 Report neu generieren",
            type="primary",
            use_container_width=True
        )
    
    with col_reset:
        if st.session_state.report_summary_text or st.session_state.pdf_report_bytes:
            if st.button("🗑️ Report löschen", use_container_width=True):
                st.session_state.report_summary_text = None
                st.session_state.pdf_report_bytes = None
                st.rerun()
    
    st.divider()
    
    # --- Generate Report ---
    if generate_clicked:
        st.session_state.pdf_report_bytes = None  # Reset PDF when regenerating
        
        report_placeholder = st.empty()
        with st.spinner("KI verfasst das Executive Summary..."):
            from prompts import get_summary_prompt
            summary_prompt = get_summary_prompt()
            history_for_summary = st.session_state.chat_history.copy()
            history_for_summary.append({"role": "user", "content": summary_prompt})
            
            summary_gen, err = get_llm_response_stream(llm_config, history_for_summary)
            if summary_gen:
                summary_text = ""
                for chunk in summary_gen:
                    summary_text += chunk
                    report_placeholder.markdown(summary_text + "▌")
                
                report_placeholder.empty()
                st.session_state.report_summary_text = summary_text
                st.rerun()
            else:
                st.error(f"Fehler bei der Report-Erstellung: {err}")
                return
    
    # --- Display Report ---
    if st.session_state.report_summary_text:
        st.markdown("### 📋 Executive Summary")
        st.markdown(st.session_state.report_summary_text)
        
        st.divider()
        
        if st.session_state.pdf_report_bytes:
            st.download_button(
                label="📥 PDF herunterladen",
                data=st.session_state.pdf_report_bytes,
                file_name="Portfolio_Gesamtreport.pdf",
                mime="application/pdf",
                use_container_width=True,
                type="primary"
            )
        else:
            if st.button("📄 Als PDF exportieren", use_container_width=True):
                with st.spinner("Erzeuge PDF mit Diagramm und Tabelle..."):
                    from pdf_export import generate_portfolio_pdf as export_full_report_to_pdf
                    pdf_bytes = export_full_report_to_pdf(
                        st.session_state.portfolio_df,
                        gesamtwert,
                        st.session_state.report_summary_text,
                        st.session_state.chat_history if include_full_chat else None
                    )
                    if pdf_bytes:
                        st.session_state.pdf_report_bytes = pdf_bytes
                        st.rerun()
                    else:
                        st.error("Fehler bei der PDF-Erstellung.")
    else:
        st.markdown("*Klicke oben auf 'Report generieren', um einen KI-gestützten Gesamtreport zu erstellen.*")
