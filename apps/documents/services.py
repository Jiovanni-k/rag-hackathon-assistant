"""Application layer for documents: keeps the database and the RAG index in sync.

Indexing runs in a background thread so uploads return immediately (202) and the frontend polls.
"""
import logging
import threading
from pathlib import Path

from django.db import close_old_connections

from rag import config
from rag.application import ingest_service
from rag.infrastructure import vector_store
from rag.infrastructure.loaders import SUPPORTED

from .models import Document

log = logging.getLogger("apps")
_reindex_lock = threading.Lock()


def documents_dir():
    config.DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    return config.DOCUMENTS_DIR


def index_title(doc):
    """Title stored with every chunk; the year lets the LLM prefer the newest version."""
    if doc.title == doc.filename:
        return None                     # let the file's own title (e.g. "# ..." in .txt) win
    return f"{doc.title} ({doc.version_year})" if doc.version_year else doc.title


def _index_one(doc_id):
    close_old_connections()
    doc = Document.objects.get(pk=doc_id)
    try:
        chunks, pages = ingest_service.index_file(documents_dir() / doc.filename, index_title(doc))
        doc.status, doc.chunk_count, doc.pages, doc.error = Document.Status.READY, chunks, pages, None
    except Exception as e:                       # report any parsing problem to the admin
        log.exception("Indexing failed for %s", doc.filename)
        doc.status, doc.error = Document.Status.FAILED, str(e)[:1000]
    doc.save()
    close_old_connections()


def start_indexing(doc, background=True):
    if background:
        threading.Thread(target=_index_one, args=(doc.pk,), daemon=True).start()
    else:
        _index_one(doc.pk)


def delete_document(doc):
    ingest_service.remove_file(doc.filename)
    path = documents_dir() / doc.filename
    if path.exists():
        path.unlink()
    doc.delete()


def sync_from_folder():
    """Register files already in the documents folder (e.g. copied by hand) in the database."""
    known = set(Document.objects.values_list("filename", flat=True))
    created = 0
    for path in sorted(documents_dir().iterdir()):
        if path.suffix.lower() in SUPPORTED and path.name not in known:
            Document.objects.create(title=path.name, filename=path.name, status=Document.Status.READY,
                                    chunk_count=vector_store.count(path.name))
            created += 1
    return created


def is_reindexing():
    return _reindex_lock.locked()


def _reindex():
    with _reindex_lock:
        close_old_connections()
        try:
            sync_from_folder()
            Document.objects.update(status=Document.Status.PROCESSING)
            ingest_service.build_index()
            for doc in Document.objects.all():
                n = vector_store.count(doc.filename)
                doc.chunk_count = n
                doc.status = Document.Status.READY if n else Document.Status.FAILED
                doc.error = None if n else "No text could be extracted from this file."
                doc.save()
        except Exception as e:
            log.exception("Re-index failed")
            Document.objects.update(status=Document.Status.FAILED, error=str(e)[:1000])
        finally:
            close_old_connections()


def start_reindex(background=True):
    """Returns False if a re-index is already running."""
    if is_reindexing():
        return False
    if background:
        threading.Thread(target=_reindex, daemon=True).start()
    else:
        _reindex()
    return True


def safe_filename(name):
    """Keep letters (incl. Arabic), digits, dot, dash, underscore; no path parts."""
    name = Path(name).name.replace(" ", "_")
    return "".join(ch for ch in name if ch.isalnum() or ch in "._-") or "document"
