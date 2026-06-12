import yfinance as yf
from pydantic_ai import RunContext

async def get_live_ticker_data(ctx: RunContext, ticker: str) -> str:
    """
    Holt aktuelle Live-Marktdaten für ein gegebenes Börsen-Ticker-Symbol (z.B. AAPL, MSFT, TSLA).
    Nutze dieses Tool immer dann, wenn der Nutzer nach einem aktuellen Kurs, Kennzahlen (wie KGV, Dividende) 
    oder Preis-Entwicklungen einer bestimmten Aktie fragt.
    """
    try:
        if ctx.deps and hasattr(ctx.deps, 'status_callback') and ctx.deps.status_callback:
            await ctx.deps.status_callback(f"📈 Rufe Live-Daten für Ticker '{ticker}' ab...")
            
        import asyncio
        
        def fetch_data():
            t = yf.Ticker(ticker)
            info = t.info
            
            if not info or 'regularMarketPrice' not in info and 'currentPrice' not in info:
                # yfinance API sometimes fails or returns empty for bad tickers
                return f"Keine aktuellen Daten für Ticker {ticker} gefunden."
                
            current_price = info.get('currentPrice', info.get('regularMarketPrice', 'N/A'))
            currency = info.get('currency', 'USD')
            day_high = info.get('dayHigh', 'N/A')
            day_low = info.get('dayLow', 'N/A')
            fifty_two_high = info.get('fiftyTwoWeekHigh', 'N/A')
            fifty_two_low = info.get('fiftyTwoWeekLow', 'N/A')
            forward_pe = info.get('forwardPE', 'N/A')
            dividend_yield = info.get('dividendYield', 'N/A')
            
            summary = (
                f"Live-Daten für {ticker} ({info.get('shortName', '')}):\n"
                f"- Aktueller Kurs: {current_price} {currency}\n"
                f"- Tageshoch/-tief: {day_high} / {day_low}\n"
                f"- 52-Wochen Hoch/Tief: {fifty_two_high} / {fifty_two_low}\n"
                f"- Erwartetes KGV (Forward P/E): {forward_pe}\n"
            )
            
            if dividend_yield != 'N/A' and dividend_yield is not None:
                summary += f"- Dividendenrendite: {dividend_yield * 100:.2f}%\n"
                
            return summary

        return await asyncio.to_thread(fetch_data)

    except Exception as e:
        return f"Fehler beim Abruf der yfinance-Daten für {ticker}: {str(e)}"
