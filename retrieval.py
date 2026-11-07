"""Retrieval layer: Arabic-friendly embeddings + hybrid search + reranking."""
import re
import chromadb
from chromadb.utils import embedding_functions
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder
from ingest import load_chunks

EMBED_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"         # supports Arabic
RERANK_MODEL = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"   # multilingual reranker
COLLECTION = "docs"
CANDIDATES = 10    # how many chunks each search collects before reranking
MAX_DIST = 0.7     # "close enough" circle; tune this with real questions

_client = chromadb.PersistentClient(path="chroma_db")
_embed = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)
_reranker = CrossEncoder(RERANK_MODEL)
_bm25, _corpus = None, None


def tokenize(text):
    """Split text into lowercase words (works for Arabic and English)."""
    return re.findall(r"\w+", text.lower())


def get_collection():
    return _client.get_or_create_collection(
        COLLECTION, embedding_function=_embed, metadata={"hnsw:space": "cosine"}
    )


def build_index(folder="documents"):
    """Delete the old index and store every chunk again."""
    global _bm25
    try:
        _client.delete_collection(COLLECTION)
    except Exception:
        pass
    col = get_collection()
    records = load_chunks(folder)
    col.add(
        ids=[r["id"] for r in records],
        documents=[r["text"] for r in records],
        metadatas=[{"source": r["source"], "page": r["page"]} for r in records],
    )
    _bm25 = None  # rebuild keyword index next time
    return len(records)


def keyword_search(question, n):
    """Classic keyword search (BM25): good for exact codes and names."""
    global _bm25, _corpus
    if _bm25 is None:
        data = get_collection().get()
        _corpus = [{"id": i, "text": d, **m}
                   for i, d, m in zip(data["ids"], data["documents"], data["metadatas"])]
        _bm25 = BM25Okapi([tokenize(c["text"]) for c in _corpus])
    scores = _bm25.get_scores(tokenize(question))
    ranked = sorted(zip(scores, _corpus), key=lambda x: x[0], reverse=True)
    return [c for s, c in ranked[:n] if s > 0]


def retrieve(question, k=3, debug=False):
    """Hybrid search + reranking. Returns [] when nothing is close enough."""
    col = get_collection()
    n = min(CANDIDATES, col.count())
    if n == 0:
        return []

    # 1. Meaning search (vector database)
    res = col.query(query_texts=[question], n_results=n)
    closest = min(res["distances"][0])
    if debug:
        print(f"  closest distance: {closest:.3f}")
    if closest > MAX_DIST:          # nothing inside the circle -> refuse
        return []

    candidates = {i: {"id": i, "text": d, **m}
                  for i, d, m in zip(res["ids"][0], res["documents"][0], res["metadatas"][0])}

    # 2. Keyword search, merged in (hybrid)
    for c in keyword_search(question, n):
        candidates.setdefault(c["id"], c)

    # 3. Rerank: score each chunk together with the question, keep the best k
    items = list(candidates.values())
    scores = _reranker.predict([(question, c["text"]) for c in items])
    for c, s in zip(items, scores):
        c["score"] = float(s)
    items.sort(key=lambda c: c["score"], reverse=True)
    return items[:k]


if __name__ == "__main__":
    print("Indexed", build_index(), "chunks")
    for q in ["How do I register for courses?", "كيف بسجل مواد؟", "Who won the 2022 World Cup?"]:
        print("\nQ:", q)
        hits = retrieve(q, debug=True)
        print("  ->", [(h["source"], h["page"]) for h in hits] or "I don't know")