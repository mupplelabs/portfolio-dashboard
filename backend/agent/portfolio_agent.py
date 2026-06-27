import os
import json
from dataclasses import dataclass
from typing import List, Callable, Optional, Awaitable
from pydantic_ai import Agent, RunContext


@dataclass
class PortfolioDeps:
    user_id: str
    has_portfolio_loaded: bool = False
    portfolio_data: list = None
    portfolio_metrics: dict = None
    status_callback: Optional[Callable[[str], Awaitable[None]]] = None
    use_deep_search: bool = False
    use_reranker: bool = False
    market_context: str = ""

# Definition des Agenten
# Wir definieren hier keinen festen Model-String, 
# sondern übergeben das Model dynamisch beim Aufruf (run_stream)
portfolio_agent = Agent(
    deps_type=PortfolioDeps,
    retries=2
)

@portfolio_agent.system_prompt
def add_system_prompt(ctx: RunContext[PortfolioDeps]) -> str:
    import sys
    import os
    # Add parent dir to path if not there
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from prompts import get_advisor_system_prompt
    base_prompt = get_advisor_system_prompt()
    
    market_instruction = ""
    if getattr(ctx.deps, 'market_context', ''):
        market_instruction = f"\n\n--- AKTUELLE MARKT-RECHERCHE ---\nDas System hat folgende Fakten im Hintergrund für dich recherchiert:\n{ctx.deps.market_context}\n---------------------------------\nBitte beziehe diese Fakten in deine Antwort ein, wenn sie relevant sind!"
    
    ticker_instruction = "\n\n(Hinweis: Du hast Zugriff auf get_live_ticker_data. Nutze dieses Tool, wenn der Nutzer explizit nach einem Live-Kurs fragt.)"
    
    if ctx.deps.has_portfolio_loaded:
        tool_instruction = "\n\n(Hinweis: Der Benutzer hat sein Portfolio geladen. Bitte nutze zwingend deine Portfolio-Tools (z.B. get_portfolio_overview, get_top_positions), um detaillierte und korrekte Informationen aus seinen Finanzdaten abzufragen, wenn du seine Fragen beantwortest. Erfinde oder schätze keine Portfolio-Werte!)"
        return base_prompt + tool_instruction + market_instruction + ticker_instruction
    else:
        return base_prompt + "\n\n(Hinweis: Der Benutzer hat aktuell noch kein Portfolio geladen.)" + market_instruction + ticker_instruction



import tools.portfolio_tools as pt
portfolio_agent.tool(pt.get_portfolio_overview)
portfolio_agent.tool(pt.get_top_positions)
portfolio_agent.tool(pt.get_position_details)
portfolio_agent.tool(pt.get_sector_allocation)

import tools.finance_tools as ft
portfolio_agent.tool(ft.get_live_ticker_data)
