import pandas as pd
import streamlit as st
import yfinance as yf
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
            "system": [{"type": "text", "text": system_instruction, "cache_control": {"type": "ephemeral"}}],
            "messages": [{"role": "user", "content": [{"type": "text", "text": user_message, "cache_control": {"type": "ephemeral"}}]}],
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
    import html
    text = html.unescape(text)
    text = text.replace('€', 'EUR')
    return text.encode('latin-1', 'ignore').decode('latin-1')

@st.cache_data(show_spinner=False)
def export_text_to_pdf(text):
    from pdf_export import export_text_to_pdf_reportlab
    try:
        return export_text_to_pdf_reportlab(text)
    except Exception as e:
        print("PDF Export Error:", e)
        return None

from pdf_export import generate_portfolio_pdf as export_full_report_to_pdf

# fpdf removed


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
                    
                # Füge Cache-Control zu den letzten zwei Nutzer-Nachrichten hinzu (für optimale Multi-Turn Caches)
                cache_slots = 0
                for i in range(len(messages) - 1, -1, -1):
                    if messages[i]["role"] == "user":
                        messages[i]["content"] = [
                            {
                                "type": "text",
                                "text": messages[i]["content"],
                                "cache_control": {"type": "ephemeral"}
                            }
                        ]
                        cache_slots += 1
                        if cache_slots >= 2: # Max 2 User-Nachrichten cachen (plus System = 3 Slots)
                            break
                    
                payload = {
                    "model": config.get('model', 'claude-sonnet-4-6'),
                    "system": [{"type": "text", "text": system_instruction, "cache_control": {"type": "ephemeral"}}],
                    "messages": messages,
                    "stream": True,
                    "max_tokens": 8192
                }
                
                url = 'https://api.anthropic.com/v1/messages'
                response = requests.post(url, json=payload, headers=headers, stream=True, timeout=300)
                response.raise_for_status()
                
                def claude_gen(resp):
                    cache_stats = {"creation": 0, "read": 0}
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
                                            if data.get('type') == 'message_start':
                                                usage = data.get('message', {}).get('usage', {})
                                                cache_stats["creation"] = usage.get('cache_creation_input_tokens', 0)
                                                cache_stats["read"] = usage.get('cache_read_input_tokens', 0)
                                            elif data.get('type') == 'content_block_delta' and data.get('delta', {}).get('type') == 'text_delta':
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

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_dividend_data(df):
    import yfinance as yf
    import pandas as pd
    
    div_data = []
    historical_divs = []
    
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()
        
    for i, row in df.iterrows():
        ticker = row.get('Ticker', '')
        if pd.isna(ticker) or str(ticker).strip() == "":
            continue
            
        t = str(ticker).strip()
        try:
            ticker_obj = yf.Ticker(t)
            info = ticker_obj.info
            
            # 1. Try to get explicit dividend rate
            div_rate = info.get('trailingAnnualDividendRate') or info.get('dividendRate')
            div_yield = info.get('trailingAnnualDividendYield') or info.get('dividendYield')
            currency = info.get('currency', 'EUR')
            
            # 2. Get history for ETFs or as fallback
            divs_series = ticker_obj.dividends
            last_year = pd.Timestamp.now(tz='UTC') - pd.DateOffset(years=1)
            
            if not divs_series.empty:
                if divs_series.index.tz is None:
                    divs_series.index = divs_series.index.tz_localize('UTC')
                else:
                    divs_series.index = divs_series.index.tz_convert('UTC')
                    
                recent_divs = divs_series[divs_series.index > last_year]
                
                # Wenn wir keine div_rate haben, aber Ausschüttungen im letzten Jahr, berechne sie
                if not div_rate and not recent_divs.empty:
                    div_rate = recent_divs.sum()
                    
                # Speichere die Historie für das Diagramm
                if not recent_divs.empty:
                    st_nom = row.get('St_Nom', 0)
                    for date, amount in recent_divs.items():
                        historical_divs.append({
                            'Datum': date,
                            'Wertpapier': row['Wertpapier'],
                            'Ausschüttung': amount * st_nom
                        })
                        
            if not div_rate:
                div_rate = 0.0
                div_yield = 0.0
                
            st_nom = row.get('St_Nom', 0)
            erwartet_pa = div_rate * st_nom
            
            akt_wert = row.get('Live_Gesamtwert', row.get('Wert', 0))
            if pd.isna(akt_wert):
                akt_wert = row.get('Wert', 0)
                
            if not div_yield and akt_wert > 0 and erwartet_pa > 0:
                div_yield = erwartet_pa / akt_wert
                
            div_data.append({
                'Wertpapier': row['Wertpapier'],
                'St_Nom': st_nom,
                'Dividende_pro_Stück': div_rate,
                'Währung': currency,
                'Erwartet_pa': erwartet_pa,
                'Rendite_Prozent': (div_yield * 100) if div_yield else 0.0,
                'Akt_Wert': akt_wert
            })
            
        except Exception as e:
            print(f"Fehler bei Dividendenabruf für {t}: {e}")
            
    df_divs = pd.DataFrame(div_data)
    df_hist = pd.DataFrame(historical_divs)
    
    return df_divs, df_hist

