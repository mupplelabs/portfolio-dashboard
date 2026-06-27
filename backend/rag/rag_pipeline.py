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
            # Hole mehr als 3, da einige durch die Blacklist fliegen könnten
            raw_results = list(ddgs.text(query, max_results=10))
            
            # Blacklist laden
            blacklist = []
            try:
                with open("domain_blacklist.txt", "r") as f:
                    blacklist = [line.strip() for line in f if line.strip() and not line.startswith("#")]
            except FileNotFoundError:
                pass
                
            filtered = []
            for r in raw_results:
                url = r['href']
                if not any(bad_domain in url for bad_domain in blacklist):
                    filtered.append(r)
                    if len(filtered) == 3:
                        break
                        
            return filtered
            
    try:
        results = await asyncio.to_thread(do_search)
    except Exception as e:
        return f"Fehler bei der DDG-Suche: {str(e)}"
        
    if not results:
        return "Deep Search: Keine Ergebnisse im Web gefunden."
        
    chunks = []
    sources = []
    
    import httpx
    
    chunks = []
    sources = []
    
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        for idx, r in enumerate(results):
            url = r['href']
            if status_callback:
                await status_callback(f"📄 Scraping ({idx+1}/{len(results)}): {url[:45]}...")
                
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    # Extraktion blockiert kurz den Eventloop, aber ist sehr schnell
                    text = trafilatura.extract(response.text)
                    if text:
                        site_chunks = [text[i:i+800] for i in range(0, len(text), 600)]
                        for c in site_chunks:
                            chunks.append(c)
                            sources.append(url)
            except Exception as e:
                print(f"RAG Scraping Fehler bei {url}: {e}")
                continue
    
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
            
            # Sortiere Indices nach Re-Ranker Score (schlechtester zuerst, bester am Ende)
            best_local_idx = np.argsort(rerank_scores)
            return [top_k_idx[i] for i in best_local_idx]
            
        try:
            final_top_idx_all = await asyncio.to_thread(apply_reranker)
        except Exception as e:
            return f"Fehler beim Re-Ranking: {str(e)}"
    else:
        # Ohne Re-Ranker: Behalte die volle Liste der Vektorsuche (ist bereits sortiert nach Score, am Ende sind die besten)
        final_top_idx_all = final_top_idx
        
    # === URL Deduplizierung (Max 1 Chunk pro URL) ===
    deduped_top_idx = []
    seen_urls = set()
    # final_top_idx_all hat den schlechtesten Score zuerst und den besten am Ende
    for idx in reversed(final_top_idx_all):
        url = sources[idx]
        if url not in seen_urls:
            seen_urls.add(url)
            deduped_top_idx.append(idx)
            if len(deduped_top_idx) == 4: # Wir wollen die besten 4
                break
                
    # Da wir in umgekehrter Reihenfolge iteriert haben (best first), ist die Liste jetzt "best first".
    # Wir iterieren unten nochmal drüber, also behalten wir es so.
    final_top_idx = deduped_top_idx
        
    if status_callback:
        await status_callback(f"✅ RAG-Kontext erfolgreich zusammengestellt.")
        
    # Kontext zusammenbauen (bestes Ergebnis zuerst)
    context = ""
    for rank, idx in enumerate(final_top_idx):
        context += f"\n[Quelle {rank+1} - {sources[idx]}]:\n{chunks[idx]}\n"
        
    return context
