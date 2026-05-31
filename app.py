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
    
    st.session_state._backup_gemini = st.session_state.gemini_api_key
    st.session_state._backup_claude = st.session_state.claude_api_key
    st.session_state._backup_url = st.session_state.local_base_url
    st.session_state._backup_local_key = st.session_state.local_api_key
    
    st.session_state.env_defaults_loaded = True

# Restore from backup if Streamlit deleted the widget key due to dropdown switch
if 'gemini_api_key' not in st.session_state: st.session_state.gemini_api_key = st.session_state.get('_backup_gemini', '')
if 'claude_api_key' not in st.session_state: st.session_state.claude_api_key = st.session_state.get('_backup_claude', '')
if 'local_base_url' not in st.session_state: st.session_state.local_base_url = st.session_state.get('_backup_url', 'http://localhost:11434/v1')
if 'local_api_key' not in st.session_state: st.session_state.local_api_key = st.session_state.get('_backup_local_key', '')

# --- Funktionen ---
import requests

def search_ticker_by_isin(isin):
    if pd.isna(isin) or str(isin).strip() == "":
        return None
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={str(isin).strip()}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            quotes = data.get('quotes', [])
            if quotes:
                for q in quotes:
                    if 'symbol' in q:
                        return q['symbol']
    except Exception:
        pass
    return None

def fetch_live_prices(df):
    import requests
    live_prices = []
    updated_tickers = []
    fmp_key = st.session_state.get('fmp_api_key_input', '').strip()
    
    for i, row in df.iterrows():
        ticker = row.get('Ticker', '')
        isin = row.get('ISIN', '')
        
        # Automatische ISIN -> Ticker Suche
        if pd.isna(ticker) or str(ticker).strip() == "":
            found_ticker = search_ticker_by_isin(isin)
            if found_ticker:
                ticker = found_ticker
            else:
                live_prices.append(None)
                updated_tickers.append(ticker)
                continue
                
        t = str(ticker).strip()
        price = None
        
        if fmp_key:
            try:
                url = f"https://financialmodelingprep.com/api/v3/quote/{t}?apikey={fmp_key}"
                resp = requests.get(url, timeout=3)
                if resp.status_code == 200:
                    data = resp.json()
                    if data and len(data) > 0 and 'price' in data[0]:
                        price = data[0]['price']
            except Exception:
                pass
                
        if price is None:
            try:
                ticker_obj = yf.Ticker(t)
                info = ticker_obj.fast_info
                price = info.get('lastPrice', None)
                if price is None or price == 0:
                    hist = ticker_obj.history(period="1d")
                    if not hist.empty:
                        price = hist['Close'].iloc[-1]
            except Exception:
                pass
                
        if price:
            live_prices.append(price)
        else:
            live_prices.append(None)
            
        updated_tickers.append(ticker)
        
    return live_prices, updated_tickers

def berechne_portfolio_metriken(df):
    if df.empty:
        return 0.0, 0.0, 0.0

    kaufwert = df['Kaufpreis'] + df['Orderkost']
    gesamt_kaufwert = kaufwert.sum()
    
    # Nutze Live_Gesamtwert wenn vorhanden, ansonsten den Wert aus der CSV
    if 'Live_Gesamtwert' in df.columns and st.session_state.live_data_fetched:
        # Fülle fehlende Live-Werte mit dem alten Wert auf
        aktueller_wert = df['Live_Gesamtwert'].fillna(df['Wert'])
    else:
        aktueller_wert = df['Wert']
        
    gesamtwert = aktueller_wert.sum()
    gesamt_gewinn = gesamtwert - gesamt_kaufwert
    
    if gesamt_kaufwert > 0:
        gesamt_performance_prozent = (gesamt_gewinn / gesamt_kaufwert) * 100
    else:
        gesamt_performance_prozent = 0.0
        
    return gesamtwert, gesamt_gewinn, gesamt_performance_prozent

def prepare_anonymized_portfolio_data(df, gesamtwert):
    if df.empty or gesamtwert <= 0:
        return ""
    
    anonymized_data = [f"Gesamtwert des Portfolios: {gesamtwert:,.2f} EUR\n"]
    for _, row in df.iterrows():
        name = row.get('Wertpapier', 'Unbekannt')
        ticker = row.get('Ticker', '')
        if pd.isna(ticker) or str(ticker).strip() == "":
            identifier = name
        else:
            identifier = f"{name} ({ticker})"
            
        kaufwert = row['Kaufpreis'] + row['Orderkost']
        
        if 'Live_Kurs' in df.columns and pd.notna(row.get('Live_Kurs')):
            akt_wert = row['St_Nom'] * row['Live_Kurs']
        else:
            akt_wert = row['Wert']
            
        gewichtung = (akt_wert / gesamtwert * 100) if gesamtwert > 0 else 0
        gewinn = akt_wert - kaufwert
        performance = (gewinn / kaufwert * 100) if kaufwert > 0 else 0
        
        anonymized_data.append(f"- Position: {identifier} | Anteil am Portfolio: {gewichtung:.2f}% | Performance bisher: {performance:.2f}%")
        
    return "\n".join(anonymized_data)

