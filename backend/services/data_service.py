import pandas as pd
import yfinance as yf
import requests
import logging
from datetime import datetime, timedelta
import traceback
import concurrent.futures

from database import get_cached_metadata, set_cached_metadata

# Wir unterdrücken die lauten Warnungen von yfinance
logging.getLogger('yfinance').setLevel(logging.CRITICAL)

# --- HYBRID FUNKTIONEN (yFinance + EODHD) ---

def get_eodhd_ticker_from_isin(isin, api_key):
    if not api_key: return None
    url = f"https://eodhd.com/api/search/{isin}?api_token={api_key}&fmt=json"
    try:
        r = requests.get(url, timeout=3)
        if r.status_code == 200 and r.json():
            eod_data = r.json()[0]
            return f"{eod_data.get('Code')}.{eod_data.get('Exchange')}"
    except: pass
    return None

def hybrid_search_by_isin(isin, api_key):
    if pd.isna(isin) or str(isin).strip() == "":
        return None, "failed", {}
        
    url_yf = f"https://query2.finance.yahoo.com/v1/finance/search?q={isin}"
    try:
        resp_yf = requests.get(url_yf, headers={'User-Agent': 'Mozilla/5.0'}, timeout=3)
        if resp_yf.status_code == 200:
            quotes = resp_yf.json().get('quotes', [])
            if quotes and 'symbol' in quotes[0]:
                symbol = quotes[0]['symbol']
                return symbol, "yfinance", {}
    except: pass
    
    if not api_key or api_key == "": return None, "failed", {}
        
    url_eod = f"https://eodhd.com/api/search/{isin}?api_token={api_key}&fmt=json"
    try:
        resp_eod = requests.get(url_eod, timeout=3)
        if resp_eod.status_code == 200:
            res = resp_eod.json()
            if res:
                symbol = f"{res[0].get('Code')}.{res[0].get('Exchange')}"
                return symbol, "eodhd", res[0]
    except: pass
    
    return None, "failed", {}

def eodhd_fetch_metadata(ticker, api_key):
    url = f"https://eodhd.com/api/fundamentals/{ticker}?api_token={api_key}"
    try:
        r = requests.get(url, timeout=3)
        if r.status_code == 200:
            general = r.json().get("General", {})
            if not general: return None
            return {
                'Typ': 'Fonds' if general.get('Type') == 'FUND' else general.get('Type', 'Unbekannt'),
                'Branche': general.get('Sector', 'Unbekannt'),
                'Region': general.get('CountryName', 'Unbekannt')
            }
    except: pass
    return None

def eodhd_fetch_price(ticker, api_key):
    url = f"https://eodhd.com/api/real-time/{ticker}?api_token={api_key}&fmt=json"
    try:
        r = requests.get(url, timeout=3)
        if r.status_code == 200 and r.json():
            return r.json().get('close', None)
    except: pass
    return None

def hybrid_get_price_and_meta(ticker, isin, api_key, source_hint, eod_search_data):
    price = None
    meta = {'Typ': 'Unbekannt', 'Branche': 'Unbekannt', 'Region': 'Unbekannt'}
    
    # 1. Metadaten aus der Datenbank (Cache) holen
    cached_meta = get_cached_metadata(ticker)
    has_cached_meta = False
    if cached_meta and cached_meta['Typ'] != 'Unbekannt':
        meta = cached_meta
        has_cached_meta = True
    
    # --- EODHD ROUTE ---
    if source_hint == "eodhd":
        if not has_cached_meta:
            if eod_search_data:
                meta['Typ'] = 'Fonds' if eod_search_data.get('Type') == 'FUND' else eod_search_data.get('Type', 'Unbekannt')
            eodhd_meta = eodhd_fetch_metadata(ticker, api_key)
            if eodhd_meta: 
                meta.update(eodhd_meta)
            set_cached_metadata(ticker, meta['Typ'], meta['Branche'], meta['Region'])
            
        price = eodhd_fetch_price(ticker, api_key)
        if (price is None or price == 0) and eod_search_data and eod_search_data.get('previousClose'):
            price = eod_search_data['previousClose']
        return price, meta
        
    # --- YFINANCE ROUTE ---
    t = yf.Ticker(ticker)
    try:
        if not has_cached_meta:
            info = t.info
            raw_type = info.get('quoteType', 'Unbekannt')
            typ_mapping = {'EQUITY': 'Aktie', 'ETF': 'ETF', 'MUTUALFUND': 'Fonds'}
            meta['Typ'] = typ_mapping.get(raw_type.upper(), raw_type)
            meta['Branche'] = info.get('sector', 'Unbekannt')
            meta['Region'] = info.get('country', 'Unbekannt')
            name = info.get('shortName', '').lower()
            
            # yFinance Korrektur-Check
            if meta['Typ'] == 'ETF' and ('deka' in name or 'fonds' in name):
                eod_ticker = get_eodhd_ticker_from_isin(isin, api_key)
                if eod_ticker:
                    meta['Typ'] = 'Fonds'
                if meta['Typ'] == 'ETF': meta['Typ'] = 'Fonds'
            
            # Cache the newly fetched/corrected metadata
            set_cached_metadata(ticker, meta['Typ'], meta['Branche'], meta['Region'])
            
        # Price fetching
        price = t.fast_info.get('lastPrice', None)
        if price is None or price == 0:
            hist = t.history(period="1d")
            if not hist.empty:
                price = hist['Close'].iloc[-1]
    except: pass
        
    # --- FALLBACK WENN YFINANCE FEHLSCHLÄGT ---
    if price is None or price == 0 or (meta['Branche'] == 'Unbekannt' and meta['Region'] == 'Unbekannt'):
        if api_key:
            eod_ticker = get_eodhd_ticker_from_isin(isin, api_key)
            if eod_ticker:
                if not has_cached_meta:
                    eodhd_meta = eodhd_fetch_metadata(eod_ticker, api_key)
                    if eodhd_meta: 
                        meta.update(eodhd_meta)
                        set_cached_metadata(ticker, meta['Typ'], meta['Branche'], meta['Region'])
                if price is None or price == 0:
                    price = eodhd_fetch_price(eod_ticker, api_key)
    return price, meta

