"""All tunable settings in one place. Values can be overridden with environment variables."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _env(name, default, cast=str):
    value = os.getenv(name)
    return cast(value) if value not in (None, "") else default


DOCUMENTS_DIR = Path(_env("RAG_DOCUMENTS_DIR", str(ROOT / "documents")))
CHROMA_DIR = Path(_env("RAG_CHROMA_DIR", str(ROOT / "chroma_db")))
COLLECTION = _env("RAG_COLLECTION", "docs_v2")

# Models
EMBED_MODEL = _env("RAG_EMBED_MODEL", "intfloat/multilingual-e5-small")   # Arabic + English
RERANK_MODEL = _env("RAG_RERANK_MODEL", "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1")
LLM_MODELS = [m for m in [os.getenv("GEMINI_MODEL")] if m] + [
    "gemini-3.5-flash", "gemini-3.8-flash", "gemini-3.5-flash-lite"]
# Small, fast models for the query-rewrite step (classification + translation)
LLM_FAST_MODELS = ["gemini-3.5-flash-lite", "gemini-3.5-flash"]
RERANK_MAX_LENGTH = _env("RAG_RERANK_MAX_LENGTH", 384, int)   # tokens; shorter = faster on CPU
LLM_TIMEOUT_MS = _env("RAG_LLM_TIMEOUT_MS", 30_000, int)
LLM_COOLDOWN_S = _env("RAG_LLM_COOLDOWN_S", 300, int)   # skip an overloaded model this long

# Chunking
CHUNK_CHARS = _env("RAG_CHUNK_CHARS", 900, int)

# Retrieval
CANDIDATES = _env("RAG_CANDIDATES", 8, int)     # per query, per search method
TOP_K = _env("RAG_TOP_K", 6, int)               # chunks given to the LLM
# Cosine distance safety net: above this nothing relevant exists, so we refuse without calling
# the LLM. Calibrated on the eval set (in-scope max 0.150, not-in-docs 0.178); closer cases are
# refused by the LLM itself (NOT_FOUND rule in the prompt).
MAX_DIST = _env("RAG_MAX_DIST", 0.20, float)
HISTORY_TURNS = _env("RAG_HISTORY_TURNS", 4, int)
