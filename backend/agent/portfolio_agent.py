import os
import json
from dataclasses import dataclass
from typing import List, Callable, Optional, Awaitable
from pydantic_ai import Agent, RunContext


@dataclass
class PortfolioDeps:
    user_id: str
    has_portfolio_loaded: bool = False
    portfolio_summary: str = ""
    status_callback: Optional[Callable[[str], Awaitable[None]]] = None

# Definition des Agenten
# Wir definieren hier keinen festen Model-String, 
# sondern übergeben das Model dynamisch beim Aufruf (run_stream)
portfolio_agent = Agent(
    deps_type=PortfolioDeps
)

@portfolio_agent.system_prompt
def add_system_prompt(ctx: RunContext[PortfolioDeps]) -> str:
    import sys
    import os
    # Add parent dir to path if not there
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from prompts import get_advisor_system_prompt
    base_prompt = get_advisor_system_prompt()
    
    if ctx.deps.has_portfolio_loaded:
        portfolio_info = f"\n\n--- AKTUELLE PORTFOLIO-DATEN ---\n{ctx.deps.portfolio_summary}\n--------------------------------"
        return base_prompt + portfolio_info
    else:
        return base_prompt + "\n\n(Hinweis: Der Benutzer hat aktuell noch kein Portfolio geladen.)"



