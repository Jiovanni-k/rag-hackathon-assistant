"""Group blocks into chunks that never cross a section boundary.

Every chunk starts with a context header "title | section", so even a short chunk tells the
search engine (and the LLM) which document, university and section it belongs to.

A new chunk also starts:
- where a detected table begins or ends, so table rows and prose are embedded separately;
- at a numbered rule ("6. ...", "(6) ...") once the current chunk is fairly full, or when the
  chunk so far holds no numbered rule at all (e.g. the rows of a long program table), so a rule
  is never just the tail of a chunk about something else.

When a chunk continues a numbered list, the list's lead-in sentence (e.g. "To receive a degree a
student must complete:") is repeated after the header. Otherwise a chunk starting at rule 6
("A minimum of 60 credits at Bethlehem University") would not say what the rule is for.
"""
import re

from rag.domain.entities import Chunk

SENTENCE_END = re.compile(r"(?<=[.!؟?。])\s+")
NUMBERED_ITEM = re.compile(r"^\s*\(?(\d{1,2})[.)]\s")
ENDS_SENTENCE = re.compile(r"[.!?؟。:：]\s*$")
MIN_CHUNK_CHARS = 30       # smaller leftovers (e.g. a lone "First Year" or "CR") join the next chunk;
                           # a short but complete fact ("Total for graduation: 139 hours.") stays alone
ITEM_BREAK_FILL = 0.4     # start a new chunk at a numbered rule once the chunk is this full...
ITEM_BREAK_FILL_NO_RULES = 0.2   # ...or this full if the chunk has no numbered rule yet


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


def _lead_in(lines):
    """The sentence that introduces a list: the last lines before item 1, if they end with ':'."""
    if not lines or not lines[-1].rstrip().endswith((":", "：")):
        return None
    start = len(lines) - 1
    while start > 0 and len(lines) - start < 3 and not ENDS_SENTENCE.search(lines[start - 1]):
        start -= 1
    return " ".join(line.strip() for line in lines[start:])


def make_chunks(source, title, blocks, size):
    chunks, buf, buf_page, buf_section, buf_kind, buf_context = [], [], 0, None, None, None
    section, recent, lead_in = None, [], None   # lines since the last numbered item; current lead-in

    def flush():
        if buf:
            header = f"{title} | {buf_section}" if buf_section else title
            if buf_context:
                header += f"\n{buf_context} (…)"
            n = len(chunks)
            chunks.append(Chunk(
                id=f"{source}-{n}", text=f"{header}\n" + "\n".join(buf),
                source=source, title=title, section=buf_section or "", page=buf_page,
            ))

    for block in blocks:
        if block.section != section:
            section, recent, lead_in = block.section, [], None
        pieces = _split_long(block.text, size) if len(block.text) > size else [block.text]
        kind = block.kind
        for piece in pieces:
            item = NUMBERED_ITEM.match(piece)
            number = int(item.group(1)) if item else None
            if number == 1:
                lead_in = _lead_in(recent)

            filled = sum(len(b) + 1 for b in buf)
            new_section = block.section != buf_section
            new_kind = kind != buf_kind
            too_big = filled + len(piece) > size
            limit = ITEM_BREAK_FILL if any(NUMBERED_ITEM.match(b) for b in buf) else ITEM_BREAK_FILL_NO_RULES
            rule_starts = item is not None and filled > size * limit
            if buf and (too_big or (filled >= MIN_CHUNK_CHARS and (new_section or new_kind or rule_starts))):
                flush()
                buf = []
            elif buf and new_section:            # tiny leftover: carry it into the new section's chunk
                buf_section = block.section
            if not buf:
                buf_page, buf_section, buf_kind = block.page, block.section, kind
                buf_context = lead_in if number and number > 1 else None
            buf.append(piece)
            recent = [] if item else (recent + [piece])[-4:]
    flush()
    return chunks
