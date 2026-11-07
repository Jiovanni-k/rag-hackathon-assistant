"""Use case: (re)build the search index from the documents folder."""
from pathlib import Path

from rag import config
from rag.infrastructure import keyword_index, vector_store
from rag.infrastructure.chunker import make_chunks
from rag.infrastructure.loaders import SUPPORTED, load_document, load_metadata


def load_all_chunks(folder=None):
    folder = Path(folder or config.DOCUMENTS_DIR)
    metadata = load_metadata(folder)
    chunks, report = [], []
    for path in sorted(folder.iterdir()):
        if path.suffix.lower() not in SUPPORTED:
            continue
        title, blocks = load_document(path, metadata)
        doc_chunks = make_chunks(path.name, title, blocks, config.CHUNK_CHARS)
        chunks += doc_chunks
        report.append((path.name, len(doc_chunks)))
    return chunks, report


def index_file(path, title=None):
    """Add (or replace) one document in the index without rebuilding everything.
    Returns (chunk_count, page_count)."""
    path = Path(path)
    if path.suffix.lower() not in SUPPORTED:
        raise ValueError(f"Unsupported file type: {path.suffix}")
    metadata = load_metadata(path.parent)
    if title:
        metadata[path.name] = {**metadata.get(path.name, {}), "title": title}
    doc_title, blocks = load_document(path, metadata)
    chunks = make_chunks(path.name, doc_title, blocks, config.CHUNK_CHARS)
    vector_store.delete_source(path.name)
    vector_store.add(chunks)
    keyword_index.invalidate()
    pages = max((b.page for b in blocks), default=0)
    return len(chunks), pages


def remove_file(name):
    vector_store.delete_source(name)
    keyword_index.invalidate()


def build_index(folder=None, verbose=False):
    """Delete the old index and store every chunk again. Returns the number of chunks."""
    chunks, report = load_all_chunks(folder)
    vector_store.reset()
    vector_store.add(chunks)
    keyword_index.invalidate()
    if verbose:
        for name, n in report:
            print(f"  {n:5} chunks  {name}")
    return len(chunks)


if __name__ == "__main__":
    print("Indexed", build_index(verbose=True), "chunks")
