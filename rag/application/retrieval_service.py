"""Use case: find the best chunks for a question.

1. Vector search with every phrasing (Arabic standalone + English translation)
2. BM25 keyword search with every phrasing, merged in (hybrid)
3. Cross-encoder rerank, keep the top k
The best vector distance is returned too, so the caller can refuse when nothing is close.
"""
from rag import config
from rag.domain.entities import Hit
from rag.infrastructure import keyword_index, reranker, vector_store


def retrieve(queries, k=None):
    queries = [q for q in dict.fromkeys(queries) if q and q.strip()]
    k = k or config.TOP_K
    vec = vector_store.search(queries, config.CANDIDATES)
    if not vec:
        return [], 1.0
    best_distance = min(d for _, d in vec.values())

    candidates = {cid: Hit(chunk, distance=d) for cid, (chunk, d) in vec.items()}
    for cid, chunk in keyword_index.search(queries, config.CANDIDATES).items():
        candidates.setdefault(cid, Hit(chunk))

    hits = list(candidates.values())
    # Rerank with the first two phrasings only (Arabic standalone + English): the cross-encoder
    # is the slowest step on CPU, and a third phrasing adds cost but little accuracy.
    for hit, s in zip(hits, reranker.score(queries[:2], [h.chunk for h in hits])):
        hit.score = s
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:k], best_distance
