from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
import pandas as pd
import io
import csv
import re

from services.data_service import fetch_live_prices, berechne_portfolio_metriken

router = APIRouter()

class PortfolioPosition(BaseModel):
    Wertpapier: str
    Ticker: str
    ISIN: str = ""
    WKN: str = ""
    St_Nom: float
    Kaufwert: float
    Avg_Kaufkurs: float
    Aktueller_Kurs: float
    Akt_Wert: float
    Gewinn_Verlust: float
    Performance: float

class PortfolioMetrics(BaseModel):
    gesamtwert: float
    gesamt_gewinn: float
    performance_prozent: float
    positions: list[PortfolioPosition]

def clean_number(val):
    if pd.isna(val):
        return 0.0
    s = str(val).strip()
    s = re.sub(r'[^\d,\.-]', '', s)
    if not s:
        return 0.0
    if ',' in s and '.' in s:
        if s.rfind(',') > s.rfind('.'):
            s = s.replace('.', '').replace(',', '.')
        else:
            s = s.replace(',', '')
    elif ',' in s:
        s = s.replace(',', '.')
    try:
        return float(s)
    except:
        return 0.0

def smart_read_csv(content: bytes) -> pd.DataFrame:
    text = content.decode('utf-8', errors='replace')
    lines = text.splitlines()
    start_idx = 0
    max_cols = 0
    for i in range(min(20, len(lines))):
        col_count = len(lines[i].split(';')) if ';' in lines[i] else len(lines[i].split(','))
        if col_count > max_cols:
            max_cols = col_count
            start_idx = i
            
    if max_cols < 2:
        return pd.read_csv(io.BytesIO(content), sep=None, engine='python')
        
    text_to_parse = "\n".join(lines[start_idx:])
    try:
        dialect = csv.Sniffer().sniff(text_to_parse[:1024])
        sep = dialect.delimiter
    except:
        sep = ';' if ';' in lines[start_idx] else ','
        
    return pd.read_csv(io.StringIO(text_to_parse), sep=sep, engine='python')

def map_columns(df: pd.DataFrame) -> pd.DataFrame:
    mapping = {
        'Wertpapier': ['bezeichnung', 'name', 'wertpapierbezeichnung', 'instrument', 'wertpapier'],
        'Ticker': ['symbol', 'kürzel', 'ticker'],
        'ISIN': ['isin', 'wkn'],
        'St_Nom': ['stück', 'menge', 'bestand', 'anteile', 'st_nom'],
        'Kaufpreis': ['kaufkurs', 'einstandskurs', 'einstandswert', 'kaufwert', 'kaufpreis'],
        'Orderkost': ['spesen', 'gebühren', 'provision', 'orderkost'],
        'Wert': ['kurswert', 'aktueller wert', 'marktwert', 'wert in eur', 'wert']
    }
    new_cols = {}
    mapped_targets = set()
    for col in df.columns:
        col_lower = str(col).lower().strip()
        mapped = False
        for target, aliases in mapping.items():
            if target not in mapped_targets and any(alias in col_lower for alias in aliases):
                new_cols[col] = target
                mapped_targets.add(target)
                mapped = True
                break
        if not mapped:
            new_cols[col] = col
    df = df.rename(columns=new_cols)
    
    for req in ['Wertpapier', 'Ticker', 'ISIN', 'St_Nom', 'Kaufpreis', 'Orderkost', 'Wert']:
        if req not in df.columns:
            df[req] = '' if req in ['Wertpapier', 'Ticker', 'ISIN'] else 0.0
    return df

