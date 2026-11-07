"""Read documents into "blocks": one block per paragraph line or table row, with page and section.

PDF  -> PyMuPDF (keeps Arabic word order much better than pypdf). Tables are detected and
        turned into one line per row ("header: value، header: value"), so a row is never split.
TXT  -> lines; "# " is the document title, "## " starts a new section.
"""
import json
import re
from dataclasses import dataclass
from pathlib import Path

import pymupdf

from rag.infrastructure.arabic import clean_text

SUPPORTED = {".pdf", ".txt"}

# Running page header in the catalog, e.g. "20    ACADEMIC REGULATIONS" or "ACADEMIC REGULATIONS   21"
RUNNING_HEADER = re.compile(r"^(?:\d{1,3}\s+([A-Z][A-Z &,\-]{3,})|([A-Z][A-Z &,\-]{3,}?)\s+\d{1,3})$")
HEADING_PATTERNS = [
    re.compile(r"^\d{1,2}\.\s+[A-Z][A-Z0-9 ,&/\-()'’]{3,70}$"),          # 3. DEGREE REQUIREMENTS
    re.compile(r"^(المادة|مادة)\s*[\(\[]?\s*\d+\s*[\)\]]?"),             # المادة (14)
    re.compile(r"^[A-Z][A-Z0-9 ,&/\-()'’]{4,60}$"),                        # STUDENT REGULATIONS
    re.compile(r"^(الفصل|الباب|القسم)\s+(ال)?\S+\s*[:：]?\s*\S*.{0,50}$"),  # الفصل الثالث: ...
]
TOC_LINE = re.compile(r"\.{5,}")       # "Orientation ........ 14"


@dataclass
class Block:
    text: str
    page: int
    section: str


def is_heading(line):
    return len(line) <= 90 and any(p.match(line) for p in HEADING_PATTERNS)


def load_metadata(folder):
    """Optional documents/metadata.json: {"file.pdf": {"title": "..."}}."""
    path = Path(folder) / "metadata.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def default_title(path):
    return path.stem.replace("_", " ")


# ---------- PDF ----------

def _table_lines(table):
    rows = [[clean_text(c or "").replace("\n", " ") for c in row] for row in table.extract()]
    rows = [r for r in rows if any(r)]
    if len(rows) < 2:
        return [" | ".join(r) for r in rows]
    header = rows[0]
    has_header = all(h and not h.replace(".", "").isdigit() for h in header)
    lines = []
    for row in rows[1:] if has_header else rows:
        if has_header:
            pairs = [f"{h}: {v}" for h, v in zip(header, row) if v]
            lines.append("، ".join(pairs))
        else:
            lines.append(" | ".join(v for v in row if v))
    return [l for l in lines if l]


def _inside(rect, boxes):
    cx, cy = (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2
    return any(b.x0 <= cx <= b.x1 and b.y0 <= cy <= b.y1 for b in boxes)


def load_pdf(path):
    blocks, chapter, section = [], "", ""
    with pymupdf.open(path) as doc:
        for page_no, page in enumerate(doc, start=1):
            tables = []
            if page.get_drawings():          # table detection is slow; only pages with ruled lines
                try:
                    tables = page.find_tables().tables
                except Exception:
                    tables = []
            boxes = [pymupdf.Rect(t.bbox) for t in tables]

            lines = []
            for b in page.get_text("blocks", sort=True):
                if b[6] != 0 or _inside(b[:4], boxes):       # skip images and table areas
                    continue
                lines += [clean_text(l) for l in b[4].splitlines()]
            lines = [l for l in lines if l and not TOC_LINE.search(l)]
            # A number alone on the first/last line is a page number. Elsewhere it is usually the
            # value column of a borderless table ("... in Accounting" / "128"), so join it upward.
            if lines and lines[0].isdigit():
                lines = lines[1:]
            if lines and lines[-1].isdigit():
                lines = lines[:-1]
            merged = []
            for line in lines:
                if merged and re.fullmatch(r"[\d.,%()\-– ]{1,12}", line) and not is_heading(merged[-1]):
                    merged[-1] += f" {line}"
                else:
                    merged.append(line)
            lines = merged

            for line in lines:
                m = RUNNING_HEADER.match(line)
                if m:                                          # chapter name from the page header
                    new_chapter = (m.group(1) or m.group(2)).strip()
                    if new_chapter != chapter:
                        chapter, section = new_chapter, ""
                    continue
                if is_heading(line):
                    section = line
                    continue
                label = " — ".join(x for x in (chapter, section) if x)
                blocks.append(Block(line, page_no, label))
            label = " — ".join(x for x in (chapter, section) if x)
            for t in tables:
                blocks += [Block(l, page_no, label) for l in _table_lines(t)]
    return blocks


# ---------- TXT ----------

def load_txt(path):
    blocks, title, section = [], None, ""
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        if raw.startswith("# "):
            title = clean_text(raw[2:])
            continue
        if raw.startswith("## "):
            section = clean_text(raw[3:])
            continue
        if raw.startswith(("المصدر:", "تاريخ الجلب:")):
            continue
        line = clean_text(raw)
        if raw.startswith((" ", "\t")) and blocks:     # continuation (e.g. a course description)
            blocks[-1].text += "\n" + line
        else:
            blocks.append(Block(line, 0, section))
    return blocks, title


def load_document(path, metadata=None):
    """Return (title, blocks) for one file."""
    path = Path(path)
    meta = (metadata or {}).get(path.name, {})
    if path.suffix.lower() == ".pdf":
        blocks, title = load_pdf(path), None
    else:
        blocks, title = load_txt(path)
    return meta.get("title") or title or default_title(path), blocks
