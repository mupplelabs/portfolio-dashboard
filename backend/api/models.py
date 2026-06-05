import httpx
from fastapi import APIRouter, HTTPException

router = APIRouter()

# Wir kapseln die Aufrufe in saubere Funktionen, damit sie bei API-Änderungen leicht wartbar sind.
async def fetch_google_models(api_key: str):
    if not api_key:
        return ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-pro", "gemini-1.5-flash"]
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, timeout=5.0)
            if resp.status_code == 200:
                data = resp.json()
                models = [m["name"].replace("models/", "") for m in data.get("models", []) if "generateContent" in m.get("supportedGenerationMethods", [])]
                return models if models else ["gemini-2.5-flash", "gemini-2.5-pro"]
            else:
                return ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-pro"]
        except Exception:
            return ["gemini-2.5-flash", "gemini-2.5-pro"]

async def fetch_anthropic_models(api_key: str):
    if not api_key:
        return ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"]
        
    url = "https://api.anthropic.com/v1/models"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01"
    }
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, headers=headers, timeout=5.0)
            if resp.status_code == 200:
                data = resp.json()
                return [m["id"] for m in data.get("data", [])]
            else:
                return ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"]
        except Exception:
            return ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"]

async def fetch_local_models(base_url: str, api_key: str):
    if not base_url:
        return []
    
    # Entferne evtl. trailing slashes
    base_url = base_url.rstrip('/')
    url = f"{base_url}/models"
    
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, headers=headers, timeout=3.0)
            if resp.status_code == 200:
                data = resp.json()
                return [m["id"] for m in data.get("data", [])]
            else:
                return []
        except Exception:
            return []

@router.get("")
@router.get("/")
async def get_models(provider: str, api_key: str = "", base_url: str = ""):
    try:
        if provider == "Google Gemini":
            models = await fetch_google_models(api_key)
            return {"models": models}
        elif provider == "Anthropic Claude":
            models = await fetch_anthropic_models(api_key)
            return {"models": models}
        elif provider == "OpenAI / Local":
            models = await fetch_local_models(base_url, api_key)
            return {"models": models}
        else:
            raise HTTPException(status_code=400, detail="Unknown provider")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