# --- PORTFOLIO LADE FUNKTION ---
import functools
import time

# Simple TTL Cache for prices (5 minutes)
_price_cache = {}
CACHE_TTL = 300 

def get_cached_price(ticker):
    if ticker in _price_cache:
        val, ts = _price_cache[ticker]
        if time.time() - ts < CACHE_TTL:
            return val
    return None

def set_cached_price(ticker, price):
    if price is not None:
        _price_cache[ticker] = (price, time.time())

def _process_single_position(row, eodhd_key):
    ticker = row.get('Ticker', '')
    isin = row.get('ISIN', '')
    
    source_hint = "yfinance"
    eod_search_data = {}
    
    if pd.isna(ticker) or str(ticker).strip() == "":
        found_ticker, src, search_data = hybrid_search_by_isin(isin, eodhd_key)
        if found_ticker:
            ticker = found_ticker
            source_hint = src
            eod_search_data = search_data
        else:
            return None, ticker, {'Typ': 'Unbekannt', 'Branche': 'Unbekannt', 'Region': 'Unbekannt'}
            
    t = str(ticker).strip()
    
    cached_price = get_cached_price(t)
    if cached_price is not None:
        cached_meta = get_cached_metadata(t)
        if cached_meta and cached_meta['Typ'] != 'Unbekannt':
            return cached_price, t, cached_meta
    
    price, meta = hybrid_get_price_and_meta(t, isin, eodhd_key, source_hint, eod_search_data)
    set_cached_price(t, price)
    return price, t, meta

def fetch_live_prices(df: pd.DataFrame, eodhd_key: str = "") -> tuple[list, list, list]:
    live_prices = []
    updated_tickers = []
    metadata = []
    
    if df.empty:
        return live_prices, updated_tickers, metadata
        
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(_process_single_position, row, eodhd_key) for _, row in df.iterrows()]
        for future in futures:
            price, t, meta = future.result()
            live_prices.append(price)
            updated_tickers.append(t)
            metadata.append(meta)
            
    return live_prices, updated_tickers, metadata

# ... (berechne_portfolio_metriken stays the same) ...

