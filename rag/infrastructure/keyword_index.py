"""BM25 keyword search: catches exact course codes, numbers and names that embeddings blur."""
from rank_bm25 import BM25Okapi

from rag.infrastructure import vector_store
from rag.infrastructure.arabic import tokenize

_index = None   # (BM25Okapi, [Chunk])


def invalidate():
    global _index
    _index = None


def _load():
    global _index
    if _index is None:
        chunks = vector_store.all_chunks()
        _index = (BM25Okapi([tokenize(c.text) for c in chunks]) if chunks else None, chunks)
    return _index


def search(queries, n):
    """Returns {chunk_id: Chunk} for the top n of each query."""
    bm25, chunks = _load()
    found = {}
    if bm25 is None:
        return found
    for q in queries:
        tokens = tokenize(q)
        if not tokens:
            continue
        scores = bm25.get_scores(tokens)
        top = sorted(range(len(chunks)), key=lambda i: scores[i], reverse=True)[:n]
        for i in top:
            if scores[i] > 0:
                found.setdefault(chunks[i].id, chunks[i])
    return found