@st.cache_data(show_spinner=False, ttl=3600)
def calculate_backtest(df, startkapital, period, benchmark_ticker="^GSPC"):
    import yfinance as yf
    import pandas as pd
    
    if df.empty or startkapital <= 0:
        return pd.Series(), pd.Series(), 0, 0
        
    period_mapping = {
        "1 Jahr": "1y",
        "3 Jahre": "3y",
        "5 Jahre": "5y",
        "10 Jahre": "10y",
        "Maximal": "max"
    }
    yf_period = period_mapping.get(period, "5y")
    
    # 1. Bestimme die aktuelle Gewichtung des Portfolios
    df_calc = df.copy()
    if 'Live_Gesamtwert' in df_calc.columns and st.session_state.get('live_data_fetched', False):
        df_calc['Akt_Wert'] = df_calc['Live_Gesamtwert'].fillna(df_calc['Wert'])
    else:
        df_calc['Akt_Wert'] = df_calc['Wert']
        
    gesamtwert = df_calc['Akt_Wert'].sum()
    if gesamtwert <= 0:
         return pd.Series(), pd.Series(), 0, 0
         
    df_calc['Gewichtung'] = df_calc['Akt_Wert'] / gesamtwert
    
    # 2. Historische Daten aller Ticker abrufen
    asset_series = []
    
    for i, row in df_calc.iterrows():
        ticker = str(row.get('Ticker', '')).strip()
        gewicht = row['Gewichtung']
        
        if not ticker or gewicht <= 0:
            continue
            
        try:
            t_obj = yf.Ticker(ticker)
            hist = t_obj.history(period=yf_period, interval="1d")
            
            if len(hist) > 0 and 'Close' in hist.columns:
                # Normalisieren: Der erste verfügbare Kurs = 1.0
                first_price = hist['Close'].iloc[0]
                if first_price > 0:
                    normalized_series = hist['Close'] / first_price
                    # Skalieren auf das zugewiesene Startkapital
                    capital_series = normalized_series * (startkapital * gewicht)
                    if capital_series.index.tz is not None:
                        capital_series.index = capital_series.index.tz_localize(None)
                    asset_series.append(capital_series)
        except Exception as e:
            print(f"Backtesting Fehler bei {ticker}: {e}")
            
    # Portfolio Summe bilden
    if not asset_series:
         return pd.Series(), pd.Series(), 0, 0
         
    # Zusammenführen (fehlende Daten mit ffill füllen)
    df_hist = pd.concat(asset_series, axis=1)
    df_hist = df_hist.sort_index().ffill().bfill()
    portfolio_series = df_hist.sum(axis=1)
    
    # 3. Benchmark abrufen
    benchmark_series = pd.Series()
    try:
        if benchmark_ticker:
            b_obj = yf.Ticker(benchmark_ticker)
            b_hist = b_obj.history(period=yf_period, interval="1d")
            if len(b_hist) > 0 and 'Close' in b_hist.columns:
                b_first = b_hist['Close'].iloc[0]
                if b_first > 0:
                    b_norm = b_hist['Close'] / b_first
                    benchmark_series = b_norm * startkapital
                    if benchmark_series.index.tz is not None:
                        benchmark_series.index = benchmark_series.index.tz_localize(None)
    except Exception as e:
        print(f"Benchmark Fehler: {e}")
        
    # Wenn Benchmark Serie und Portfolio Serie nicht dieselben Indizes haben, alignen wir sie
    if not benchmark_series.empty:
        df_combined = pd.DataFrame({'Portfolio': portfolio_series, 'Benchmark': benchmark_series})
        df_combined = df_combined.sort_index().ffill().dropna()
        portfolio_series = df_combined['Portfolio']
        benchmark_series = df_combined['Benchmark']
        
    # 4. Max Drawdown berechnen
    def calc_max_drawdown(series):
        if series.empty: return 0.0
        roll_max = series.cummax()
        drawdowns = series / roll_max - 1.0
        return drawdowns.min() * 100
        
    pf_drawdown = calc_max_drawdown(portfolio_series)
    bm_drawdown = calc_max_drawdown(benchmark_series)
    
    return portfolio_series, benchmark_series, pf_drawdown, bm_drawdown