@st.cache_data(show_spinner=False, ttl=300)
def fetch_portfolio_history(df, period, fmp_key=None):
    import yfinance as yf
    import requests
    from datetime import datetime, timedelta
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()
        
    period_mapping = {
        "1 Tag": ("1d", "5m"),
        "1 Woche": ("5d", "1h"),
        "1 Monat": ("1mo", "1d"),
        "3 Monate": ("3mo", "1d"),
        "1 Jahr": ("1y", "1d"),
        "10 Jahre": ("10y", "1d"),
        "Maximal": ("max", "1d")
    }
    yf_period, yf_interval = period_mapping.get(period, ("1y", "1d"))
    
    series_list = []
    constant_assets = {}
    
    for i, row in df.iterrows():
        ticker = str(row.get('Ticker', '')).strip()
        name = str(row.get('Wertpapier', f'Position {i}'))
        st_nom = row.get('St_Nom', 0)
        konstant_wert = row.get('Live_Gesamtwert', row.get('Wert', 0))
        if pd.isna(konstant_wert):
            konstant_wert = row.get('Wert', 0)
            
        if ticker:
            use_fmp = False
            fmp_hist = pd.DataFrame()
            if fmp_key and period != "1 Tag":
                try:
                    today = datetime.today()
                    if period == "1 Woche":
                        start_date = today - timedelta(days=7)
                    elif period == "1 Monat":
                        start_date = today - timedelta(days=30)
                    elif period == "3 Monate":
                        start_date = today - timedelta(days=90)
                    elif period == "1 Jahr":
                        start_date = today - timedelta(days=365)
                    elif period == "10 Jahre":
                        start_date = today - timedelta(days=3650)
                    else:
                        start_date = today - timedelta(days=10000)
                        
                    start_str = start_date.strftime("%Y-%m-%d")
                    end_str = today.strftime("%Y-%m-%d")
                    
                    url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{ticker}?from={start_str}&to={end_str}&apikey={fmp_key}"
                    resp = requests.get(url, timeout=5)
                    if resp.status_code == 200:
                        data = resp.json()
                        if 'historical' in data and len(data['historical']) > 0:
                            fmp_df = pd.DataFrame(data['historical'])
                            fmp_df['date'] = pd.to_datetime(fmp_df['date'])
                            fmp_df.set_index('date', inplace=True)
                            fmp_df.sort_index(inplace=True)
                            if len(fmp_df) > 1 and 'close' in fmp_df.columns:
                                fmp_hist = fmp_df[['close']].rename(columns={'close': 'Close'})
                                use_fmp = True
                except Exception:
                    pass
                    
            try:
                if use_fmp:
                    hist = fmp_hist
                else:
                    t_obj = yf.Ticker(ticker)
                    hist = t_obj.history(period=yf_period, interval=yf_interval)
                    
                if len(hist) > 1 and 'Close' in hist.columns:
                    if hist.index.tz is not None:
                        hist.index = hist.index.tz_localize(None)
                    wert_series = hist['Close'] * st_nom
                    wert_series.name = name
                    series_list.append(wert_series)
                else:
                    constant_assets[name] = konstant_wert
            except:
                constant_assets[name] = konstant_wert
        else:
            constant_assets[name] = konstant_wert
            
    if not series_list:
        end_date = pd.Timestamp.today(tz='UTC')
        if period == "1 Tag":
            dates = pd.date_range(end=end_date, periods=2, freq='12h')
        elif period == "1 Woche":
            dates = pd.date_range(end=end_date, periods=5, freq='B')
        elif period == "1 Monat":
            dates = pd.date_range(end=end_date, periods=20, freq='B')
        elif period == "3 Monate":
            dates = pd.date_range(end=end_date, periods=60, freq='B')
        elif period == "10 Jahre":
            dates = pd.date_range(end=end_date, periods=2520, freq='B')
        else:
            dates = pd.date_range(end=end_date, periods=252, freq='B')
        hist_df = pd.DataFrame(index=dates)
    else:
        hist_df = pd.concat(series_list, axis=1, sort=False)
        hist_df = hist_df.sort_index()
        hist_df = hist_df.ffill().bfill()
        
    portfolio_history = hist_df.sum(axis=1) if not hist_df.empty else pd.Series(0, index=hist_df.index)
    total_constant = sum(constant_assets.values())
    portfolio_history += total_constant
    
    result_total = portfolio_history.reset_index()
    result_total.columns = ['Datum', 'Wert']
    result_total['Asset'] = 'Gesamt-Portfolio'
    
    for name, val in constant_assets.items():
        hist_df[name] = val
        
    hist_df = hist_df.reset_index()
    hist_df = hist_df.rename(columns={hist_df.columns[0]: 'Datum'})
    
    result_individual = hist_df.melt(id_vars=['Datum'], var_name='Asset', value_name='Wert')
    
    if isinstance(result_total['Datum'].dtype, pd.DatetimeTZDtype):
        result_total['Datum'] = result_total['Datum'].dt.tz_localize(None)
    if isinstance(result_individual['Datum'].dtype, pd.DatetimeTZDtype):
        result_individual['Datum'] = result_individual['Datum'].dt.tz_localize(None)
        
    return result_total, result_individual


def generate_search_context(llm_config, prompt_text, is_portfolio_analysis=False):
    import requests
    import json
    import re
    from prompts import get_search_context_prompt
    
    system_instruction, user_message = get_search_context_prompt(prompt_text, is_portfolio_analysis)
    
    headers = {"Content-Type": "application/json"}
    if llm_config.get('api_key'):
        headers["Authorization"] = f"Bearer {llm_config['api_key']}"
        
    payload = {
        "model": llm_config.get('model', 'local-model'),
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_message}
        ],
        "stream": False
    }
    
    # Handle Anthropic Claude API format if selected
    if llm_config.get('provider') == 'Anthropic Claude':
        headers["x-api-key"] = llm_config.get('api_key', '')
        headers["anthropic-version"] = "2023-06-01"
        if "Authorization" in headers:
            del headers["Authorization"]
        
        payload = {
            "model": llm_config.get('model', 'claude-3-5-sonnet-20240620'),
            "system": system_instruction,
            "messages": [{"role": "user", "content": user_message}],
            "max_tokens": 1024
        }
        url = "https://api.anthropic.com/v1/messages"
    else:
        # OpenAI compatible (Local/LM Studio/Ollama)
        base_url = llm_config.get('base_url') or 'http://localhost:11434/v1'
        url = base_url.rstrip('/') + '/chat/completions'
    
    result = {"web_queries": [], "tickers": []}
    
    if llm_config.get('provider') == 'Google Gemini':
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=llm_config.get('api_key', ''))
            response = client.models.generate_content(
                model=llm_config.get('model', 'gemini-2.5-flash'),
                contents=user_message,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.2
                )
            )
            raw_output = response.text.strip()
            
            json_match = re.search(r"\{.*?\}", raw_output, re.DOTALL)
            if json_match:
                raw_output = json_match.group(0)
                
            parsed = json.loads(raw_output)
            result["web_queries"] = parsed.get("web_queries", [])[:2]
            result["tickers"] = parsed.get("tickers", [])[:3]
        except Exception as e:
            print("Fehler bei generate_search_context (Gemini):", e)
            result["web_queries"] = [prompt_text]
        return result

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if llm_config.get('provider') == 'Anthropic Claude':
            raw_output = data['content'][0]['text'].strip()
        else:
            raw_output = data['choices'][0]['message']['content'].strip()
            
        if "</think>" in raw_output:
            raw_output = raw_output.split("</think>")[-1].strip()
            
        json_match = re.search(r"\{.*?\}", raw_output, re.DOTALL)
        if json_match:
            raw_output = json_match.group(0)
            
        parsed = json.loads(raw_output)
        result["web_queries"] = parsed.get("web_queries", [])[:2]
        result["tickers"] = parsed.get("tickers", [])[:3]
    except Exception as e:
        print("Fehler bei generate_search_context:", e)
        result["web_queries"] = [prompt_text]
        
    return result

