from typing import List, Dict, Any
from pydantic_ai import RunContext

# We import PortfolioDeps locally to avoid circular imports if needed, or just type check
from agent.portfolio_agent import PortfolioDeps

async def get_portfolio_overview(ctx: RunContext[PortfolioDeps]) -> str:
    """Gibt eine aggregierte Übersicht über das gesamte Portfolio (Gesamtwert, Gesamtrendite etc.) zurück."""
    print("🛠️  [TOOL CALL] get_portfolio_overview: Lade aggregierte Portfolio-Daten...")
    if ctx.deps.status_callback:
        await ctx.deps.status_callback("📊 Rufe aggregierte Portfolio-Daten ab...")
        
    if not ctx.deps.portfolio_metrics:
        return "Keine Portfolio-Metriken verfügbar."
    
    m = ctx.deps.portfolio_metrics
    return (
        f"Portfolio Übersicht:\n"
        f"- Gesamtwert: {m.get('gesamtwert', 0):.2f} €\n"
        f"- Gesamt Gewinn/Verlust: {m.get('gesamt_gewinn', 0):.2f} € ({m.get('performance_prozent', 0):.2f}%)\n"
    )

async def get_top_positions(ctx: RunContext[PortfolioDeps], n: int = 5, filter_field: str = None, filter_value: str = None) -> str:
    """
    Gibt die Top N Positionen sortiert nach ihrem aktuellen Wert im Portfolio zurück. Standardmäßig die Top 5.
    Optional kann nach einem Feld gefiltert werden (z.B. filter_field='Typ', filter_value='ETF').
    """
    print(f"🛠️  [TOOL CALL] get_top_positions: Analysiere die Top {n} Positionen (Filter: {filter_field}={filter_value})...")
    if ctx.deps.status_callback:
        await ctx.deps.status_callback(f"📈 Analysiere die Top {n} Positionen...")
        
    if not ctx.deps.portfolio_data:
        return "Keine Portfolio-Daten verfügbar."
    
    data = ctx.deps.portfolio_data
    
    if filter_field and filter_value:
        data = [p for p in data if str(p.get(filter_field, '')).lower() == str(filter_value).lower()]
        if not data:
            return f"Keine Positionen gefunden, die {filter_field} = '{filter_value}' entsprechen."
            
    # Sort by value descending
    sorted_data = sorted(data, key=lambda x: x.get("Akt_Wert", 0), reverse=True)
    
    top_n = sorted_data[:n]
    if not top_n:
        return "Das Portfolio ist leer."
        
    result = f"Top {n} Positionen nach Wert:\n"
    for pos in top_n:
        result += f"- {pos.get('Wertpapier', 'Unbekannt')} ({pos.get('Ticker', '')}) [Typ: {pos.get('Typ', 'Unbekannt')}, Branche: {pos.get('Branche', 'Unbekannt')}]: {pos.get('Akt_Wert', 0):.2f} € (Gewinn: {pos.get('Gewinn_Verlust', 0):.2f} €, {pos.get('Performance', 0):.2f}%)\n"
    
    return result

async def get_position_details(ctx: RunContext[PortfolioDeps], identifier: str) -> str:
    """Sucht nach einer bestimmten Position (z.B. AAPL, Apple) und gibt alle Metriken (Wert, Rendite, Dividenden) dafür zurück."""
    print(f"🛠️  [TOOL CALL] get_position_details: Suche Details für '{identifier}'...")
    if ctx.deps.status_callback:
        await ctx.deps.status_callback(f"🔍 Lade detaillierte Kennzahlen für '{identifier}' aus dem Portfolio...")
        
    if not ctx.deps.portfolio_data:
        return "Keine Portfolio-Daten verfügbar."
    
    identifier_lower = identifier.lower()
    for pos in ctx.deps.portfolio_data:
        if pos.get("Ticker", "").lower() == identifier_lower or pos.get("Wertpapier", "").lower() == identifier_lower:
            # Format nicely
            return (
                f"Details für {pos.get('Wertpapier')} ({pos.get('Ticker')}):\n"
                f"- Typ: {pos.get('Typ', 'N/A')} | WKN: {pos.get('WKN', 'N/A')} | ISIN: {pos.get('ISIN', 'N/A')}\n"
                f"- Branche: {pos.get('Branche', 'N/A')} | Region: {pos.get('Region', 'N/A')}\n"
                f"- Stücke: {pos.get('St_Nom', 0)} | Einstandskurs: {pos.get('Avg_Kaufkurs', 0):.2f} €\n"
                f"- Aktueller Kurs: {pos.get('Aktueller_Kurs', 0):.2f} €\n"
                f"- Investiert: {pos.get('Kaufwert', 0):.2f} € | Aktueller Wert: {pos.get('Akt_Wert', 0):.2f} €\n"
                f"- Gewinn/Verlust: {pos.get('Gewinn_Verlust', 0):.2f} € ({pos.get('Performance', 0):.2f}%)\n"
                f"- Dividende (Jahr): {pos.get('Dividende', 0):.2f} €\n"
            )
            
    return f"Position '{identifier}' nicht im Portfolio gefunden."

async def get_sector_allocation(ctx: RunContext[PortfolioDeps], field: str = "Branche") -> str:
    """
    Gibt die Verteilung des Portfolios nach einem bestimmten Feld zurück (z.B. 'Branche', 'Region' oder 'Typ').
    Hilfreich um Klumpenrisiken und Diversifikation zu analysieren.
    """
    print(f"🛠️  [TOOL CALL] get_sector_allocation: Berechne Verteilung für Feld '{field}'...")
    if ctx.deps.status_callback:
        await ctx.deps.status_callback(f"🥧 Berechne Portfolio-Verteilung nach '{field}'...")
        
    if not ctx.deps.portfolio_data:
        return "Keine Portfolio-Daten verfügbar."
    
    sectors = {}
    total_value = 0
    for pos in ctx.deps.portfolio_data:
        sector = pos.get(field, "Unbekannt")
        val = pos.get("Akt_Wert", 0)
        sectors[sector] = sectors.get(sector, 0) + val
        total_value += val
        
    if total_value == 0:
        return f"Gesamtwert ist 0, keine {field}-Allokation berechenbar."
        
    result = f"{field}-Allokation:\n"
    # Sort by value descending
    sorted_sectors = sorted(sectors.items(), key=lambda x: x[1], reverse=True)
    
    for sector, val in sorted_sectors:
        pct = (val / total_value) * 100
        result += f"- {sector}: {val:.2f} € ({pct:.2f}%)\n"
        
    return result
