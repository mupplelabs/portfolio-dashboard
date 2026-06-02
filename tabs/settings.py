import streamlit as st

def render():
    st.header("⚙️ Einstellungen (KI & API)")
    st.markdown("Konfiguriere hier die API-Schlüssel für KI-Modelle und Datenquellen.")
    
    col_ki, col_data = st.columns(2)
    
    with col_ki:
        st.subheader("🤖 KI Provider & Keys")
        llm_provider = st.selectbox("LLM Provider", ["Google Gemini", "Anthropic Claude", "OpenAI / Local"], key="llm_provider_input")
        if llm_provider == "Google Gemini":
            gemini_api_key = st.text_input("Gemini API Key", type="password", value=st.session_state._backup_gemini)
            if gemini_api_key != st.session_state._backup_gemini:
                st.session_state._backup_gemini = gemini_api_key
                st.rerun()
        elif llm_provider == "Anthropic Claude":
            claude_api_key = st.text_input("Claude API Key", type="password", value=st.session_state._backup_claude)
            if claude_api_key != st.session_state._backup_claude:
                st.session_state._backup_claude = claude_api_key
                st.rerun()
        else:
            local_base_url = st.text_input("API Base URL", value=st.session_state._backup_url)
            if local_base_url != st.session_state._backup_url:
                st.session_state._backup_url = local_base_url
                st.rerun()
            local_api_key = st.text_input("API Key (Optional)", type="password", value=st.session_state._backup_local_key)
            if local_api_key != st.session_state._backup_local_key:
                st.session_state._backup_local_key = local_api_key
                st.rerun()
                
    with col_data:
        st.subheader("📈 Datenquellen")
        fmp_api_key = st.text_input("FMP API Key (Optional)", type="password", value=st.session_state._backup_fmp_key)
        if fmp_api_key != st.session_state._backup_fmp_key:
            st.session_state._backup_fmp_key = fmp_api_key
            st.rerun()
        st.session_state.fmp_api_key_input = st.session_state._backup_fmp_key
