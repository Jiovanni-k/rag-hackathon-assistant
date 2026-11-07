"""Group blocks into chunks that never cross a section boundary.

Every chunk starts with a context header "title | section", so even a short chunk tells the
search engine (and the LLM) which document, university and section it belongs to.
"""
import re

from rag.domain.entities import Chunk

SENTENCE_END = re.compile(r"(?<=[.!؟?。])\s+")


def _split_long(text, size):
    """Split one oversized block at sentence ends, falling back to hard cuts."""
    parts, current = [], ""
    for sentence in SENTENCE_END.split(text):
        while len(sentence) > size:
            parts.append(sentence[:size])
            sentence = sentence[size:]
        if len(current) + len(sentence) + 1 > size and current:
            parts.append(current)
            current = ""
        current = f"{current} {sentence}".strip()
    if current:
        parts.append(current)
    return parts


def make_chunks(source, title, blocks, size):
    chunks, buf, buf_page, buf_section = [], [], 0, None

    def flush():
        if buf:
            header = f"{title} | {buf_section}" if buf_section else title
            n = len(chunks)
            chunks.append(Chunk(
                id=f"{source}-{n}", text=f"{header}\n" + "\n".join(buf),
                source=source, title=title, section=buf_section or "", page=buf_page,
            ))

    for block in blocks:
        pieces = _split_long(block.text, size) if len(block.text) > size else [block.text]
        for piece in pieces:
            new_section = block.section != buf_section
            too_big = sum(len(b) + 1 for b in buf) + len(piece) > size
            if buf and (new_section or too_big):
                flush()
                buf = []
            if not buf:
                buf_page, buf_section = block.page, block.section
            buf.append(piece)
    flush()
    return chunks
