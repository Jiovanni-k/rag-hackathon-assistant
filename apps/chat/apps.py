import logging
import os
import sys
import threading

from django.apps import AppConfig

log = logging.getLogger("apps")


def _warm_up():
    """Load the embedding + reranker models and the BM25 index once, so the first real
    question is not slowed down by ~30 s of model loading."""
    try:
        from rag.infrastructure import keyword_index, reranker, vector_store
        if vector_store.count():
            vector_store.search(["warm up"], 1)
            keyword_index.search(["warm up"], 1)
            reranker.score(["warm up"], vector_store.all_chunks()[:1])
        log.info("RAG models warmed up")
    except Exception:                       # never block the server because of warm-up
        log.exception("RAG warm-up failed")


def _is_server_process():
    argv = " ".join(sys.argv)
    if "runserver" in argv:                 # autoreloader: only the child (RUN_MAIN) serves requests
        return os.environ.get("RUN_MAIN") == "true" or "--noreload" in argv
    return "gunicorn" in argv


class ChatConfig(AppConfig):
    name = "apps.chat"
    label = "chat"

    def ready(self):
        if os.getenv("RAG_WARMUP", "true").lower() == "true" and _is_server_process():
            threading.Thread(target=_warm_up, daemon=True).start()
