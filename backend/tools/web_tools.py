import httpx
from bs4 import BeautifulSoup
from ddgs import DDGS
from pydantic_ai import RunContext

# Das PydanticAI Framework wird die Docstrings nutzen, 
# um dem LLM zu erklären, was die Tools tun!

async def search_web(ctx: RunContext, query: str, max_results: int = 3) -> str:
    """
    Sucht im Internet (Web) nach dem gegebenen Suchbegriff.
    Nutze dieses Tool, um aktuelle Nachrichten, Fakten oder generelle Informationen zu finden.
    Es liefert kurze Snippets und die URLs der Ergebnisse zurück.
    """
    try:
        if ctx.deps and hasattr(ctx.deps, 'status_callback') and ctx.deps.status_callback:
            await ctx.deps.status_callback(f"🔎 Suche im Web nach: '{query}'...")
            
        def do_search():
            with DDGS() as ddgs:
                return list(ddgs.text(query, max_results=max_results))
                
        import asyncio
        results = await asyncio.to_thread(do_search)
        
        if not results:
            return "Keine Ergebnisse gefunden."
            
        output = []
        for r in results:
            output.append(f"Titel: {r['title']}\nURL: {r['href']}\nAuszug: {r['body']}\n")
            
        return "\n".join(output)
        
    except Exception as e:
        return f"Fehler bei der Websuche: {str(e)}"

async def read_webpage(ctx: RunContext, url: str) -> str:
    """
    Lädt den Textinhalt einer Webseite herunter. 
    Nutze dieses Tool, wenn ein Such-Snippet (aus search_web) nicht ausreicht 
    und du den kompletten Artikel lesen musst, um eine Frage zu beantworten.
    """
    try:
        if ctx.deps and hasattr(ctx.deps, 'status_callback') and ctx.deps.status_callback:
            domain = url.split("//")[-1].split("/")[0]
            await ctx.deps.status_callback(f"📄 Lese Artikel auf {domain}...")
            
        async with httpx.AsyncClient(follow_redirects=True) as client:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            resp = await client.get(url, headers=headers, timeout=10.0)
            
            if resp.status_code != 200:
                return f"Fehler: Seite konnte nicht geladen werden (Status {resp.status_code})"
                
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Skripte und Styles entfernen
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
                
            text = soup.get_text(separator=' ', strip=True)
            # Kürze extrem lange Texte
            if len(text) > 15000:
                text = text[:15000] + " ... [Text abgeschnitten]"
                
            return text
            
    except Exception as e:
        return f"Fehler beim Lesen der Webseite: {str(e)}"
