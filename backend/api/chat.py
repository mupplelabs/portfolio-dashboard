from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from agent.portfolio_agent import portfolio_agent, PortfolioDeps
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prompts import get_summary_prompt
from pydantic import BaseModel

from agent.router import analyze_intent
from rag.rag_pipeline import run_rag_search
from token_db import insert_usage, get_usage_timeline
router = APIRouter()

class ChatSummaryRequest(BaseModel):
    portfolio_summary: str
    message_history: list[dict]
    provider: str = "Google Gemini"
    model: str = "gemini-2.5-flash"
    apiKey: str = ""
    baseUrl: str = "http://localhost:11434/v1"

from api.settings import get_api_key_for_provider

@router.post("/api/chat/summary")
async def generate_chat_summary(req: ChatSummaryRequest):
    # Fetch API key from DB if missing or masked
    api_key = req.apiKey
    if not api_key or api_key in ["sk-***", "AIza***", "***"]:
        api_key = get_api_key_for_provider(req.provider)
        
    # Convert dict history to PydanticAI message objects if needed,
    # but actually we can just format it as a big text block for the summary.
    history_text = ""
    for msg in req.message_history:
        role = "User" if msg.get("role") == "user" else "Advisor"
        history_text += f"{role}: {msg.get('content', '')}\n\n"
        
    ai_model = 'google:gemini-2.5-flash' # Default
    if req.provider == "Anthropic Claude":
        if api_key:
            from pydantic_ai.providers.anthropic import AnthropicProvider
            from pydantic_ai.models.anthropic import AnthropicModel
            custom_provider = AnthropicProvider(api_key=api_key)
            ai_model = AnthropicModel(req.model, provider=custom_provider)
        else:
            ai_model = f"anthropic:{req.model}"
    elif req.provider == "Google Gemini":
        if api_key:
            from pydantic_ai.providers.google import GoogleProvider
            from pydantic_ai.models.google import GoogleModel
            custom_provider = GoogleProvider(api_key=api_key)
            ai_model = GoogleModel(req.model, provider=custom_provider)
        else:
            ai_model = f"google:{req.model}"
    elif req.provider == "OpenAI / Local":
        from pydantic_ai.providers.openai import OpenAIProvider
        from pydantic_ai.models.openai import OpenAIChatModel
        local_key = api_key if api_key else "dummy"
        custom_provider = OpenAIProvider(base_url=req.baseUrl, api_key=local_key)
        ai_model = OpenAIChatModel(req.model, provider=custom_provider)
        
    from pydantic_ai import Agent
    summary_agent = Agent(
        model=ai_model,
        system_prompt=get_summary_prompt()
    )
    
    prompt = f"Portfolio Kontext:\n{req.portfolio_summary}\n\nBisheriger Chatverlauf:\n{history_text}"
    
    from fastapi.responses import StreamingResponse
    
    async def generate():
        try:
            async with summary_agent.run_stream(prompt) as result:
                async for text in result.stream_text(delta=True):
                    yield text
        except Exception as e:
            yield f"\n\nFehler bei der Zusammenfassung: {str(e)}"
            
    return StreamingResponse(generate(), media_type="text/plain")


