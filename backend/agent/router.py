import os
try:
    from semantic_router import Route
    from semantic_router.layer import RouteLayer
    from semantic_router.encoders import HuggingFaceEncoder
except ImportError as e:
    import traceback
    print(f"WARNING: semantic_router or sentence_transformers missing. Using fallback regex router. Error details: {e}")
    traceback.print_exc()
    def analyze_intent(user_input: str) -> str:
        """
        Fallback-Router basierend auf simplen Keywords, falls RAG-Module nicht installiert sind.
        """
        text = user_input.lower()
        research_keywords = ["news", "markt", "zinsen", "inflation", "wirtschaft", "berater"]
        if any(kw in text for kw in research_keywords):
            return "research_needed"
        return "portfolio_only"
else :
    # 1. Definiere den Encoder (gleiches lokales Modell wie im RAG, damit es gecached ist)
    # Wir nutzen paraphrase-multilingual-MiniLM-L12-v2 für deutsche Sprache!
    encoder = HuggingFaceEncoder(name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    research_route = Route(
    name="research_needed",
    utterances=[
        "Wie wirken sich die aktuellen Zinsen auf mein Portfolio aus?",
        "Was macht der Tech-Sektor gerade?",
        "Warum fällt der Goldpreis?",
        "Gibt es News zu Apple?",
        "Sollte ich Nvidia jetzt kaufen angesichts der Nachrichten?",
        "Wie ist die aktuelle Marktlage?",
        "Erzähl mir was über die Inflation",
        "Was sagt die EZB?",
        "Such mal nach aktuellen Börsennews",
        "Bitte analysiere mein Portfolio als Finanzberater und beziehe explizit Marktsituation und News ein.",
        "Analysiere meine Klumpenrisiken und gib konkrete Handlungsempfehlungen unter Berücksichtigung der neuesten Nachrichten.",
        "Bewerte meine Diversifikation angesichts der aktuellen Marktlage und makroökonomischen Trends.",
        "Schau dir mein Portfolio an, ruf die Daten ab und mache dann einen Abgleich mit den aktuellen Wirtschafts-News.",
        "Bitte analysiere mein Portfolio als Finanzberater. Rufe dafür zunächst zwingend deine Portfolio-Tools auf. Beziehe explizit Marktsituation und News ein.",
        "Bitte analysiere mein Portfolio als Finanzberater. Rufe dafür zunächst zwingend deine Portfolio-Tools auf (z.B. get_portfolio_overview, get_sector_allocation, get_top_positions), um dir einen Überblick zu verschaffen. Identifiziere danach Klumpenrisiken, fehlende Diversifikation und gib konkrete Handlungsempfehlungen. Beziehe explizit Marktsituation und News ein."
    ]
    )

    portfolio_route = Route(
    name="portfolio_only",
    utterances=[
        "Wie viele Apple Aktien habe ich?",
        "Zeig mir meine Top 5 Positionen",
        "Bin ich im Minus?",
        "Wie hoch ist mein Gesamtwert?",
        "Was ist meine größte Position?",
        "Welche Sektoren habe ich im Portfolio?",
        "Wie viel Cash habe ich noch?",
        "Hast du mein Portfolio analysiert?"
    ]
    )

    # 3. Erstelle den RouteLayer
    route_layer = RouteLayer(encoder=encoder, routes=[research_route, portfolio_route])

    def analyze_intent(user_input: str) -> str:
        """
        Nimmt den Nutzer-Input und gibt den Namen der Route zurück.
        Gibt None zurück, wenn keine Route passt (Fallback).
        """
        route = route_layer(user_input)
        return route.name if route else None