def fetch_custom_web_search(queries, include_macro=True):
    if not queries and not include_macro:
        return ""
    
    context_lines = []
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text("Aktuelle Marktlage Börse Zinsen Inflation", max_results=2))
            if results:
                context_lines.append("- Globale Makroökonomie (Zinsen, Inflation):")
                for r in results:
                    context_lines.append(f"  * {r['title']} (Quelle: {r.get('href', '')}): {r['body'][:150]}...")
    except:
        pass
        
    for q in queries:
        try:
            from ddgs import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(q, max_results=3))
                if results:
                    context_lines.append(f"- Websuche für '{q}':")
                    for r in results:
                        context_lines.append(f"  * {r['title']} (Quelle: {r.get('href', '')}): {r['body'][:150]}...")
        except Exception as e:
            if "429" in str(e) or "RateLimit" in str(e):
                return "RATE_LIMIT"
            pass
            
    return "\\n".join(context_lines) if context_lines else ""

def fetch_ticker_live_data(tickers):
    if not tickers:
        return ""
    
    import yfinance as yf
    lines = []
    lines.append("- Offizielle Live-Kursdaten (Yahoo Finance):")
    for t in tickers:
        try:
            ticker = yf.Ticker(t)
            info = ticker.info
            price = info.get('currentPrice') or info.get('regularMarketPrice')
            currency = info.get('currency', 'Unbekannt')
            if price:
                lines.append(f"  * {t}: Aktueller Kurs = {price} {currency}")
            
            news = ticker.news
            if news:
                headlines = [f"{n['title']} (URL: {n.get('link', '')})" for n in news[:2] if 'title' in n]
                if headlines:
                    lines.append(f"  * {t} News: " + " | ".join(headlines))
        except:
            lines.append(f"  * {t}: Keine Live-Daten gefunden.")
            
    return "\\n".join(lines)

def fetch_market_context(df):
    if df.empty:
        return ""
    
    sort_col = 'Live_Gesamtwert' if 'Live_Gesamtwert' in df.columns else 'Wert'
    df_sorted = df.sort_values(by=sort_col, ascending=False).head(5)
    context_lines = []
    
    valid_tickers = []
    names = []
    
    for _, row in df_sorted.iterrows():
        name = str(row.get('Wertpapier', '')).strip()
        if name:
            names.append(name)
            
        ticker = str(row.get('Ticker', '')).strip()
        if ticker:
            valid_tickers.append(ticker)
            try:
                news = yf.Ticker(ticker).news
                if news:
                    headlines = [f"{n['title']} (URL: {n.get('link', '')})" for n in news[:3] if 'title' in n]
                    if headlines:
                        context_lines.append(f"- {ticker} News: " + " | ".join(headlines))
            except:
                pass
                
    # Search DDG with the top names or tickers
    search_terms = valid_tickers if valid_tickers else names
    if search_terms:
        # Beschränke auf die Top 3, damit die Suchanfrage nicht zu lang und verwirrend wird
        query_terms = " ".join(search_terms[:3])
        search_query = f"{query_terms} marktentwicklung finanzen"
        try:
            from ddgs import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(search_query, max_results=2))
                if results:
                    context_lines.append("- Spezifische Markttrends (Web):")
                    for r in results:
                        context_lines.append(f"  * {r['title']} (Quelle: {r.get('href', '')}): {r['body'][:150]}...")
        except:
            pass
            
    # Globale Makro-Trends (Immer abrufen!)
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text("Aktuelle Marktlage Börse Zinsen Inflation", max_results=3))
            if results:
                context_lines.append("- Globale Makroökonomie (Zinsen, Inflation, Krisen):")
                for r in results:
                    context_lines.append(f"  * {r['title']} (Quelle: {r.get('href', '')}): {r['body'][:150]}...")
    except:
        pass
        
    # Allgemeine Indizes News (S&P 500)
    try:
        news_sp500 = yf.Ticker("^GSPC").news
        if news_sp500:
            headlines = [f"{n['title']} (URL: {n.get('link', '')})" for n in news_sp500[:3] if 'title' in n]
            if headlines:
                context_lines.append(f"- Leitindizes (S&P 500) News: " + " | ".join(headlines))
    except:
        pass
            
    return "\n".join(context_lines) if context_lines else ""

def fetch_chat_search_context(query):
    # Wenn die Frage sehr kurz ist (z.B. nur "Tesla"), hängen wir "Aktie News" an.
    # Bei ganzen Sätzen (z.B. "Welche ETFs bietet die Deka an?") nutzen wir die Frage unverfälscht,
    # da ein Anhängen von englischen Begriffen wie "news finance" die Suchmaschine verwirrt.
    words = query.strip().split()
    if len(words) <= 2:
        search_query = f"{query} Aktie Finanzen News"
    else:
        search_query = query
        
    context_lines = []
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(search_query, max_results=3))
            if results:
                for r in results:
                    context_lines.append(f"- {r['title']} (Quelle: {r.get('href', 'Unbekannt')}): {r['body'][:200]}...")
    except:
        pass
    return "\n".join(context_lines) if context_lines else ""

