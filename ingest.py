"""Ingestion layer: load documents, clean them, and split them into chunks."""
import re
from pathlib import Path
from pypdf import PdfReader

CHUNK_SIZE = 500   # characters per chunk (about a paragraph)
OVERLAP = 100      # characters repeated between neighbouring chunks


def clean(text):
    """Remove messy spacing so the text is easier to search."""
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk(text, size=CHUNK_SIZE, overlap=OVERLAP):
    """Cut text into overlapping pieces."""
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start:start + size])
        start += size - overlap
    return chunks


def load_pages(path):
    """Return (page_number, text) pairs for a .txt or .pdf file."""
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(path)
        for number, page in enumerate(reader.pages, start=1):
            yield number, page.extract_text() or ""
    else:
        yield 1, path.read_text(encoding="utf-8")


def load_chunks(folder="documents"):
    """Read every file in the folder and return its chunks with metadata."""
    records = []
    for path in sorted(Path(folder).iterdir()):
        if path.suffix.lower() not in {".txt", ".pdf"}:
            continue
        for page, text in load_pages(path):
            for i, piece in enumerate(chunk(clean(text))):
                records.append({
                    "id": f"{path.name}-p{page}-{i}",
                    "text": piece,
                    "source": path.name,
                    "page": page,
                })
    return records


if __name__ == "__main__":
    records = load_chunks()
    print(f"{len(records)} chunks loaded")
    for r in records[:3]:
        print(r["id"], "|", r["text"][:80])