def berechne_portfolio_metriken(df: pd.DataFrame, live_data_fetched: bool = False) -> tuple[float, float, float, list]:
    if df.empty:
        return 0.0, 0.0, 0.0, []

    kaufwert = df['Kaufpreis'] + df['Orderkost']
    gesamt_kaufwert = kaufwert.sum()
    
    if 'Live_Gesamtwert' in df.columns and live_data_fetched:
        aktueller_wert = df['Live_Gesamtwert'].fillna(df['Wert'])
    else:
        aktueller_wert = df['Wert']
        
    gesamtwert = aktueller_wert.sum()
    gesamt_gewinn = gesamtwert - gesamt_kaufwert
    
    if gesamt_kaufwert > 0:
        gesamt_performance_prozent = (gesamt_gewinn / gesamt_kaufwert) * 100
    else:
        gesamt_performance_prozent = 0.0
        
    positions = []
    for idx, row in df.iterrows():
        st_nom = float(row.get('St_Nom', 0))
        kaufwert_pos = float(row.get('Kaufpreis', 0)) + float(row.get('Orderkost', 0))
        
        avg_kaufkurs = kaufwert_pos / st_nom if st_nom > 0 else 0.0
        
        akt_wert_pos = float(row.get('Live_Gesamtwert', row.get('Wert', 0))) if live_data_fetched and 'Live_Gesamtwert' in row else float(row.get('Wert', 0))
        if pd.isna(akt_wert_pos): akt_wert_pos = 0.0
        
        akt_kurs_raw = row.get('Live_Kurs', 0)
        akt_kurs_pos = float(akt_kurs_raw) if live_data_fetched and 'Live_Kurs' in row and not pd.isna(akt_kurs_raw) else (akt_wert_pos / st_nom if st_nom > 0 else 0.0)
        if pd.isna(akt_kurs_pos): akt_kurs_pos = 0.0
        
        g_v_pos = akt_wert_pos - kaufwert_pos
        perf_pos = (g_v_pos / kaufwert_pos * 100) if kaufwert_pos > 0 else 0.0
        if pd.isna(g_v_pos): g_v_pos = 0.0
        if pd.isna(perf_pos): perf_pos = 0.0
        
        positions.append({
            "Wertpapier": str(row.get('Wertpapier', 'Unbekannt')),
            "Ticker": str(row.get('Ticker', '')),
            "ISIN": str(row.get('ISIN', '')),
            "WKN": str(row.get('WKN', '')),
            "Typ": str(row.get('Typ', 'Unbekannt')),
            "Branche": str(row.get('Branche', 'Unbekannt')),
            "Region": str(row.get('Region', 'Unbekannt')),
            "St_Nom": st_nom,
            "Kaufwert": kaufwert_pos,
            "Avg_Kaufkurs": avg_kaufkurs,
            "Aktueller_Kurs": akt_kurs_pos,
            "Akt_Wert": akt_wert_pos,
            "Gewinn_Verlust": g_v_pos,
            "Performance": perf_pos
        })
        
    return float(gesamtwert), float(gesamt_gewinn), float(gesamt_performance_prozent), positions

# --- HISTORIE / BACKTESTING ---

def eodhd_fetch_history(ticker, api_key, period_years=5):
    start_date = (datetime.now() - timedelta(days=period_years*365)).strftime('%Y-%m-%d')
    url = f"https://eodhd.com/api/eod/{ticker}?from={start_date}&api_token={api_key}&fmt=json"
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200 and r.json():
            return pd.Series({pd.to_datetime(item['date']): item.get('adjusted_close', item['close']) for item in r.json()})
    except: pass
    return pd.Series()

def hybrid_fetch_history_series(ticker, isin, api_key, period_years=5):
    try:
        t = yf.Ticker(ticker)
        period_str = f"{period_years}y" if period_years <= 10 else "max"
        hist = t.history(period=period_str, interval="1d")
        if not hist.empty and 'Close' in hist.columns:
            return hist['Close']
    except: pass
    
    if api_key:
        eod_ticker = get_eodhd_ticker_from_isin(isin, api_key)
        if eod_ticker:
            return eodhd_fetch_history(eod_ticker, api_key, period_years)
            
    return pd.Series()