def clean_for_pdf(text):
    text = text.replace('€', 'EUR')
    return text.encode('latin-1', 'ignore').decode('latin-1')

@st.cache_data(show_spinner=False)
def export_text_to_pdf(text):
    import markdown
    from fpdf import FPDF
    md_html = markdown.markdown(text, extensions=['tables'])
    md_html = md_html.replace('<table>', '<table border="1" width="100%">')
    md_html = md_html.replace('<th>', '<th bgcolor="#ecf0f1">')
    
    full_html = f"""
    <h1 align="center">KI Antwort</h1>
    <br>
    {md_html}
    """
    clean_html = clean_for_pdf(full_html)
    import re
    # Remove emojis and high unicode symbols that break default FPDF fonts
    # Keep ASCII, Latin-1, Latin Extended-A, Euro sign, smart quotes, dashes
    clean_html = re.sub(r'[^\x00-\x7F\xA0-\xFF\u0100-\u017F\u20AC\u2018-\u201D\u2013\u2014]', '', clean_html)
    
    pdf = FPDF()
    pdf.add_page()
    try:
        pdf.write_html(clean_html)
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            pdf_bytes = bytes(pdf.output(dest='S'))
        return pdf_bytes
    except Exception as e:
        print("PDF HTML Error:", e)
        # Fallback auf reinen Text ohne Formatierung
        try:
            pdf = FPDF()
            pdf.add_page()
            import re
            plain_text = re.sub('<[^<]+>', '', full_html)
            plain_text = clean_for_pdf(plain_text)
            plain_text = re.sub(r'[^\x00-\x7F\xA0-\xFF\u0100-\u017F\u20AC\u2018-\u201D\u2013\u2014]', '', plain_text)
            pdf.set_font("Helvetica", size=11)
            pdf.multi_cell(0, 5, plain_text)
            return bytes(pdf.output(dest='S'))
        except Exception as e2:
            print("PDF Fallback Error:", e2)
            return None

