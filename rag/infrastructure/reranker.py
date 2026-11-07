"""Cross-encoder reranker: reads question and chunk together, much more precise than vectors."""
from functools import lru_cache

from sentence_transformers import CrossEncoder

from rag import config


@lru_cache(maxsize=1)
def _model():
    return CrossEncoder(config.RERANK_MODEL, max_length=config.RERANK_MAX_LENGTH)


def score(queries, chunks):
    """Best score of each chunk over all query phrasings (Arabic and English)."""
    if not chunks:
        return []
    pairs = [(q, c.text) for c in chunks for q in queries]
    raw = _model().predict(pairs, batch_size=32, show_progress_bar=False)
    k = len(queries)
    return [float(max(raw[i * k:(i + 1) * k])) for i in range(len(chunks))]
