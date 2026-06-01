import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from google import genai

# Konfiguration der Streamlit-Seite (Muss als erstes aufgerufen werden)
st.set_page_config(
    page_title="Portfolio Analyse Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS für ein modernes Design
st.markdown("""
<style>
    /* Allgemeine Anpassungen */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    /* Metrik-Karten stylen */
    div[data-testid="metric-container"] {
        background-color: #1E1E1E;
        border: 1px solid #333;
        padding: 5% 5% 5% 10%;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    div[data-testid="metric-container"] label {
        color: #B0B0B0 !important;
        font-weight: bold;
    }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
        color: #FFFFFF !important;
    }
</style>
""", unsafe_allow_html=True)


# --- Session State Initialisierung ---
if 'portfolio_df' not in st.session_state:
    # Platzhalter-Daten laden
    st.session_state.portfolio_df = pd.DataFrame({
        'Wertpapier': ['Apple Inc.', 'Microsoft Corp.', 'Deka MSCI World'],
        'Ticker': ['AAPL', 'MSFT', 'EUNL.DE'],
        'Boersenpl': ['XETRA', 'XETRA', 'Tradegate'],
        'St_Nom': [50.0, 30.0, 100.0],
        'St_NomW': ['Stk', 'Stk', 'Stk'],
        'Wert': [8500.00, 12000.00, 11500.00],
        'WertW': ['EUR', 'EUR', 'EUR'],
        'Orderkost': [10.00, 10.00, 15.00],
        'OrderkostW': ['EUR', 'EUR', 'EUR'],
        'Kaufpreis': [7500.00, 10500.00, 10500.00], # Bank CSVs verwenden 'Kaufpreis' oft als Gesamtwert
        'ISIN': ['US0378331005', 'US5949181045', 'DE000ETFL508']
    })

if 'live_data_fetched' not in st.session_state:
    st.session_state.live_data_fetched = False
if 'uploader_key' not in st.session_state:
    st.session_state.uploader_key = 0
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'gemini_error' not in st.session_state:
    st.session_state.gemini_error = False
import os
if 'env_defaults_loaded' not in st.session_state:
    st.session_state.gemini_api_key = os.environ.get('GEMINI_API_KEY', '')
    st.session_state.claude_api_key = os.environ.get('CLAUDE_API_KEY', '')
    st.session_state.local_base_url = os.environ.get('LOCAL_LLM_URL', 'http://localhost:11434/v1')
    st.session_state.local_api_key = os.environ.get('LOCAL_LLM_KEY', '')
    st.session_state.fmp_api_key_input = os.environ.get('FMP_API_KEY', '')
    
    st.session_state._backup_gemini = st.session_state.gemini_api_key
    st.session_state._backup_claude = st.session_state.claude_api_key
    st.session_state._backup_url = st.session_state.local_base_url
    st.session_state._backup_local_key = st.session_state.local_api_key
    st.session_state._backup_fmp_key = st.session_state.fmp_api_key_input
    
    st.session_state.env_defaults_loaded = True

if '_backup_gemini' not in st.session_state: st.session_state._backup_gemini = st.session_state.get('gemini_api_key', '')
if '_backup_claude' not in st.session_state: st.session_state._backup_claude = st.session_state.get('claude_api_key', '')
if '_backup_url' not in st.session_state: st.session_state._backup_url = st.session_state.get('local_base_url', 'http://localhost:11434/v1')
if '_backup_local_key' not in st.session_state: st.session_state._backup_local_key = st.session_state.get('local_api_key', '')
if '_backup_fmp_key' not in st.session_state: st.session_state._backup_fmp_key = st.session_state.get('fmp_api_key_input', '')

# Restore from backup if Streamlit deleted the widget key due to dropdown switch
if 'gemini_api_key' not in st.session_state: st.session_state.gemini_api_key = st.session_state.get('_backup_gemini', '')
if 'claude_api_key' not in st.session_state: st.session_state.claude_api_key = st.session_state.get('_backup_claude', '')
if 'local_base_url' not in st.session_state: st.session_state.local_base_url = st.session_state.get('_backup_url', 'http://localhost:11434/v1')
if 'local_api_key' not in st.session_state: st.session_state.local_api_key = st.session_state.get('_backup_local_key', '')
if 'fmp_api_key_input' not in st.session_state: st.session_state.fmp_api_key_input = st.session_state.get('_backup_fmp_key', '')

from utils import *
from tabs import portfolio_overview, rebalancing, dividends, backtesting, ai_advisor, setup_data, report, settings

# --- Hauptbereich ---

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(['📊 Dashboard', '💸 Dividend Radar', '⏱️ Backtesting', '⚖️ Rebalancing', '📄 Report', '📂 Positionen', '⚙️ Einstellungen'])

with tab1:
    portfolio_overview.render()

with tab2:
    dividends.render()
    
with tab3:
    backtesting.render()

with tab4:
    rebalancing.render()

with tab5:
    report.render()
    
with tab6:
    setup_data.render()
    
with tab7:
    settings.render()

# --- Copilot Sidebar ---
with st.sidebar:
    ai_advisor.render()

# --- Programmatic Tab Switcher ---
if st.session_state.get('switch_tab') is not None:
    tab_idx = st.session_state.switch_tab
    st.session_state.switch_tab = None
    import streamlit.components.v1 as components
    components.html(f"""
        <script>
            setTimeout(() => {{
                const tabs = window.parent.document.querySelectorAll('button[data-baseweb="tab"]');
                if (tabs.length > {tab_idx}) {{
                    tabs[{tab_idx}].click();
                }}
            }}, 150);
        </script>
    """, height=0)