def export_full_report_to_pdf(portfolio_df, gesamtwert, summary_text):
    import markdown
    import tempfile
    import os
    import plotly.express as px
    from fpdf import FPDF
    
    # 1. Generate Chart Image
    fig = px.pie(
        portfolio_df, 
        values='_Plot_Wert' if '_Plot_Wert' in portfolio_df.columns else 'Wert', 
        names='Wertpapier', 
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    fig.update_layout(
        showlegend=True,
        paper_bgcolor='white',
        plot_bgcolor='white',
        font=dict(color='black')
    )
    
    tmp_img_path = os.path.join(tempfile.gettempdir(), "portfolio_chart.png")
    fig.write_image(tmp_img_path, width=600, height=400)
    
    # 2. Build HTML
    # 2. Build HTML
    full_html = f"""
    <h1 align="center">Dein Portfolio Gesamtreport</h1>
    <h2 align="center">Gesamtwert: {gesamtwert:,.2f} EUR</h2>
    <br>
    <div align="center">
        <img src="{tmp_img_path}" width="400">
    </div>
    <br>
    <h2>Aktuelle Positionen</h2>
    <table border="1" width="100%">
        <thead>
            <tr>
                <th bgcolor="#ecf0f1" width="40%"><b>Wertpapier</b></th>
                <th bgcolor="#ecf0f1" width="20%"><b>Anteile</b></th>
                <th bgcolor="#ecf0f1" width="20%"><b>Akt. Kurs</b></th>
                <th bgcolor="#ecf0f1" width="20%"><b>Gesamtwert</b></th>
            </tr>
        </thead>
        <tbody>
"""
    for _, row in portfolio_df.iterrows():
        wp = row.get('Wertpapier', '')
        ant = row.get('St_Nom', 0)
        kurs = row.get('Aktueller Kurs', row.get('Ø Kaufkurs', 0))
        wert = row.get('Akt. Wert', row.get('Wert', 0))
        full_html += f'<tr><td>{wp}</td><td>{ant:,.2f}</td><td>{kurs:,.2f} EUR</td><td>{wert:,.2f} EUR</td></tr>'
        
    full_html += """
        </tbody>
    </table>
    <br>
    <h2>KI Executive Summary</h2>
"""
    # Generate Markdown and force table borders for FPDF
    md_html = markdown.markdown(summary_text, extensions=['tables'])
    md_html = md_html.replace('<table>', '<table border="1" width="100%">')
    md_html = md_html.replace('<th>', '<th bgcolor="#ecf0f1">')
    
    full_html += md_html
    
    clean_html = clean_for_pdf(full_html)
    import re
    # Remove emojis and high unicode symbols that break default FPDF fonts
    # Keep ASCII, Latin-1, Latin Extended-A, Euro sign, smart quotes, dashes
    clean_html = re.sub(r'[^\x00-\x7F\xA0-\xFF\u0100-\u017F\u20AC\u2018-\u201D\u2013\u2014]', '', clean_html)
    
    pdf = FPDF()
    pdf.add_page()
    try:
        pdf.write_html(clean_html)
        pdf_bytes = bytes(pdf.output(dest='S'))
    except Exception as e:
        print('PDF Error:', e)
        # Fallback auf reinen Text
        try:
            pdf = FPDF()
            pdf.add_page()
            import re
            plain_text = re.sub('<[^<]+>', '', full_html)
            plain_text = clean_for_pdf(plain_text)
            plain_text = re.sub(r'[^\x00-\x7F\xA0-\xFF\u0100-\u017F\u20AC\u2018-\u201D\u2013\u2014]', '', plain_text)
            pdf.set_font("Helvetica", size=11)
            pdf.multi_cell(0, 5, plain_text)
            pdf_bytes = bytes(pdf.output(dest='S'))
        except Exception as e2:
            print('PDF Fallback Error:', e2)
            pdf_bytes = None
    finally:
        if os.path.exists(tmp_img_path):
            os.remove(tmp_img_path)
            
    return pdf_bytes


def get_llm_response_stream(config, history, use_google_grounding=False, retries=1):
    import time
    import json
    from prompts import get_advisor_system_prompt
    
    system_instruction = get_advisor_system_prompt()
    
    for attempt in range(retries + 1):
        try:
            if config['provider'] == 'Google Gemini':
                from google import genai
                from google.genai import types
                client = genai.Client(api_key=config['api_key'])
                contents = []
                for idx, msg in enumerate(history):
                    role = "user" if msg['role'] == 'user' else "model"
                    if idx < len(history) - 1 and role == "user" and 'display' in msg:
                        content_to_send = msg['display']
                    else:
                        content_to_send = msg['content']
                    contents.append(
                        types.Content(role=role, parts=[types.Part.from_text(text=content_to_send)])
                    )
                
                genai_config = types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    max_output_tokens=8192
                )
                
                response_stream = client.models.generate_content_stream(
                    model=config.get('model', 'gemini-2.5-flash'),
                    contents=contents,
                    config=genai_config
                )
                
                def gen(c, stream):
                    try:
                        for chunk in stream:
                            if chunk.text:
                                yield chunk.text
                    except Exception as e:
                        yield f"\n\n*[Verbindung zur KI unterbrochen: {e}]*"
                return gen(client, response_stream), None
            elif config['provider'] == 'Anthropic Claude':
                import requests
                import json
                headers = {
                    "x-api-key": config['api_key'],
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                }
                
                messages = []
                for idx, msg in enumerate(history):
                    role = "user" if msg['role'] == 'user' else "assistant"
                    
                    if idx < len(history) - 1 and role == "user" and 'display' in msg:
                        content_to_send = msg['display']
                    else:
                        content_to_send = msg['content']
                        
                    messages.append({"role": role, "content": content_to_send})
                    
                payload = {
                    "model": config.get('model', 'claude-sonnet-4-6'),
                    "system": system_instruction,
                    "messages": messages,
                    "stream": True,
                    "max_tokens": 8192
                }
                
                url = 'https://api.anthropic.com/v1/messages'
                response = requests.post(url, json=payload, headers=headers, stream=True, timeout=300)
                response.raise_for_status()
                
                def claude_gen(resp):
                    try:
                        with resp:
                            for line in resp.iter_lines():
                                if line:
                                    line = line.decode('utf-8')
                                    if line.startswith('data: '):
                                        data_str = line[6:]
                                        if data_str.strip() == '[DONE]':
                                            continue
                                        try:
                                            data = json.loads(data_str)
                                            if data.get('type') == 'content_block_delta' and data.get('delta', {}).get('type') == 'text_delta':
                                                yield data['delta']['text']
                                        except Exception:
                                            pass
                    except Exception as e:
                        yield f"\n\n*[Verbindung zur KI unterbrochen: {e}]*"
                return claude_gen(response), None
            else:
                import requests
                headers = {"Content-Type": "application/json"}
                if config.get('api_key'):
                    headers["Authorization"] = f"Bearer {config['api_key']}"
                
                messages = [{"role": "system", "content": system_instruction}]
                for idx, msg in enumerate(history):
                    role = "user" if msg['role'] == 'user' else "assistant"
                    
                    if idx < len(history) - 1 and role == "user" and 'display' in msg:
                        content_to_send = msg['display']
                    else:
                        content_to_send = msg['content']
                        
                    messages.append({"role": role, "content": content_to_send})
                    
                payload = {
                    "model": config.get('model', 'local-model'),
                    "messages": messages,
                    "stream": True
                }
                
                url = config.get('base_url', 'http://localhost:11434/v1').rstrip('/') + '/chat/completions'
                response = requests.post(url, json=payload, headers=headers, stream=True, timeout=300)
                response.raise_for_status()
                
                def local_gen(resp):
                    reasoning_started = False
                    reasoning_ended = False
                    try:
                        with resp:
                            for line in resp.iter_lines():
                                if line:
                                    line = line.decode('utf-8')
                                    if line.startswith('data: '):
                                        data_str = line[6:]
                                        if data_str.strip() == '[DONE]':
                                            break
                                        try:
                                            data = json.loads(data_str)
                                            delta = data['choices'][0].get('delta', {})
                                            
                                            reasoning = delta.get('reasoning_content')
                                            if reasoning:
                                                if not reasoning_started:
                                                    yield "🤔 **Gedankengang der KI:**\n\n"
                                                    reasoning_started = True
                                                yield reasoning
                                                
                                            content = delta.get('content')
                                            if content:
                                                if reasoning_started and not reasoning_ended:
                                                    yield "\n\n---\n\n**Antwort:**\n\n"
                                                    reasoning_ended = True
                                                yield content
                                        except Exception:
                                            pass
                    except Exception as e:
                        yield f"\n\n*[Verbindung zur KI unterbrochen: {e}]*"
                return local_gen(response), None
        except Exception as e:
            error_msg = str(e)
            
            # Sauberes Error-Handling für Google API Rate Limits (429)
            if "429" in error_msg and "RESOURCE_EXHAUSTED" in error_msg:
                import re
                retry_match = re.search(r"retry in ([\d\.]+)s", error_msg)
                if retry_match:
                    seconds = int(float(retry_match.group(1))) + 1
                    user_msg = f"⚠️ **API Limit erreicht (429 Rate Limit)**\nDas Limit deines aktuellen API-Schlüssels (z.B. Google Gemini Free-Tier) wurde erreicht. Bitte warte **{seconds} Sekunden** und versuche es dann erneut."
                else:
                    user_msg = "⚠️ **API Limit erreicht (429 Rate Limit)**\nDas Limit deines aktuellen API-Schlüssels ist aufgebraucht. Bitte warte einen Moment oder prüfe dein Kontingent."
                return None, user_msg
                
            if attempt < retries:
                import time
                time.sleep(2)
                continue
                
            return None, f"Fehler bei der KI-Analyse nach {retries+1} Versuchen: {error_msg}"

