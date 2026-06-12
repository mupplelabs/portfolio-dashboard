from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from agent.portfolio_agent import portfolio_agent, PortfolioDeps
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prompts import get_summary_prompt
from pydantic import BaseModel

router = APIRouter()

class ChatSummaryRequest(BaseModel):
    portfolio_summary: str
    message_history: list[dict]
    provider: str = "Google Gemini"
    model: str = "gemini-2.5-flash"
    apiKey: str = ""
    baseUrl: str = "http://localhost:11434/v1"

@router.post("/api/chat/summary")
async def generate_chat_summary(req: ChatSummaryRequest):
    # Convert dict history to PydanticAI message objects if needed,
    # but actually we can just format it as a big text block for the summary.
    history_text = ""
    for msg in req.message_history:
        role = "User" if msg.get("role") == "user" else "Advisor"
        history_text += f"{role}: {msg.get('content', '')}\n\n"
        
    ai_model = 'google:gemini-2.5-flash' # Default
    if req.provider == "Anthropic Claude":
        if req.apiKey:
            from pydantic_ai.providers.anthropic import AnthropicProvider
            from pydantic_ai.models.anthropic import AnthropicModel
            custom_provider = AnthropicProvider(api_key=req.apiKey)
            ai_model = AnthropicModel(req.model, provider=custom_provider)
        else:
            ai_model = f"anthropic:{req.model}"
    elif req.provider == "Google Gemini":
        if req.apiKey:
            from pydantic_ai.providers.google import GoogleProvider
            from pydantic_ai.models.google import GoogleModel
            custom_provider = GoogleProvider(api_key=req.apiKey)
            ai_model = GoogleModel(req.model, provider=custom_provider)
        else:
            ai_model = f"google:{req.model}"
    elif req.provider == "OpenAI / Local":
        from pydantic_ai.providers.openai import OpenAIProvider
        from pydantic_ai.models.openai import OpenAIChatModel
        local_key = req.apiKey if req.apiKey else "dummy"
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
    
    # Callback für Tool-Status-Updates
    async def send_status(message: str):
        await websocket.send_json({"type": "status", "text": message})
        
    # Initiale Abhängigkeiten (Deps) für diesen Socket/User
    deps = PortfolioDeps(
        user_id="default_user",
        has_portfolio_loaded=False,
        portfolio_summary="",
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
            if "portfolio_summary" in data:
                deps.portfolio_summary = data["portfolio_summary"]
                deps.has_portfolio_loaded = bool(deps.portfolio_summary)
                
            user_message = data.get("message", "")
            if not user_message:
                continue
                
            # --- Dynamische Model-Auswahl ---
            provider = data.get("provider", "Google Gemini")
            model_name = data.get("model", "gemini-2.5-flash")
            api_key = data.get("apiKey", "")
            base_url = data.get("baseUrl", "http://localhost:11434/v1")
            
            # PydanticAI unterstützt alle drei Provider nativ!
            # Wir mappen sie hier auf die PydanticAI Syntax:
            ai_model = 'google:gemini-2.5-flash' # Default
            if provider == "Anthropic Claude":
                if api_key:
                    from pydantic_ai.providers.anthropic import AnthropicProvider
                    from pydantic_ai.models.anthropic import AnthropicModel
                    custom_provider = AnthropicProvider(api_key=api_key)
                    ai_model = AnthropicModel(model_name, provider=custom_provider)
                else:
                    ai_model = f"anthropic:{model_name}"
            elif provider == "Google Gemini":
                if api_key:
                    from pydantic_ai.providers.google import GoogleProvider
                    from pydantic_ai.models.google import GoogleModel
                    custom_provider = GoogleProvider(api_key=api_key)
                    ai_model = GoogleModel(model_name, provider=custom_provider)
                else:
                    ai_model = f"google:{model_name}"
            elif provider == "OpenAI / Local":
                from pydantic_ai.providers.openai import OpenAIProvider
                from pydantic_ai.models.openai import OpenAIChatModel
                local_key = api_key if api_key else "dummy"
                custom_provider = OpenAIProvider(base_url=base_url, api_key=local_key)
                ai_model = OpenAIChatModel(model_name, provider=custom_provider)

            try:
                # Sende initiales Status-Update
                await websocket.send_json({"type": "thinking_start"})
                
                # --- Pre-Search Logik (Agent 1) ---
                search_context = ""
                from agent.research_agent import research_agent, ResearchDeps
                from pydantic_ai import Agent
                
                # 1. Router: Brauchen wir Research?
                router_agent = Agent(
                    model=ai_model,
                    output_type=bool,
                    system_prompt=(
                        "Entscheide, ob zur Beantwortung der User-Frage eine Internetrecherche (News) "
                        "oder aktuelle Live-Kurse (Börsen-Ticker) zwingend nötig sind. "
                        "Antworte mit True, wenn ja, ansonsten mit False."
                    )
                )
                
                await websocket.send_json({"type": "thinking", "text": "🤔 Prüfe ob externe Recherche nötig ist..."})
                try:
                    router_prompt = f"User: {user_message}"
                    route_result = await router_agent.run(router_prompt)
                    needs_research = route_result.output
                    
                    if needs_research:
                        await websocket.send_json({"type": "thinking", "text": "🔎 Aktiviere Research Agent für Informationsbeschaffung..."})
                        
                        research_prompt = user_message
                        if deps.has_portfolio_loaded:
                            research_prompt += f"\n\nPortfolio Kontext:\n{deps.portfolio_summary}"
                            
                        # Baue Research Dependencies für Status Callbacks
                        res_deps = ResearchDeps(status_callback=send_status)
                        
                        research_result = await research_agent.run(
                            research_prompt,
                            model=ai_model,
                            deps=res_deps
                        )
                        
                        result_text = research_result.output
                        if "Keine Recherche nötig" not in result_text:
                            search_context = f"\n\n[SYSTEM-HINWEIS: Ein interner Research-Agent hat folgende topaktuelle Fakten für dich recherchiert. Nutze sie zwingend für deine Antwort, tu aber so, als wäre es dein eigenes Wissen:]\n{result_text}\n[ENDE SYSTEM-HINWEIS]"
                    else:
                        await websocket.send_json({"type": "thinking", "text": "ℹ️ Keine externe Websuche nötig."})
                        
                except Exception as e:
                    await websocket.send_json({"type": "thinking", "text": f"⚠️ Research fehlgeschlagen: {str(e)}"})
                
                final_prompt = user_message + search_context
                
                await websocket.send_json({"type": "thinking_done"})
                await websocket.send_json({"type": "status", "text": "Generiere finales Gutachten..."})

                # Agent asynchron mit Stream ausführen, model dynamisch übergeben
                async with portfolio_agent.run_stream(
                    final_prompt,
                    deps=deps,
                    message_history=message_history,
                    model=ai_model
                ) as result:
                    async for chunk in result.stream_text(delta=True):
                        # Sende den Chunk sofort via WebSocket ans Frontend
                        await websocket.send_json({"type": "chunk", "text": chunk})
                
                # Speichere die neuen Nachrichten im Kontext für die nächste Frage
                message_history = result.new_messages()
                
                # Sende End-Signal
                await websocket.send_json({"type": "done"})
                
            except Exception as e:
                await websocket.send_json({"type": "error", "text": f"Agent Error: {str(e)}"})
                
    except WebSocketDisconnect:
        print("Client disconnected")