@router.post("/metrics", response_model=PortfolioMetrics)
async def get_portfolio_metrics(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")
        
    try:
        content = await file.read()
        df = smart_read_csv(content)
        df = map_columns(df)
        
        for col in ['St_Nom', 'Wert', 'Orderkost', 'Kaufpreis']:
            df[col] = df[col].apply(clean_number)
            
        # Fetch live prices for the uploaded CSV
        live_prices, updated_tickers = fetch_live_prices(df)
        df['Live_Kurs'] = live_prices
        df['Ticker'] = updated_tickers
        
        # Calculate live value based on fetched prices or fallback to CSV 'Wert'
        df['Live_Kurs'] = pd.to_numeric(df['Live_Kurs'], errors='coerce')
        df['Live_Gesamtwert'] = df.apply(
            lambda row: row['St_Nom'] * row['Live_Kurs'] if pd.notna(row['Live_Kurs']) and row['Live_Kurs'] > 0 else row.get('Wert', 0),
            axis=1
        )
                    
        gesamtwert, gewinn, performance, positions = berechne_portfolio_metriken(df, live_data_fetched=True)
        
        return PortfolioMetrics(
            gesamtwert=gesamtwert,
            gesamt_gewinn=gewinn,
            performance_prozent=performance,
            positions=positions
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

class PDFReportRequest(BaseModel):
    positions: list[PortfolioPosition]
    gesamtwert: float
    summary_text: str
    chat_history: list[dict] = []

@router.post("/report/pdf")
async def generate_pdf(req: PDFReportRequest):
    try:
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from pdf_export import generate_portfolio_pdf
        from fastapi.responses import Response
        
        df_data = []
        for p in req.positions:
            df_data.append({
                "Wertpapier": p.Wertpapier,
                "St_Nom": p.St_Nom,
                "Aktueller Kurs": p.Aktueller_Kurs,
                "Akt. Wert": p.Akt_Wert,
                "Wert": p.Akt_Wert,
                "_Plot_Wert": p.Akt_Wert
            })
        
        df = pd.DataFrame(df_data) if df_data else pd.DataFrame()
        
        pdf_bytes = generate_portfolio_pdf(
            portfolio_df=df,
            gesamtwert=req.gesamtwert,
            summary_text=req.summary_text,
            chat_history=req.chat_history
        )
        
        return Response(content=pdf_bytes, media_type="application/pdf", headers={
            "Content-Disposition": "attachment; filename=Portfolio_Gesamtreport.pdf"
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

class DividendRequest(BaseModel):
    positions: list[PortfolioPosition]

@router.post("/dividends")
async def get_dividends(req: DividendRequest):
    df_data = []
    for p in req.positions:
        df_data.append({
            "Wertpapier": p.Wertpapier,
            "Ticker": p.Ticker,
            "St_Nom": p.St_Nom,
            "Wert": p.Akt_Wert,
            "Live_Gesamtwert": p.Akt_Wert
        })
    df = pd.DataFrame(df_data) if df_data else pd.DataFrame()
    
    from services.data_service import fetch_dividend_data
    df_divs, df_hist = fetch_dividend_data(df)
    
    if not df_hist.empty and 'Datum' in df_hist.columns:
        df_hist['Datum'] = df_hist['Datum'].astype(str)
        
    return {
        "divs": df_divs.to_dict(orient='records') if not df_divs.empty else [],
        "hist": df_hist.to_dict(orient='records') if not df_hist.empty else []
    }

class BacktestRequest(BaseModel):
    positions: list[PortfolioPosition]
    startkapital: float
    period: str
    benchmark_ticker: str

@router.post("/backtest")
async def run_backtest(req: BacktestRequest):
    df_data = []
    for p in req.positions:
        df_data.append({
            "Wertpapier": p.Wertpapier,
            "Ticker": p.Ticker,
            "St_Nom": p.St_Nom,
            "Wert": p.Akt_Wert,
            "Live_Gesamtwert": p.Akt_Wert
        })
    df = pd.DataFrame(df_data) if df_data else pd.DataFrame()
    
    from services.data_service import calculate_backtest
    pf_series, bm_series, pf_dd, bm_dd = calculate_backtest(
        df, req.startkapital, req.period, req.benchmark_ticker
    )
    
    pf_dict = pf_series.to_dict() if not pf_series.empty else {}
    bm_dict = bm_series.to_dict() if not bm_series.empty else {}
    
    pf_json = {str(k)[:10]: v for k, v in pf_dict.items()}
    bm_json = {str(k)[:10]: v for k, v in bm_dict.items()}
    
    return {
        "portfolio": pf_json,
        "benchmark": bm_json,
        "pf_drawdown": float(pf_dd),
        "bm_drawdown": float(bm_dd)
    }

@router.get("/search")
async def search_ticker(query: str):
    import yfinance as yf
    from services.data_service import search_ticker_by_isin
    
    ticker_symbol = search_ticker_by_isin(query) or query
    try:
        t = yf.Ticker(ticker_symbol.strip())
        info = t.info
        name = info.get("shortName") or info.get("longName") or ticker_symbol
        price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
        if price is None:
            # Fallback to history
            hist = t.history(period="1d")
            if not hist.empty:
                price = hist['Close'].iloc[-1]
            else:
                price = 0.0
                
        currency = info.get("currency", "EUR")
        
        isin_val = "-"
        try:
            # Versuch die ISIN über yfinance abzurufen
            fetched_isin = t.isin
            if fetched_isin and fetched_isin != "-":
                isin_val = fetched_isin
        except Exception:
            pass
            
        return {
            "Ticker": ticker_symbol,
            "Wertpapier": name,
            "Aktueller_Kurs": float(price),
            "Waehrung": currency,
            "ISIN": isin_val
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Ticker {query} nicht gefunden: {str(e)}")

class CalculateMetricsRequest(BaseModel):
    positions: list[dict]

@router.post("/metrics/calculate", response_model=PortfolioMetrics)
async def calculate_metrics_from_json(req: CalculateMetricsRequest):
    df = pd.DataFrame(req.positions) if req.positions else pd.DataFrame()
    
    if df.empty:
        return PortfolioMetrics(gesamtwert=0.0, gesamt_gewinn=0.0, performance_prozent=0.0, positions=[])
    
    # Ensure datatypes
    for col in ['St_Nom', 'Kaufwert', 'Akt_Wert']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
            
    if 'Kaufwert' in df.columns:
        if 'Kaufpreis' not in df.columns:
            df['Kaufpreis'] = df['Kaufwert']
        else:
            df['Kaufpreis'] = df['Kaufpreis'].fillna(df['Kaufwert'])
            
    if 'Orderkost' not in df.columns:
        df['Orderkost'] = 0.0
    else:
        df['Orderkost'] = df['Orderkost'].fillna(0.0)
        
    if 'Akt_Wert' in df.columns:
        if 'Live_Gesamtwert' not in df.columns:
            df['Live_Gesamtwert'] = df['Akt_Wert']
        else:
            df['Live_Gesamtwert'] = df['Live_Gesamtwert'].fillna(df['Akt_Wert'])
            
        if 'Wert' not in df.columns:
            df['Wert'] = df['Akt_Wert']
        else:
            df['Wert'] = df['Wert'].fillna(df['Akt_Wert'])
            
    if 'Aktueller_Kurs' in df.columns:
        if 'Live_Kurs' not in df.columns:
            df['Live_Kurs'] = df['Aktueller_Kurs']
        else:
            df['Live_Kurs'] = df['Live_Kurs'].fillna(df['Aktueller_Kurs'])
            
    # Recalculate Kaufwert and Akt_Wert if St_Nom has changed in frontend
    if 'St_Nom' in df.columns:
        if 'Avg_Kaufkurs' in df.columns:
            df['Kaufwert'] = df['St_Nom'] * df['Avg_Kaufkurs']
            df['Kaufpreis'] = df['Kaufwert']
            
        if 'Live_Kurs' in df.columns:
            df['Akt_Wert'] = df['St_Nom'] * df['Live_Kurs']
            df['Live_Gesamtwert'] = df['Akt_Wert']
            df['Wert'] = df['Akt_Wert']
        
    gesamtwert, gewinn, performance, positions = berechne_portfolio_metriken(df, live_data_fetched=True)
    
    return PortfolioMetrics(
        gesamtwert=gesamtwert,
        gesamt_gewinn=gewinn,
        performance_prozent=performance,
        positions=positions
    )

@router.post("/analysis-prompt")
async def generate_analysis_prompt(req: CalculateMetricsRequest):
    df = pd.DataFrame(req.positions) if req.positions else pd.DataFrame()
    if df.empty:
        return {"prompt": "Kein Portfolio vorhanden."}
        
    for col in ['St_Nom', 'Kaufwert', 'Akt_Wert']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
            
    if 'Kaufpreis' not in df.columns:
        df['Kaufpreis'] = df.get('Kaufwert', 0.0)
    if 'Orderkost' not in df.columns:
        df['Orderkost'] = 0.0
        
    if 'Live_Gesamtwert' not in df.columns:
        df['Live_Gesamtwert'] = df.get('Akt_Wert', 0.0)
    if 'Wert' not in df.columns:
        df['Wert'] = df.get('Akt_Wert', 0.0)
        
    if 'Live_Kurs' not in df.columns:
        df['Live_Kurs'] = df.get('Aktueller_Kurs', 0.0)
        
    gesamtwert = df['Akt_Wert'].sum() if 'Akt_Wert' in df.columns else 0.0
    
    import sys, os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from backend.services.ai_service import prepare_anonymized_portfolio_data
    from backend.prompts import get_auto_analysis_initial_prompt
    
    portfolio_text = prepare_anonymized_portfolio_data(df, gesamtwert)
    prompt = get_auto_analysis_initial_prompt(portfolio_text)
    
    return {"prompt": prompt}

from fastapi.responses import StreamingResponse

@router.post("/analyze-stream")
async def analyze_portfolio_stream(req: CalculateMetricsRequest):
    df = pd.DataFrame(req.positions) if req.positions else pd.DataFrame()
    if df.empty:
        def empty_gen(): yield "Kein Portfolio vorhanden."
        return StreamingResponse(empty_gen(), media_type="text/plain")
        
    for col in ['St_Nom', 'Kaufwert', 'Akt_Wert']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
            
    if 'Kaufpreis' not in df.columns:
        df['Kaufpreis'] = df.get('Kaufwert', 0.0)
    if 'Orderkost' not in df.columns:
        df['Orderkost'] = 0.0
        
    if 'Live_Gesamtwert' not in df.columns:
        df['Live_Gesamtwert'] = df.get('Akt_Wert', 0.0)
    if 'Wert' not in df.columns:
        df['Wert'] = df.get('Akt_Wert', 0.0)
        
    if 'Live_Kurs' not in df.columns:
        df['Live_Kurs'] = df.get('Aktueller_Kurs', 0.0)
        
    gesamtwert = df['Akt_Wert'].sum() if 'Akt_Wert' in df.columns else 0.0
    
    import sys, os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from backend.services.ai_service import prepare_anonymized_portfolio_data, get_llm_response_stream
    from backend.prompts import get_auto_analysis_initial_prompt
    
    portfolio_text = prepare_anonymized_portfolio_data(df, gesamtwert)
    prompt = get_auto_analysis_initial_prompt(portfolio_text)
    
    # Provider-Auswahl ähnlich zur alten Streamlit-Logik (Fallback Kette)
    config = {
        "provider": "Google Gemini",
        "api_key": os.environ.get("GOOGLE_API_KEY", ""),
        "model": "gemini-2.5-flash"
    }
    
    if not config["api_key"] and os.environ.get("CLAUDE_API_KEY"):
        config = {
            "provider": "Anthropic Claude",
            "api_key": os.environ.get("CLAUDE_API_KEY", ""),
            "model": "claude-sonnet-4-6"
        }
    elif not config["api_key"] and os.environ.get("LOCAL_LLM_URL"):
        config = {
            "provider": "OpenAI / Local",
            "api_key": os.environ.get("LOCAL_LLM_KEY", ""),
            "model": "llama3",
            "base_url": os.environ.get("LOCAL_LLM_URL")
        }
        
    if not config["api_key"] and config["provider"] == "Google Gemini":
        def err_gen(): yield "⚠️ **Kein LLM konfiguriert:** Bitte hinterlege den GOOGLE_API_KEY in der Umgebung."
        return StreamingResponse(err_gen(), media_type="text/markdown")

    history = [{"role": "user", "content": prompt}]
    
    gen, err = get_llm_response_stream(config, history)
    
    if err:
        def sys_err_gen(): yield f"⚠️ **Fehler bei der KI-Analyse:**\n{err}"
        return StreamingResponse(sys_err_gen(), media_type="text/plain")
        
    return StreamingResponse(gen, media_type="text/plain")