@st.cache_data(show_spinner=False, ttl=300)
def get_available_models(provider, api_key, base_url=""):
    models = []
    if provider == 'Google Gemini' and api_key:
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            # Try to list models
            for m in client.models.list():
                if 'generateContent' in m.supported_generation_methods:
                    models.append(m.name.replace('models/', ''))
        except Exception:
            # Fallback
            models = ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-flash", "gemini-1.5-pro"]
    elif provider == 'OpenAI / Local' and base_url:
        try:
            import requests
            headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
            url = base_url.rstrip('/') + '/models'
            response = requests.get(url, headers=headers, timeout=3)
            if response.status_code == 200:
                data = response.json()
                if 'data' in data:
                    models = [m['id'] for m in data['data']]
        except Exception:
            # Fallback
            models = ["llama3", "mistral", "local-model"]
    elif provider == 'Anthropic Claude':
        if api_key:
            try:
                import requests
                headers = {
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01"
                }
                url = "https://api.anthropic.com/v1/models"
                response = requests.get(url, headers=headers, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if 'data' in data:
                        models = [m['id'] for m in data['data']]
            except Exception:
                pass
        if not models:
            models = ["claude-sonnet-4-6", "claude-3-7-sonnet-20250219", "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"]
            
    if not models:
        if provider == 'Google Gemini':
            models = ["gemini-2.5-flash"]
        elif provider == 'Anthropic Claude':
            models = ["claude-sonnet-4-6"]
        else:
            models = ["llama3", "local-model"]
        
    return models

# --- Sidebar: Upload und Manuelle Eingabe ---
with st.sidebar:
    st.title("📂 Daten Eingabe")
    
# 1. Datei-Upload
    st.subheader("CSV hochladen")
    uploaded_file = st.file_uploader("Wähle deine Portfolio CSV-Datei", type=['csv'], key=f"uploader_{st.session_state.uploader_key}")
    
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

                    # Stelle sicher, dass Ticker-Spalte existiert
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
            
    st.divider()
    
    # 2. Manuelle Eingabe
    st.subheader("Position hinzufügen")
    with st.form("add_position_form"):
        col1, col2 = st.columns(2)
        with col1:
            wertpapier = st.text_input("Wertpapier Name")
            isin = st.text_input("ISIN")
            ticker = st.text_input("Yahoo Ticker (z.B. AAPL)")
            st_nom = st.number_input("Stück/Nominal", min_value=0.0, format="%.4f")
            kaufpreis = st.number_input("Kaufwert (Gesamt)", min_value=0.0, format="%.2f")
            boersenpl = st.text_input("Börsenplatz", value="XETRA")
        with col2:
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

# --- Hauptbereich ---
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

st.divider()

# --- KI Analyse Bereich ---
st.subheader("🤖 KI-gestützte Portfolio-Analyse")

# Construct llm_config from session state for early checks
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

if st.session_state.portfolio_df.empty:
    st.info("Füge dem Portfolio erst Positionen hinzu, um eine Analyse durchzuführen.")
elif not (llm_config.get('api_key') or llm_config['provider'] != 'Google Gemini'):
    st.error("Bitte lege im Zahnrad (unten) einen API-Key fest, um den Chat zu aktivieren!")
else:
    # Zeige Chat Verlauf
    for i, msg in enumerate(st.session_state.chat_history):
        if i == 0 and msg['role'] == 'user' and 'display' not in msg:
            with st.chat_message("user"):
                st.write("*(Portfolio-Daten zur Analyse übergeben)*")
        else:
            with st.chat_message(msg['role']):
                if msg['role'] == 'user' and 'display' in msg:
                    st.markdown(msg['display'])
                else:
                    if msg.get('reasoning'):
                        with st.expander("🤔 Gedankengang der KI (abgeschlossen)"):
                            st.markdown(msg['reasoning'])
                    st.markdown(msg['content'])
                    
                    if msg['role'] == 'model':
                        try:
                            from st_copy_to_clipboard import st_copy_to_clipboard
                            st_copy_to_clipboard(msg['content'], before_copy_label="📋 Antwort kopieren", after_copy_label="✅ Kopiert!", key=f"copy_{i}")
                        except ImportError:
                            pass
                        
                        if i == len(st.session_state.chat_history) - 1 and "[Verbindung zur KI unterbrochen:" in msg['content']:
                            if st.button("🔄 Antwort neu generieren", key=f"retry_gen_{i}"):
                                st.session_state.chat_history.pop()
                                st.rerun()

# Chat Eingabe und Buttons (Immer gerendert, aber ggf. disabled)
status_container = st.empty()
model_response_placeholder = st.empty()

with st.bottom:
    cancel_placeholder = st.empty()

    cols = st.columns([0.4, 0.1, 0.25, 0.25])
    col_model = cols[0]
    col_config = cols[1]

    with col_config:
        with st.popover("⚙️"):
            with st.expander("🤖 KI Provider & Keys", expanded=True):
                llm_provider = st.selectbox("LLM Provider", ["Google Gemini", "Anthropic Claude", "OpenAI / Local"], key="llm_provider_input")
                if llm_provider == "Google Gemini":
                    gemini_api_key = st.text_input("Gemini API Key", type="password", value=st.session_state._backup_gemini)
                    if gemini_api_key != st.session_state._backup_gemini:
                        st.session_state._backup_gemini = gemini_api_key
                        st.rerun()
                    current_api_key = st.session_state._backup_gemini
                    current_base_url = None
                elif llm_provider == "Anthropic Claude":
                    claude_api_key = st.text_input("Claude API Key", type="password", value=st.session_state._backup_claude)
                    if claude_api_key != st.session_state._backup_claude:
                        st.session_state._backup_claude = claude_api_key
                        st.rerun()
                    current_api_key = st.session_state._backup_claude
                    current_base_url = None
                else:
                    local_base_url = st.text_input("API Base URL", value=st.session_state._backup_url)
                    if local_base_url != st.session_state._backup_url:
                        st.session_state._backup_url = local_base_url
                        st.rerun()
                    local_api_key = st.text_input("API Key (Optional)", type="password", value=st.session_state._backup_local_key)
                    if local_api_key != st.session_state._backup_local_key:
                        st.session_state._backup_local_key = local_api_key
                        st.rerun()
                    current_api_key = st.session_state._backup_local_key
                    current_base_url = st.session_state._backup_url
            with st.expander("📈 Datenquelle", expanded=True):
                fmp_api_key = st.text_input("FMP API Key (Optional)", type="password", key="fmp_api_key_input")
                st.session_state.fmp_api_key = fmp_api_key

    if llm_provider in ["Google Gemini", "Anthropic Claude"]:
        available_models = get_available_models(llm_provider, current_api_key) if current_api_key else (["gemini-2.5-flash"] if llm_provider == "Google Gemini" else ["claude-sonnet-4-6"])
    else:
        available_models = get_available_models(llm_provider, current_api_key, current_base_url) if current_base_url else ["llama3", "local-model"]

    with col_model:
        if available_models:
            llm_model = st.selectbox("Modell", available_models, index=0, label_visibility="collapsed", key="llm_model_input")
        else:
            llm_model = st.selectbox("Modell", ["Keine Modelle gefunden"], disabled=True, label_visibility="collapsed", key="llm_model_input")

    llm_config = {"provider": llm_provider, "api_key": current_api_key, "base_url": current_base_url, "model": llm_model}
    
    if is_ready:
        if len(st.session_state.chat_history) == 0:
            with cols[2]:
                use_web_search = st.checkbox("🌐 News & Webdaten", value=True)
            with cols[3]:
                include_portfolio = st.checkbox("📊 Portfolio-Daten", value=True)
            trigger_auto = st.button("Portfolio automatisch analysieren", type="primary", width="stretch")
            use_chat_search = use_web_search
        else:
            trigger_auto = False
            use_web_search = False
            with cols[2]:
                use_chat_search = st.toggle("🌐 Live-Websuche", value=True)
                include_portfolio = st.toggle("📊 Portfolio anhängen", value=False)
            with cols[3]:
                if 'pdf_report_bytes' not in st.session_state:
                    st.session_state.pdf_report_bytes = None
                    
                if st.session_state.pdf_report_bytes:
                    st.download_button(label="📥 PDF herunterladen", data=st.session_state.pdf_report_bytes, file_name="Portfolio_Gesamtreport.pdf", mime="application/pdf", width="stretch")
                else:
                    is_generating = len(st.session_state.chat_history) > 0 and st.session_state.chat_history[-1]['role'] == 'user'
                    if st.button("📄 PDF generieren", width="stretch", disabled=is_generating):
                        with st.spinner("KI verfasst das Executive Summary..."):
                            from prompts import get_summary_prompt
                            summary_prompt = get_summary_prompt()
                            history_for_summary = st.session_state.chat_history.copy()
                            history_for_summary.append({"role": "user", "content": summary_prompt})
                            
                            summary_gen, err = get_llm_response_stream(llm_config, history_for_summary, use_google_grounding=False)
                            if summary_gen:
                                summary_text = ""
                                for chunk in summary_gen:
                                    summary_text += chunk
                                    status_container.markdown("### 📝 KI verfasst Executive Summary...\n" + summary_text)
                                    
                                with st.spinner("Erzeuge PDF mit Diagramm und Tabelle..."):
                                    pdf_bytes = export_full_report_to_pdf(st.session_state.portfolio_df, gesamtwert, summary_text)
                                    if pdf_bytes:
                                        st.session_state.pdf_report_bytes = pdf_bytes
                                        st.rerun()
                                    else:
                                        st.error("Fehler bei der PDF-Erstellung (fpdf/kaleido)")
                            else:
                                st.error(f"Fehler bei der Zusammenfassung: {err}")
    else:
        trigger_auto = False
        use_web_search = False
        include_portfolio = False
        use_chat_search = False
        with cols[2]:
            st.checkbox("🌐 News & Webdaten", value=False, disabled=True)
        with cols[3]:
            st.checkbox("📊 Portfolio-Daten", value=False, disabled=True)
        st.button("Portfolio automatisch analysieren", type="primary", width="stretch", disabled=True)

if len(st.session_state.chat_history) == 0:
    user_q = st.chat_input("...oder stelle direkt eine allgemeine oder spezifische Frage.", key="main_chat", disabled=not is_ready)
else:
    user_q = st.chat_input("Stelle eine Rückfrage...", key="main_chat", disabled=not is_ready)
    
if trigger_auto or user_q:
    with cancel_placeholder.container():
        cancel_col, _ = st.columns([0.25, 0.75])
        with cancel_col:
            if st.button("⏹ Vorbereitung Abbrechen", key="cancel_pre_search"):
                st.rerun()
            
    if trigger_auto:
        with status_container.container():
            with st.status("Aktualisiere Portfolio-Kurse über Yahoo Finance...", expanded=True) as status:
                live_prices, updated_tickers = fetch_live_prices(st.session_state.portfolio_df)
                st.session_state.portfolio_df['Ticker'] = updated_tickers
                st.session_state.portfolio_df['Live_Kurs'] = live_prices
                st.session_state.portfolio_df['Live_Gesamtwert'] = st.session_state.portfolio_df['St_Nom'] * st.session_state.portfolio_df['Live_Kurs']
                st.session_state.live_data_fetched = True
                gesamtwert, _, _ = berechne_portfolio_metriken(st.session_state.portfolio_df)
                status.update(label="Portfolio-Kurse erfolgreich aktualisiert.", state="complete")

    portfolio_text = prepare_anonymized_portfolio_data(st.session_state.portfolio_df, gesamtwert)
    
    if trigger_auto:
        from prompts import get_auto_analysis_initial_prompt
        initial_prompt = get_auto_analysis_initial_prompt(portfolio_text if include_portfolio else "")
        display_q = "Portfolio automatisch analysieren"
        
        if use_web_search:
            with status_container.container():
                with st.status("Analysiere Portfolio für gezielte Marktsuche...", expanded=True) as status:
                    search_ctx = generate_search_context(llm_config, portfolio_text, is_portfolio_analysis=True)
                    queries = search_ctx["web_queries"]
                    tickers = search_ctx["tickers"]
                    
                    if queries or tickers:
                        st.write("**Gedankengang zur Websuche:**")
                        if queries: st.write(f"- 🌐 Suche nach: `{', '.join(queries)}`")
                        if tickers: st.write(f"- 📈 Ticker-Abfrage: `{', '.join(tickers)}`")
                        
                    status.update(label="Sammle Marktdaten und News aus dem Web...", state="running")
                    
                    search_results = fetch_custom_web_search(queries, include_macro=True)
                    ticker_data = fetch_ticker_live_data(tickers) if tickers else ""
                    
                    market_context = ""
                    if search_results and search_results != "RATE_LIMIT": 
                        market_context += search_results
                        if ticker_data: 
                            market_context += ("\n\n" if market_context else "") + ticker_data
                            
                        if not market_context or search_results == "RATE_LIMIT":
                            status.update(label="Einfache Websuche als Fallback...", state="running")
                            fallback_res = fetch_chat_search_context("aktuelle marktsituation aktien etfs")
                            if not market_context: market_context = fallback_res if fallback_res != "RATE_LIMIT" else ""
                        
                if market_context == "RATE_LIMIT":
                    market_context = "" # Fallback trigger
                    
            if market_context:
                initial_prompt += f"\n\nZusätzlicher Kontext aus aktuellen Nachrichten/Websuche:\n{market_context}\nNutze diese Informationen, falls sie für die Antwort relevant sind."
            else:
                initial_prompt += f"\n\nZusätzlicher Kontext: Die Live-APIs für Marktdaten (Websuche) sind momentan wegen zu vieler Anfragen blockiert (Rate Limit). Bitte greife für deine Bewertung auf dein allgemeines, aktuelles Wissen zurück."
        
        st.session_state.pdf_report_bytes = None
        st.session_state.chat_history.append({"role": "user", "content": initial_prompt, "display": display_q})
        do_grounding = use_web_search and llm_config['provider'] == 'Google Gemini'
        
    else:
        display_q = user_q
        if include_portfolio:
            user_q += f"\n\n---\n**Aktueller Portfolio-Stand zur Referenz:**\n{portfolio_text}\nNutze diese Daten für deine Antwort, falls sie relevant sind."
            
        if use_chat_search:
            with status_container.container():
                with st.status("KI extrahiert Suchbegriffe und Ticker...", expanded=True) as status:
                    search_ctx = generate_search_context(llm_config, user_q)
                    queries = search_ctx["web_queries"]
                    tickers = search_ctx["tickers"]
                        
                    if queries or tickers:
                        st.write("**Gedankengang zur Websuche:**")
                        if queries: st.write(f"- 🌐 Suche nach: `{', '.join(queries)}`")
                        if tickers: st.write(f"- 📈 Ticker-Abfrage: `{', '.join(tickers)}`")
                    
                    status.update(label=f"Recherchiere im Web & frage Ticker {', '.join(tickers)} ab...", state="running")
                    search_results = fetch_custom_web_search(queries) if queries else fetch_chat_search_context(user_q)
                    if search_results == "RATE_LIMIT":
                        search_results = ""
                        user_q += "\n\n(HINWEIS FÜR DIE KI: Die Live-Suche nach aktuellen Marktdaten wurde blockiert oder hat keine Ergebnisse geliefert. Bitte nutze dein allgemeines Wissen, um die Frage bestmöglich zu beantworten. Falls Echtzeit-Kurse gefragt sind, weise den Nutzer kurz darauf hin, dass diese gerade nicht geladen werden konnten.)"
                        
                    ticker_data = fetch_ticker_live_data(tickers) if tickers else ""
                    
                    # Kombiniere beides
                    combined_context = ""
                    if search_results:
                        combined_context += search_results
                    if ticker_data:
                        combined_context += ("\n\n" if combined_context else "") + ticker_data
                        
                    if combined_context:
                        search_results = combined_context # um unten in user_q eingefügt zu werden
                        
                    if search_results:
                        user_q += f"\n\n---\n**Zusätzlicher Kontext aus aktueller Websuche zu dieser Frage:**\n{search_results}\nNutze diese Informationen für deine Antwort, falls sie relevant sind."
        
        st.session_state.pdf_report_bytes = None
        st.session_state.chat_history.append({"role": "user", "content": user_q, "display": display_q})
        
    # Rerun to show user message immediately
    st.rerun()

# Handle Model Response if the last message is from user
if len(st.session_state.chat_history) > 0 and st.session_state.chat_history[-1]['role'] == 'user':
    with model_response_placeholder.container():
        with st.chat_message("model"):
            with st.spinner(f"KI ({llm_config['model']}) bereitet Antwort vor..."):
                answer_gen, err = get_llm_response_stream(llm_config, st.session_state.chat_history)
                if answer_gen:
                    if 'cancel_placeholder' in locals():
                        with cancel_placeholder.container():
                            cancel_col, _ = st.columns([0.25, 0.75])
                            with cancel_col:
                                cancel_clicked = st.button("⏹ Abbrechen", key="cancel_gen")
                                if cancel_clicked:
                                    st.session_state.chat_history.pop()
                                    st.rerun()
                    else:
                        cancel_col, _ = st.columns([0.25, 0.75])
                        with cancel_col:
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
if len(st.session_state.chat_history) > 0:
    st.divider()
    if st.button("Chat & Analyse zurücksetzen", type="secondary", width="stretch"):
        st.session_state.chat_history = []
        st.session_state.gemini_error = False
        st.rerun()