@router.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # Callback für Tool-Status-Updates (als 'thinking' damit sie im Verlauf bleiben)
    async def send_status(message: str):
        await websocket.send_json({"type": "thinking", "text": message})
        
    # Initiale Abhängigkeiten (Deps) für diesen Socket/User
    deps = PortfolioDeps(
        user_id="default_user",
        has_portfolio_loaded=False,
        portfolio_data=None,
        portfolio_metrics=None,
        status_callback=send_status
    )
    
    # Message History (für den Kontext)
    message_history = []
    
    try:
        while True:
            # Empfange Daten vom Client (JSON)
            data_str = await websocket.receive_text()
            data = json.loads(data_str)
            
            # Update Deps, falls das Frontend aktuelle Portfolio-Zahlen mitgeschickt hat
            if "portfolio_data" in data and "portfolio_metrics" in data:
                deps.portfolio_data = data["portfolio_data"]
                deps.portfolio_metrics = data["portfolio_metrics"]
                deps.has_portfolio_loaded = bool(deps.portfolio_data and len(deps.portfolio_data) > 0)
                
            user_message = data.get("message", "")
            if not user_message:
                continue
                
            # --- Dynamische Model-Auswahl ---
            provider = data.get("provider", "Google Gemini")
            model_name = data.get("model", "gemini-2.5-flash")
            api_key = data.get("apiKey", "")
            base_url = data.get("baseUrl", "http://localhost:11434/v1")
            use_deep_search = data.get("useDeepSearch", False)
            use_reranker = data.get("useReranker", False)
            
            research_provider = data.get("researchProvider", provider)
            research_model_name = data.get("researchModel", model_name)
            research_api_key = data.get("researchApiKey", api_key)
            
            # PydanticAI unterstützt alle drei Provider nativ!
            # Helper Funktion um PydanticAI Model-Objekte zu generieren
            def build_model(prov, mod_name, key, url):
                if not key or key in ["sk-***", "AIza***", "***"]:
                    key = get_api_key_for_provider(prov)
                    
                if prov == "Anthropic Claude":
                    if key:
                        os.environ["ANTHROPIC_API_KEY"] = key
                    return f"anthropic:{mod_name}"
                elif prov == "Google Gemini":
                    if key:
                        from pydantic_ai.providers.google import GoogleProvider
                        from pydantic_ai.models.google import GoogleModel
                        return GoogleModel(mod_name, provider=GoogleProvider(api_key=key))
                    return f"google:{mod_name}"
                elif prov == "OpenAI / Local":
                    from pydantic_ai.providers.openai import OpenAIProvider
                    from pydantic_ai.models.openai import OpenAIChatModel
                    local_key = key if key else "dummy"
                    return OpenAIChatModel(mod_name, provider=OpenAIProvider(base_url=url, api_key=local_key))
                return f"google:{mod_name}"

            ai_model = build_model(provider, model_name, api_key, base_url)
            research_ai_model = build_model(research_provider, research_model_name, research_api_key, base_url)

            try:
                # Aktualisiere Web-Search Einstellungen auf dem bestehenden deps Objekt
                deps.use_deep_search = use_deep_search
                deps.use_reranker = use_reranker
                deps.market_context = ""
                
                # Sende initiales Status-Update
                await websocket.send_json({"type": "thinking_start"})
                
                # === 1. Semantic Routing ===
                import asyncio
                route = await asyncio.to_thread(analyze_intent, user_message)
                
                # === 2. Research Pipeline (falls nötig) ===
                if route == "research_needed" and use_deep_search:
                    await websocket.send_json({"type": "status", "text": "🎯 Router: Websuche erforderlich."})
                    async def send_rag_status(msg: str):
                        await websocket.send_json({"type": "status", "text": msg})
                        
                    research_briefing = await run_rag_search(
                        query=user_message,
                        use_reranker=use_reranker,
                        status_callback=send_rag_status
                    )
                    deps.market_context = research_briefing
                    await websocket.send_json({"type": "status", "text": "✅ Research Briefing generiert. Berate Portfolio..."})
                elif route == "portfolio_only":
                    await websocket.send_json({"type": "status", "text": "🎯 Router: Lokale Portfolio-Daten ausreichend."})
                else:
                    await websocket.send_json({"type": "status", "text": "Analysiere Anfrage..."})
                
                final_prompt = user_message
                
                await websocket.send_json({"type": "thinking_done"})

                # Agent asynchron mit iter() ausführen für feingranulares Streaming
                try:
                    async with portfolio_agent.iter(
                        final_prompt,
                        deps=deps,
                        message_history=message_history,
                        model=ai_model,
                        model_settings={'max_tokens': 4096}
                    ) as agent_run:
                        async for node in agent_run:
                            if not hasattr(node, "stream"):
                                continue

                            async with node.stream(agent_run.ctx) as streamed:
                                async for event in streamed:
                                    event_name = type(event).__name__

                                    # ── Deltas (live streaming) ──────────────────────────────
                                    if event_name == "PartDeltaEvent":
                                        delta = event.delta
                                        if type(delta).__name__ == "TextPartDelta":
                                            content = getattr(delta, 'content_delta', '')
                                            if content:
                                                await websocket.send_json({"type": "chunk", "text": content})

                                    # ── Part Start (erster Buchstabe) ────────────────────────
                                    elif event_name == "PartStartEvent":
                                        part = getattr(event, 'part', None)
                                        if part:
                                            ptype = type(part).__name__
                                            if ptype == "TextPart":
                                                content = getattr(part, 'content', '')
                                                if content:
                                                    await websocket.send_json({"type": "chunk", "text": content})
                                                    
                                    # ── Part vollständig angekommen ──────────────────────────
                                    elif event_name == "PartEndEvent":
                                        part = event.part
                                        ptype = type(part).__name__

                                        if ptype == "ToolCallPart":
                                            # Signal an Frontend: Den bisherigen Text in die Denk-Blase verschieben!
                                            await websocket.send_json({
                                                "type": "shift_to_thinking", 
                                                "tool": getattr(part, 'tool_name', 'tool')
                                            })
                                        elif ptype == "TextPart":
                                            # Sende den kompletten, validierten Textblock als Überschreibung,
                                            # um verlorene Deltas zu korrigieren!
                                            content = getattr(part, 'content', '')
                                            if content:
                                                await websocket.send_json({"type": "replace", "text": content})

                                    # ── Tool-Ergebnis ────────────────────────────────────────
                                    elif event_name == "FunctionToolResultEvent":
                                        # Optional: Ein kleines Status-Update, dass das Tool fertig ist
                                        # await websocket.send_json({"type": "status", "text": f"✅ Daten geladen."})
                                        pass
                    
                    # Speichere die neuen Nachrichten im Kontext für die nächste Frage
                    message_history = agent_run.result.new_messages()
                    
                    # Token Tracking
                    usage = getattr(agent_run.result, 'usage', None)
                    if usage:
                        req_tokens = getattr(usage, 'request_tokens', getattr(usage, 'requests', getattr(usage, 'prompt_tokens', 0)))
                        res_tokens = getattr(usage, 'response_tokens', getattr(usage, 'responses', getattr(usage, 'completion_tokens', 0)))
                        import asyncio
                        asyncio.create_task(asyncio.to_thread(
                            insert_usage, 
                            provider, 
                            model_name, 
                            req_tokens, 
                            res_tokens
                        ))
                    
                    # Sende End-Signal
                    await websocket.send_json({"type": "done"})
                except Exception as e:
                    error_msg = str(e)
                    if "503" in error_msg or "Service Unavailable" in error_msg:
                        user_error = "Fehler: Die KI-Schnittstelle (Provider) ist momentan überlastet (HTTP 503). Bitte versuche es in ein paar Sekunden erneut."
                    elif "429" in error_msg or "Too Many Requests" in error_msg:
                        user_error = "Fehler: Du hast das Rate-Limit des KI-Providers erreicht (HTTP 429). Bitte warte kurz."
                    elif "400" in error_msg or "Invalid api_key" in error_msg:
                        user_error = "Fehler: Der API-Key ist ungültig oder abgelaufen (HTTP 400). Bitte überprüfe die Einstellungen."
                    else:
                        user_error = f"Fehler bei der KI-Generierung: {error_msg}"
                        
                    await websocket.send_json({"type": "error", "text": user_error})
                    # Wichtig: done senden, damit das Frontend nicht im 'waiting' Status hängt
                    await websocket.send_json({"type": "done"})
                
            except WebSocketDisconnect:
                print("Client hat die Verbindung während der Generierung abgebrochen.")
                break
            except RuntimeError as e:
                if "close message has been sent" in str(e):
                    print("Verbindung bereits geschlossen.")
                    break
                raise
            except Exception as e:
                try:
                    await websocket.send_json({"type": "error", "text": f"Agent Error: {str(e)}"})
                except RuntimeError:
                    print("Konnte Fehler nicht senden, da WebSocket bereits geschlossen ist.")
                    break
    except WebSocketDisconnect:
        print("Client disconnected")

