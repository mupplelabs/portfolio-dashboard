from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from dotenv import load_dotenv
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Lade die .env Datei aus dem Root-Verzeichnis (ein Ordner über 'backend')
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

from contextlib import asynccontextmanager

import database
import token_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize databases
    database.init_db()
    token_db.init_db()
    yield
    # Shutdown logic can go here if needed

app = FastAPI(
    title="Portfolio Analyse API",
    description="Backend API for the Portfolio Analysis Dashboard",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration - allowing the Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

@app.get("/api/config")
def get_config():
    return {
        "has_google_key": bool(os.environ.get("GOOGLE_API_KEY")),
        "has_anthropic_key": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "has_local_key": bool(os.environ.get("LOCAL_LLM_KEY")),
        "local_llm_url": os.environ.get("LOCAL_LLM_URL", "")
    }

# We will mount routers here later
from api.portfolio import router as portfolio_router
from api.chat import router as chat_router
from api.models import router as models_router
from api.settings import router as settings_router

app.include_router(portfolio_router, prefix="/api/portfolio")
app.include_router(models_router, prefix="/api/models")
app.include_router(settings_router, prefix="/api/settings")
app.include_router(chat_router) # WebSockets don't strictly need an api prefix if they define it

# --- Frontend Serving ---
# Serve static frontend files from the 'static' directory if it exists
frontend_dist = Path(__file__).resolve().parent / "static"
if frontend_dist.exists():
    # Mount the assets directory (js, css, images) directly
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")
    
    # Catch-all route to serve the SPA (Single Page Application)
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        if full_path.startswith("api/"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="API route not found")
            
        path = frontend_dist / full_path
        if path.is_file():
            return FileResponse(path)
        # Fallback to index.html for client-side routing
        return FileResponse(frontend_dist / "index.html")

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