def calculate_backtest(df, startkapital, period, eodhd_key="", benchmark_ticker="^GSPC"):
    import yfinance as yf
    import pandas as pd
    
    if df.empty or startkapital <= 0:
        return pd.Series(), pd.Series(), 0, 0
        
    period_mapping = {
        "1 Jahr": 1,
        "3 Jahre": 3,
        "5 Jahre": 5,
        "10 Jahre": 10,
        "Maximal": 20
    }
    period_years = period_mapping.get(period, 5)
    
    df_calc = df.copy()
    if 'Live_Gesamtwert' in df_calc.columns:
        df_calc['Akt_Wert'] = df_calc['Live_Gesamtwert'].fillna(df_calc['Wert'])
    else:
        df_calc['Akt_Wert'] = df_calc['Wert']
        
    gesamtwert = df_calc['Akt_Wert'].sum()
    if gesamtwert <= 0:
         return pd.Series(), pd.Series(), 0, 0
         
    df_calc['Gewichtung'] = df_calc['Akt_Wert'] / gesamtwert
    
    asset_series = []
    
    for i, row in df_calc.iterrows():
        ticker = str(row.get('Ticker', '')).strip()
        isin = str(row.get('ISIN', '')).strip()
        gewicht = row['Gewichtung']
        
        if not ticker or gewicht <= 0:
            continue
            
        hist_close = hybrid_fetch_history_series(ticker, isin, eodhd_key, period_years)
        
        if not hist_close.empty:
            first_price = hist_close.iloc[0]
            if first_price > 0:
                normalized_series = hist_close / first_price
                capital_series = normalized_series * (startkapital * gewicht)
                if capital_series.index.tz is not None:
                    capital_series.index = capital_series.index.tz_localize(None)
                capital_series.index = capital_series.index.normalize()
                capital_series.name = ticker
                asset_series.append(capital_series)
                
    if not asset_series:
         return pd.Series(), pd.Series(), 0, 0, pd.DataFrame()
         
    df_hist = pd.concat(asset_series, axis=1)
    df_hist = df_hist.sort_index().ffill().bfill()
    portfolio_series = df_hist.sum(axis=1)
    
    # Benchmark
    benchmark_series = pd.Series()
    try:
        b_hist = hybrid_fetch_history_series(benchmark_ticker, "", "", period_years)
        if not b_hist.empty:
            b_first = b_hist.iloc[0]
            if b_first > 0:
                b_norm = b_hist / b_first
                benchmark_series = b_norm * startkapital
                if benchmark_series.index.tz is not None:
                    benchmark_series.index = benchmark_series.index.tz_localize(None)
                benchmark_series.index = benchmark_series.index.normalize()
    except: pass
        
    if not benchmark_series.empty:
        df_combined = pd.DataFrame({'Portfolio': portfolio_series, 'Benchmark': benchmark_series})
        df_combined = df_combined.sort_index().ffill().dropna()
        portfolio_series = df_combined['Portfolio']
        benchmark_series = df_combined['Benchmark']
        
    def calc_max_drawdown(series):
        if series.empty: return 0.0
        roll_max = series.cummax()
        drawdowns = series / roll_max - 1.0
        return drawdowns.min() * 100
        
    pf_drawdown = calc_max_drawdown(portfolio_series)
    bm_drawdown = calc_max_drawdown(benchmark_series)
    
    return portfolio_series, benchmark_series, pf_drawdown, bm_drawdown, df_hist

# --- DIVIDENDEN ---

def eodhd_fetch_dividends(ticker, api_key):
    url = f"https://eodhd.com/api/div/{ticker}?api_token={api_key}&fmt=json"
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200 and r.json():
            return pd.Series({pd.to_datetime(item['date']): item['value'] for item in r.json()})
    except: pass
    return pd.Series()

def hybrid_fetch_dividends_series(ticker, isin, api_key):
    try:
        t = yf.Ticker(ticker)
        divs = t.dividends
        if not divs.empty:
            return divs
    except: pass
    
    if api_key:
        eod_ticker = get_eodhd_ticker_from_isin(isin, api_key)
        if eod_ticker:
            return eodhd_fetch_dividends(eod_ticker, api_key)
            
    return pd.Series()

def fetch_dividend_data(df, eodhd_key=""):
    import yfinance as yf
    import pandas as pd
    
    div_data = []
    historical_divs = []
    
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()
        
    for i, row in df.iterrows():
        ticker = row.get('Ticker', '')
        isin = row.get('ISIN', '')
        if pd.isna(ticker) or str(ticker).strip() == "":
            continue
            
        t = str(ticker).strip()
        try:
            div_rate = 0.0
            div_yield = 0.0
            currency = 'EUR'
            
            # Info only from yFinance for div rate for simplicity
            try:
                t_obj = yf.Ticker(t)
                info = t_obj.info
                div_rate = info.get('trailingAnnualDividendRate') or info.get('dividendRate') or 0.0
                div_yield = info.get('trailingAnnualDividendYield') or info.get('dividendYield') or 0.0
                currency = info.get('currency', 'EUR')
            except: pass
            
            divs_series = hybrid_fetch_dividends_series(t, isin, eodhd_key)
            last_year = pd.Timestamp.now(tz='UTC') - pd.DateOffset(years=1)
            
            if not divs_series.empty:
                if divs_series.index.tz is None:
                    divs_series.index = divs_series.index.tz_localize('UTC')
                else:
                    divs_series.index = divs_series.index.tz_convert('UTC')
                    
                recent_divs = divs_series[divs_series.index > last_year]
                
                if not div_rate and not recent_divs.empty:
                    div_rate = recent_divs.sum()
                    
                if not recent_divs.empty:
                    st_nom = row.get('St_Nom', 0)
                    for date, amount in recent_divs.items():
                        historical_divs.append({
                            'Datum': date,
                            'Wertpapier': row['Wertpapier'],
                            'Ausschüttung': amount * st_nom
                        })
                        
            st_nom = row.get('St_Nom', 0)
            erwartet_pa = div_rate * st_nom
            
            akt_wert = row.get('Live_Gesamtwert', row.get('Wert', 0))
            if pd.isna(akt_wert): akt_wert = row.get('Wert', 0)
                
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
