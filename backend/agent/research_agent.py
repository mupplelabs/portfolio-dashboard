import sys
import os
from typing import Optional, Callable, Awaitable
from dataclasses import dataclass
from pydantic_ai import Agent, RunContext

@dataclass
class ResearchDeps:
    status_callback: Optional[Callable[[str], Awaitable[None]]] = None

# Der Research Agent gibt nun einen fertigen Text (Zusammenfassung) zurück, 
# statt nur einer strukturierten Liste von Queries.
research_agent = Agent(
    deps_type=ResearchDeps,
    output_type=str,
    retries=2
)

@research_agent.system_prompt
def add_research_prompt(ctx: RunContext) -> str:
    return (
        "Du bist ein intelligenter Research-Assistent für ein Finanz-Portfolio-Dashboard. "
        "Deine Aufgabe ist es, aktuelle Informationen, Nachrichten und Live-Börsenkurse zu beschaffen, "
        "die zur Beantwortung der Nutzerfrage notwendig sind.\n\n"
        "Regeln:\n"
        "1. Nutze die verfügbaren Tools (search_web, get_live_ticker_data, read_webpage) so oft wie nötig.\n"
        "2. Wenn die Frage offensichtlich kein aktuelles Wissen erfordert, gib einfach 'Keine Recherche nötig.' zurück.\n"
        "3. Lese komplette Artikel via read_webpage nur, wenn die Such-Snippets nicht ausreichen.\n"
        "4. Fasse am Ende alle gefundenen relevanten Fakten kompakt zusammen. Diese Zusammenfassung "
        "wird als Kontext an den Haupt-Agenten übergeben."
    )

# Registrierung der Tools
import tools.web_tools as web_tools
import tools.finance_tools as finance_tools

research_agent.tool(web_tools.search_web)
research_agent.tool(web_tools.read_webpage)
research_agent.tool(finance_tools.get_live_ticker_data)
