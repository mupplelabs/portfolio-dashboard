# InvestIQ 📈

Ein modernes, interaktives Dashboard zur Analyse und Überwachung deines Investment-Portfolios. InvestIQ kombiniert eine blitzschnelle Vue.js-Oberfläche mit einem leistungsstarken FastAPI-Backend und bietet Echtzeit-Kursdaten, historische Performance-Analysen und KI-gestützte Einblicke in deine Anlagen.

## Features ✨

- **Live-Kursdaten:** Automatische Aktualisierung der Portfolio-Werte mittels `yfinance` und Financial Modeling Prep API.
- **Interaktive Visualisierungen:** Detaillierte Graphen zur Asset-Allokation und historischen Performance.
- **Portfolio Navigator (KI):** Ein integrierter KI-Berater (unterstützt Google Gemini, Anthropic Claude und lokale LLMs), der dein Portfolio auf Klumpenrisiken analysiert und kontextbezogene Handlungsempfehlungen liefert.
- **Single-Container Deployment:** Dank Multi-Stage Docker-Build lässt sich die gesamte Applikation (Frontend & Backend) extrem einfach auf Servern (z.B. Synology NAS) hosten.
- **PDF-Export:** Generiere umfassende Berichte deines Portfolios inklusive Visualisierungen und KI-Zusammenfassungen.

## Technologien 🛠️

- **Frontend:** Vue.js 3, Vite, Plotly.js (Charts)
- **Backend:** Python, FastAPI, Uvicorn
- **Datenverarbeitung:** Pandas, NumPy
- **Finanzdaten:** yfinance, Financial Modeling Prep (optional)
- **KI-Integration:** PydanticAI (Google Gemini, Anthropic Claude, OpenAI-kompatible lokale Modelle via LM Studio/Ollama)
- **Web-Suche:** DuckDuckGo Search (`ddgs`)

## Installation & Ausführung 🚀

Die einfachste Methode, InvestIQ zu betreiben, ist über Docker.

### Umgebungsvariablen (.env)

Erstelle im Hauptverzeichnis eine Datei namens `.env`. Diese wird sowohl von Docker als auch bei der lokalen Ausführung eingelesen.

```env
# Google Gemini API Key
GEMINI_API_KEY=dein_gemini_api_key_hier

# Anthropic Claude API Key
CLAUDE_API_KEY=dein_claude_api_key_hier

# URL für ein lokales LLM (z.B. LM Studio, Ollama)
LOCAL_LLM_URL=http://192.168.178.39:1234/v1

# API Key für lokales LLM (falls benötigt)
LOCAL_LLM_KEY=dein_lokaler_key_hier

# Financial Modeling Prep API Key (für Aktien-Live-Kurse)
FMP_API_KEY=dein_fmp_api_key_hier
```

### Setup mit Docker (Empfohlen für Server/NAS)

Das bereitgestellte Docker-Setup kompiliert automatisch das Vue-Frontend und serviert es über das FastAPI-Backend. Alles läuft in **einem einzigen Container**.

1. **Repository klonen** oder in das Projektverzeichnis wechseln.
2. **Container starten:**
   ```bash
   docker-compose up -d --build
   ```
3. **App öffnen:**
   Rufe `http://localhost:8080` in deinem Browser auf.
   *(Hinweis: Das Backend im Container lauscht auf Port 8000. In der `docker-compose.yml` wird dieser standardmäßig auf Port 8080 nach außen freigegeben. Das kann dort beliebig geändert werden.)*

### Lokales Setup (Für Entwicklung)

Für die Entwicklung ist es sinnvoll, Frontend und Backend getrennt laufen zu lassen, um Hot-Reloading zu nutzen.

**1. Backend (FastAPI)**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Auf Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```
*Das Backend läuft nun auf http://localhost:8000.*

**2. Frontend (Vue.js)**
Öffne ein neues Terminal:
```bash
cd frontend
npm install
npm run dev
```
*Das Frontend läuft nun auf http://localhost:5173 und leitet API-Anfragen automatisch an Port 8000 weiter.*

## Lizenzen & Drittanbieter 📄

Dieses Projekt steht unter der [MIT-Lizenz](LICENSE.md).

Zusätzlich verwendet dieses Projekt Ressourcen von Drittanbietern:
- **Fonts:** Die in dieser Anwendung verwendeten Schriften (z.B. Google Fonts) unterliegen ihren jeweiligen Lizenzen (in der Regel die [SIL Open Font License](https://scripts.sil.org/OFL)).

## Hinweis / Disclaimer ⚠️
Dies ist ein Tool zur Analyse und Visualisierung. Der integrierte KI-Assistent simuliert einen Finanzberater, stellt jedoch **keine rechtliche oder bindende Anlageberatung** dar. Investitionen in Wertpapiere bergen Risiken. Alle Entscheidungen triffst du auf eigene Verantwortung.
