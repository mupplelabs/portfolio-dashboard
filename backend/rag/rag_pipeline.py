import asyncio
from typing import Callable, Awaitable, Optional

try:
    from sentence_transformers import SentenceTransformer, CrossEncoder
    import trafilatura
    import numpy as np
    from ddgs import DDGS
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False

# Lazy-loaded models
_bi_encoder = None
_reranker = None

def _get_bi_encoder():
    global _bi_encoder
    if _bi_encoder is None:
        _bi_encoder = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    return _bi_encoder

def _get_reranker():
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoder('BAAI/bge-reranker-base')
    return _reranker

async def run_rag_search(query: str, use_reranker: bool = False, status_callback: Optional[Callable[[str], Awaitable[None]]] = None) -> str:
    """
    Führt die RAG-Pipeline aus: Web Scrape -> Chunking -> Embedding -> (optional) Re-Ranker.
    Gibt die besten Text-Chunks als String formatiert zurück.
    """
    if not RAG_AVAILABLE:
        return "⚠️ Fehler: RAG-Abhängigkeiten fehlen. Bitte installiere requirements-rag.txt oder baue den Docker-Container mit INSTALL_RAG=true neu."
        
    if status_callback:
        await status_callback(f"🔎 Deep Search: Suche im Web nach '{query}'...")
        
    def do_search():
        with DDGS() as ddgs:
            # Hole Top 3 Links
            return list(ddgs.text(query, max_results=3))
            
    try:
        results = await asyncio.to_thread(do_search)
    except Exception as e:
        return f"Fehler bei der DDG-Suche: {str(e)}"
        
    if not results:
        return "Deep Search: Keine Ergebnisse im Web gefunden."
        
    chunks = []
    sources = []
    
    if status_callback:
        await status_callback(f"📄 Scraping von {len(results)} Webseiten...")
        
    def scrape_and_chunk():
        local_chunks = []
        local_sources = []
        for r in results:
            url = r['href']
            # Download und Extraktion
            html = trafilatura.fetch_url(url)
            if html:
                text = trafilatura.extract(html)
                if text:
                    # Chunking: 800 Zeichen Länge, 600 Zeichen Schrittweite (200 Z. Überlappung)
                    site_chunks = [text[i:i+800] for i in range(0, len(text), 600)]
                    for c in site_chunks:
                        local_chunks.append(c)
                        local_sources.append(url)
        return local_chunks, local_sources
        
    try:
        chunks, sources = await asyncio.to_thread(scrape_and_chunk)
    except Exception as e:
        return f"Fehler beim Scraping: {str(e)}"
    
    if not chunks:
        return "Deep Search: Konnte keine auswertbaren Texte von den Webseiten extrahieren (möglicherweise Bot-Schutz)."
        
    if status_callback:
        await status_callback(f"🧠 Analysiere {len(chunks)} Text-Abschnitte (Vektorsuche)...")
        
    def semantic_filter():
        bi_encoder = _get_bi_encoder()
        query_emb = bi_encoder.encode(query)
        chunk_embs = bi_encoder.encode(chunks)
        
        # Kosinusähnlichkeit berechnen
        norm_chunks = np.linalg.norm(chunk_embs, axis=1)
        norm_query = np.linalg.norm(query_emb)
        norm_chunks[norm_chunks == 0] = 1e-10
        norm_query = norm_query if norm_query != 0 else 1e-10
        
        scores = np.dot(chunk_embs, query_emb) / (norm_chunks * norm_query)
        
        # Top 15 (oder weniger)
        top_k = min(15, len(chunks))
        top_k_idx = np.argsort(scores)[-top_k:]
        return top_k_idx
        
    try:
        top_k_idx = await asyncio.to_thread(semantic_filter)
    except Exception as e:
        return f"Fehler bei der Vektorsuche: {str(e)}"
    
    final_top_idx = top_k_idx
    
    if use_reranker:
        if status_callback:
            await status_callback(f"🎯 Re-Ranking der besten {len(top_k_idx)} Treffer...")
            
        def apply_reranker():
            reranker = _get_reranker()
            pairs = [[query, chunks[i]] for i in top_k_idx]
            rerank_scores = reranker.predict(pairs)
            
            # Top 4 nach Re-Ranking
            top_final = min(4, len(top_k_idx))
            best_local_idx = np.argsort(rerank_scores)[-top_final:]
            return [top_k_idx[i] for i in best_local_idx]
            
        try:
            final_top_idx = await asyncio.to_thread(apply_reranker)
        except Exception as e:
            return f"Fehler beim Re-Ranking: {str(e)}"
    else:
        # Ohne Re-Ranker: Nimm einfach die besten 4 aus der Vektorsuche
        top_final = min(4, len(final_top_idx))
        final_top_idx = final_top_idx[-top_final:]
        
    if status_callback:
        await status_callback(f"✅ RAG-Kontext erfolgreich zusammengestellt.")
        
    # Kontext zusammenbauen (bestes Ergebnis zuerst)
    context = ""
    for rank, idx in enumerate(reversed(final_top_idx)):
        context += f"\n[Quelle {rank+1} - {sources[idx]}]:\n{chunks[idx]}\n"
        
    return context
