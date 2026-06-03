# Portfolio Analyse Dashboard 📈

Ein modernes, interaktives Dashboard zur Analyse und Überwachung deines Investment-Portfolios. Gebaut mit [Streamlit](https://streamlit.io/), bietet diese Anwendung Echtzeit-Kursdaten, historische Performance-Analysen und KI-gestützte Einblicke in deine Anlagen.

## Features ✨

- **Live-Kursdaten:** Automatische Aktualisierung der Portfolio-Werte mittels `yfinance` und Financial Modeling Prep API.
- **Interaktive Visualisierungen:** Detaillierte Graphen zur Asset-Allokation und historischen Performance (bis zu 10 Jahre).
- **KI-Finanzberater:** Integrierter KI-Assistent (unterstützt Google Gemini, Anthropic Claude und lokale Modelle), der dein Portfolio auf Klumpenrisiken analysiert und kontextbezogene Handlungsempfehlungen basierend auf aktuellen Marktdaten gibt. (Inklusive Performance-Optimierungen wie Prompt Caching für Claude und einer vereinheitlichten Gemini-Pipeline).
- **PDF-Export:** Generiere umfassende Berichte deines Portfolios inklusive Visualisierungen und KI-Zusammenfassungen als PDF (dank `reportlab` nun noch robuster und mit breiterem Font-Support).
- **Docker Ready:** Einfache Bereitstellung und Ausführung in einer isolierten Container-Umgebung.

## Technologien 🛠️

- **Frontend / Framework:** Streamlit
- **Datenverarbeitung:** Pandas, NumPy
- **Visualisierung:** Plotly Express
- **Finanzdaten:** yfinance, Financial Modeling Prep (optional)
- **KI-Integration:** google-genai, Anthropic API, lokale Modelle via OpenAI-kompatibler API
- **Web-Suche / Marktdaten:** DuckDuckGo Search (`ddgs`)
- **PDF-Generierung:** reportlab, markdown

## Installation & Ausführung 🚀

Die einfachste Methode, das Dashboard zu starten, ist über Docker.

### Umgebungsvariablen (.env)

Bevor du die Anwendung startest (egal ob mit Docker oder lokal), solltest du eine `.env` Datei im Hauptverzeichnis anlegen, um deine API-Schlüssel sicher zu hinterlegen. Wenn diese Datei existiert, werden die Schlüssel automatisch in der Seitenleiste der App vorausgefüllt.

Erstelle dazu eine Datei namens `.env` (oder kopiere eine existierende `.env.example`) mit folgendem Aufbau:

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

### Voraussetzungen
- [Docker](https://docs.docker.com/get-docker/) und [Docker Compose](https://docs.docker.com/compose/install/) installiert.

### Setup mit Docker

1. **Repository klonen** (falls zutreffend) oder in das Projektverzeichnis wechseln.
2. **Container starten:**
   ```bash
   docker-compose up -d --build
   ```
3. **Dashboard öffnen:**
   Rufe `http://localhost:8501` in deinem Browser auf.

Das Verzeichnis ist als Volume in `docker-compose.yml` eingebunden, sodass Änderungen am Code (`app.py`) direkt übernommen werden, ohne den Container neu bauen zu müssen (Hot-Reloading).

### Lokales Setup (ohne Docker)

1. **Virtuelle Umgebung erstellen und aktivieren:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Auf Windows: .venv\Scripts\activate
   ```
2. **Abhängigkeiten installieren:**
   ```bash
   pip install -r requirements.txt
   ```
3. **App starten:**
   ```bash
   streamlit run app.py
   ```

## Nutzung 💡

1. **Daten hochladen:** Lade deine Bank-CSVs (z.B. Deka, Trade Republic) mit deinen Portfoliobeständen hoch.
2. **API Keys eintragen (optional):** Gib deine API-Schlüssel für Google Gemini, Anthropic oder Financial Modeling Prep in der Seitenleiste ein, um erweiterte Funktionen freizuschalten.
3. **Analysieren:** Betrachte die interaktiven Charts, überprüfe die aktuelle Marktlage und chatte mit dem KI-Berater über Optimierungspotenziale deines Portfolios.

## Lizenzen & Drittanbieter 📄

Dieses Projekt steht unter der [MIT-Lizenz](LICENSE.md).

Zusätzlich verwendet dieses Projekt Ressourcen von Drittanbietern:
- **Fonts:** Die in dieser Anwendung verwendeten Schriften (z.B. Google Fonts) unterliegen ihren jeweiligen Lizenzen (in der Regel die [SIL Open Font License](https://scripts.sil.org/OFL)).

## Hinweis / Disclaimer ⚠️
Dies ist ein Tool zur Analyse und Visualisierung. Der integrierte KI-Assistent simuliert einen Finanzberater, stellt jedoch **keine rechtliche oder bindende Anlageberatung** dar. Investitionen in Wertpapiere bergen Risiken. Alle Entscheidungen triffst du auf eigene Verantwortung.
