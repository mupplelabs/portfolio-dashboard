from typing import List, Dict, Any
from pydantic_ai import RunContext

# We import PortfolioDeps locally to avoid circular imports if needed, or just type check
from agent.portfolio_agent import PortfolioDeps

def get_portfolio_overview(ctx: RunContext[PortfolioDeps]) -> str:
    """Gibt eine aggregierte Übersicht über das gesamte Portfolio (Gesamtwert, Gesamtrendite etc.) zurück."""
    if not ctx.deps.portfolio_metrics:
        return "Keine Portfolio-Metriken verfügbar."
    
    m = ctx.deps.portfolio_metrics
    return (
        f"Portfolio Übersicht:\n"
        f"- Gesamtwert: {m.get('gesamtwert', 0):.2f} €\n"
        f"- Gesamt Gewinn/Verlust: {m.get('gesamt_gewinn', 0):.2f} € ({m.get('performance_prozent', 0):.2f}%)\n"
    )

def get_top_positions(ctx: RunContext[PortfolioDeps], n: int = 5) -> str:
    """Gibt die Top N Positionen sortiert nach ihrem aktuellen Wert im Portfolio zurück. Standardmäßig die Top 5."""
    if not ctx.deps.portfolio_data:
        return "Keine Portfolio-Daten verfügbar."
    
    data = ctx.deps.portfolio_data
    # Sort by value descending
    sorted_data = sorted(data, key=lambda x: x.get("Wert_EUR", 0), reverse=True)
    
    top_n = sorted_data[:n]
    if not top_n:
        return "Das Portfolio ist leer."
        
    result = f"Top {n} Positionen nach Wert:\n"
    for pos in top_n:
        result += f"- {pos.get('Name', 'Unbekannt')} ({pos.get('Ticker', '')}): {pos.get('Wert_EUR', 0):.2f} € (Gewinn: {pos.get('Gewinn_EUR', 0):.2f} €, {pos.get('Performance_Prozent', 0):.2f}%)\n"
    
    return result

def get_position_details(ctx: RunContext[PortfolioDeps], identifier: str) -> str:
    """Sucht nach einer bestimmten Position (z.B. AAPL, Apple) und gibt alle Metriken (Wert, Rendite, Dividenden) dafür zurück."""
    if not ctx.deps.portfolio_data:
        return "Keine Portfolio-Daten verfügbar."
    
    identifier_lower = identifier.lower()
    for pos in ctx.deps.portfolio_data:
        if pos.get("Ticker", "").lower() == identifier_lower or pos.get("Name", "").lower() == identifier_lower:
            # Format nicely
            return (
                f"Details für {pos.get('Name')} ({pos.get('Ticker')}):\n"
                f"- Typ: {pos.get('Typ', 'N/A')} | WKN: {pos.get('WKN', 'N/A')}\n"
                f"- Branche: {pos.get('Branche', 'N/A')} | Region: {pos.get('Region', 'N/A')}\n"
                f"- Stücke: {pos.get('Stuecke', 0)} | Einstandskurs: {pos.get('Einstandskurs_EUR', 0):.2f} €\n"
                f"- Aktueller Kurs: {pos.get('Aktueller_Kurs_EUR', 0):.2f} €\n"
                f"- Investiert: {pos.get('Investiert_EUR', 0):.2f} € | Aktueller Wert: {pos.get('Wert_EUR', 0):.2f} €\n"
                f"- Gewinn/Verlust: {pos.get('Gewinn_EUR', 0):.2f} € ({pos.get('Performance_Prozent', 0):.2f}%)\n"
                f"- Gewichtung im Portfolio: {pos.get('Gewichtung_Prozent', 0):.2f}%\n"
                f"- Dividende (Jahr): {pos.get('Dividende_EUR', 0):.2f} €\n"
            )
            
    return f"Position '{identifier}' nicht im Portfolio gefunden."

def get_sector_allocation(ctx: RunContext[PortfolioDeps]) -> str:
    """Gibt eine Liste der Branchen/Sektoren des Portfolios und deren anteiligen Wert zurück."""
    if not ctx.deps.portfolio_data:
        return "Keine Portfolio-Daten verfügbar."
    
    sectors = {}
    total_value = 0
    for pos in ctx.deps.portfolio_data:
        sector = pos.get("Branche", "Unbekannt")
        val = pos.get("Wert_EUR", 0)
        sectors[sector] = sectors.get(sector, 0) + val
        total_value += val
        
    if total_value == 0:
        return "Gesamtwert ist 0, keine Sektor-Allokation berechenbar."
        
    result = "Sektor-Allokation:\n"
    # Sort by value descending
    sorted_sectors = sorted(sectors.items(), key=lambda x: x[1], reverse=True)
    
    for sector, val in sorted_sectors:
        pct = (val / total_value) * 100
        result += f"- {sector}: {val:.2f} € ({pct:.2f}%)\n"
        
    return result
