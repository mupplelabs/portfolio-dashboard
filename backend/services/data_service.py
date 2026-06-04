import pandas as pd
import yfinance as yf
import requests

def search_ticker_by_isin(isin: str) -> str | None:
    if pd.isna(isin) or str(isin).strip() == "":
        return None
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={str(isin).strip()}"
    headers = {'User-Agent': 'Mozilla/5.0'}
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

def fetch_live_prices(df: pd.DataFrame, fmp_key: str = "") -> tuple[list, list]:
    live_prices = []
    updated_tickers = []
    
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
        
        # FMP Logic
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
                
        # yfinance Fallback
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
                
        live_prices.append(price)
        updated_tickers.append(ticker)
        
    return live_prices, updated_tickers

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
        
    # Prepare position data for frontend
    positions = []
    
    # Safely iterate through rows to build the list
    for idx, row in df.iterrows():
        st_nom = float(row.get('St_Nom', 0))
        kaufwert_pos = float(row.get('Kaufpreis', 0)) + float(row.get('Orderkost', 0))
        
        # Avoid division by zero
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
            "St_Nom": st_nom,
            "Kaufwert": kaufwert_pos,
            "Avg_Kaufkurs": avg_kaufkurs,
            "Aktueller_Kurs": akt_kurs_pos,
            "Akt_Wert": akt_wert_pos,
            "Gewinn_Verlust": g_v_pos,
            "Performance": perf_pos
        })
        
    return float(gesamtwert), float(gesamt_gewinn), float(gesamt_performance_prozent), positions


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
    if 'Live_Gesamtwert' in df_calc.columns:
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
