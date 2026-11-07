"""Chroma vector store with multilingual-e5 embeddings.

e5 models expect "query: " / "passage: " prefixes, so we embed ourselves instead of using
Chroma's built-in embedding function.
"""
from functools import lru_cache

import chromadb
from sentence_transformers import SentenceTransformer

from rag import config
from rag.domain.entities import Chunk


@lru_cache(maxsize=1)
def _model():
    return SentenceTransformer(config.EMBED_MODEL)


@lru_cache(maxsize=1)
def _client():
    return chromadb.PersistentClient(path=str(config.CHROMA_DIR))


def _prefix(kind):
    return f"{kind}: " if "e5" in config.EMBED_MODEL else ""


def embed(texts, kind):
    vectors = _model().encode([_prefix(kind) + t for t in texts], batch_size=32,
                              normalize_embeddings=True, show_progress_bar=False)
    return vectors.tolist()


def collection():
    return _client().get_or_create_collection(config.COLLECTION, metadata={"hnsw:space": "cosine"})


def reset():
    try:
        _client().delete_collection(config.COLLECTION)
    except Exception:
        pass
    return collection()


def add(chunks, batch=256):
    col = collection()
    for i in range(0, len(chunks), batch):
        part = chunks[i:i + batch]
        col.add(ids=[c.id for c in part], documents=[c.text for c in part],
                metadatas=[c.metadata() for c in part], embeddings=embed([c.text for c in part], "passage"))


def count():
    return collection().count()


def all_chunks():
    data = collection().get()
    return [Chunk(id=i, text=d, **m) for i, d, m in zip(data["ids"], data["documents"], data["metadatas"])]


def search(queries, n):
    """Search several phrasings at once. Returns {chunk_id: (Chunk, best_distance)}."""
    col = collection()
    n = min(n, col.count())
    if n == 0:
        return {}
    res = col.query(query_embeddings=embed(queries, "query"), n_results=n)
    found = {}
    for ids, docs, metas, dists in zip(res["ids"], res["documents"], res["metadatas"], res["distances"]):
        for i, d, m, dist in zip(ids, docs, metas, dists):
            if i not in found or dist < found[i][1]:
                found[i] = (Chunk(id=i, text=d, **m), dist)
    return found
