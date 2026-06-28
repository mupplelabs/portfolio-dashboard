from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import get_db_connection
from security import encrypt_api_key, decrypt_api_key

router = APIRouter()

class SettingsUpdate(BaseModel):
    settings: dict[str, str]

@router.get("/")
def get_settings():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM settings")
            rows = cursor.fetchall()
            
            settings_dict = {}
            for row in rows:
                key = row['key']
                val = row['value']
                # Mask API keys for frontend, but keep providers/models visible
                if "api_key" in key.lower() and val:
                    # Provide a masked version to indicate it exists
                    settings_dict[key] = "sk-***" if "sk-" in val or decrypt_api_key(val).startswith("sk-") else "AIza***" if "AIza" in val or decrypt_api_key(val).startswith("AIza") else "***"
                else:
                    settings_dict[key] = val
                    
            return settings_dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/")
def update_settings(payload: SettingsUpdate):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            for key, value in payload.settings.items():
                # If the frontend sends back a masked key, we ignore it and keep the existing one in DB
                if value in ["sk-***", "AIza***", "***"]:
                    continue
                    
                # Encrypt API keys before storing
                if "api_key" in key.lower() and value:
                    value = encrypt_api_key(value)
                    
                cursor.execute(
                    "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (key, value)
                )
            conn.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def get_api_key_for_provider(provider_name: str) -> str:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        key_name = ""
        if provider_name == "Google Gemini":
            key_name = "google_api_key"
        elif provider_name == "Anthropic Claude":
            key_name = "anthropic_api_key"
        elif provider_name == "OpenAI / Local":
            key_name = "openai_api_key"
            
        if not key_name:
            return ""
            
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key_name,))
        row = cursor.fetchone()
        if row and row["value"]:
            return decrypt_api_key(row["value"])
        return ""

def get_setting(key: str) -> str:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else ""
