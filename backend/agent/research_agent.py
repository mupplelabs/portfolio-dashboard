import sys
import os
from typing import List
from pydantic_ai import Agent, RunContext
from pydantic import BaseModel

class SearchQueries(BaseModel):
    web_queries: List[str]
    tickers: List[str]
    reasoning: str

research_agent = Agent(
    output_type=SearchQueries
)

@research_agent.system_prompt
def add_research_prompt(ctx: RunContext) -> str:
    # Add parent dir to path if not there
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from prompts import get_search_context_prompt
    
    # Wir rufen den Prompt auf. Da wir nicht wissen, ob es eine Portfolio Analyse ist,
    # setzen wir is_portfolio_analysis auf True, wenn das Portfolio übergeben wurde.
    # Da dies aktuell nicht direkt im RunContext liegt, nehmen wir den generischen oder passen es an.
    # Für Pydantic-AI reicht uns der "system_instruction" Teil.
    system_inst, _ = get_search_context_prompt("", is_portfolio_analysis=True)
    
    # Wir schneiden den harten JSON-Formatierungs-Block ab, da Pydantic-AI das eigene Schema anhängt
    base_prompt = system_inst.split("Format:")[0]
    
    return base_prompt + "\nZusätzlich: Schreibe eine kurze Begründung (reasoning), warum diese gesucht werden sollen."
