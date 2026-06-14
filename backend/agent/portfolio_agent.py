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
        tool_instruction = "\n\n(Hinweis: Der Benutzer hat sein Portfolio geladen. Bitte nutze zwingend deine Portfolio-Tools (z.B. get_portfolio_overview, get_top_positions), um detaillierte und korrekte Informationen aus seinen Finanzdaten abzufragen, wenn du seine Fragen beantwortest. Erfinde oder schätze keine Portfolio-Werte!)"
        return base_prompt + tool_instruction
    else:
        return base_prompt + "\n\n(Hinweis: Der Benutzer hat aktuell noch kein Portfolio geladen.)"

import tools.portfolio_tools as pt
portfolio_agent.tool(pt.get_portfolio_overview)
portfolio_agent.tool(pt.get_top_positions)
portfolio_agent.tool(pt.get_position_details)
portfolio_agent.tool(pt.get_sector_allocation)