@router.get("/api/tokens/stats")
async def get_token_stats(unit: str = 'week', offset: int = 0):
    """Returns the aggregated token usage stats for timeline."""
    import asyncio
    stats = await asyncio.to_thread(get_usage_timeline, unit, offset)
    return {"stats": stats}

class TitleGenerationRequest(BaseModel):
    chat_content: str
    provider: str = "Google Gemini"
    model: str = "gemini-2.5-flash"
    apiKey: str = ""
    baseUrl: str = "http://localhost:11434/v1"

@router.post("/api/chat/generate-title")
async def generate_chat_title(req: TitleGenerationRequest):
    from pydantic_ai import Agent
    from llm_factory import get_llm_model
    from agent.router import analyze_intent
    from rag.rag_pipeline import run_rag_search
    
    title_agent = Agent(
        system_prompt="Du bist ein Editor für Finanz-Reports. Generiere für den folgenden Text eine sehr kurze, prägnante Überschrift (maximal 6 Wörter, keine Satzzeichen am Ende, kein Markdown).",
    )
    
    ai_model = get_llm_model(req.provider, req.model, req.apiKey, req.baseUrl)
    
    try:
        result = await title_agent.run(f"Text:\n{req.chat_content}", model=ai_model)
        return {"title": result.output.strip()}
    except Exception as e:
        return {"title": "KI Analyse"}
