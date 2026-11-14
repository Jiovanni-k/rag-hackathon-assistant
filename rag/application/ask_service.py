"""Use case: answer a student's question (with optional conversation history)."""
import re

from rag import config
from rag.application import prompts
from rag.application.retrieval_service import retrieve
from rag.domain.entities import Answer, Source
from rag.infrastructure import llm

CITATION = re.compile(r"\[(\d+(?:\s*[,،]\s*\d+)*)\]")
SCOPES = {"academic", "greeting", "out_of_scope"}


def _text(value):
    return value.strip() if isinstance(value, str) else ""


def rewrite(question, history):
    """One LLM call: classify scope, resolve follow-ups, translate to English.
    If the call fails or returns something unexpected, fall back to searching the original question."""
    try:
        data = llm.generate(prompts.rewrite_prompt(question, history), json_output=True, fast=True)
    except llm.LLMUnavailable:
        data = {}
    if not isinstance(data, dict):          # e.g. the model returned a JSON list
        data = {}
    scope = data.get("scope")
    return {"scope": scope if scope in SCOPES else "academic",
            "standalone": _text(data.get("standalone")) or question,
            "english": _text(data.get("english"))}


def _numbers(group):
    return [int(n) - 1 for n in re.split(r"\s*[,،]\s*", group)]


def _cite(answer_text, hits):
    """Keep only the excerpts the answer cites, as sources, and renumber the markers to match:
    an answer citing [3] and [5] becomes [1] and [2], the positions of its sources in the list.
    Returns (answer_text, sources)."""
    cited = []
    for group in CITATION.findall(answer_text):
        for i in _numbers(group):
            if 0 <= i < len(hits) and i not in cited:
                cited.append(i)
    position = {i: n for n, i in enumerate(cited, start=1)}

    def renumber(match):
        nums = list(dict.fromkeys(position[i] for i in _numbers(match.group(1)) if i in position))
        return f"[{', '.join(map(str, nums))}]" if nums else match.group(0)   # e.g. "[2024]" stays

    sources = []
    for i in cited or [0]:          # no citation at all: still show the best excerpt
        c = hits[i].chunk
        body = c.text.split("\n", 1)[-1]
        sources.append(Source(document=c.source, title=c.title, page=c.page, section=c.section,
                              snippet=" ".join(body.split())[:240]))
    return CITATION.sub(renumber, answer_text), sources


def ask(question, history=None):
    history = (history or [])[-2 * config.HISTORY_TURNS:]
    q = rewrite(question, history)

    if q["scope"] == "greeting":
        return Answer(prompts.GREETING_MSG, reason="greeting", standalone_question=q["standalone"])
    if q["scope"] == "out_of_scope":
        return Answer(prompts.OUT_OF_SCOPE_MSG, refused=True, reason="out_of_scope",
                      standalone_question=q["standalone"])

    hits, best = retrieve([q["standalone"], q["english"], question])
    debug = {"standalone_question": q["standalone"], "best_distance": best,
             "retrieved": [h.chunk.text for h in hits]}
    if not hits or best > config.MAX_DIST:          # nothing close enough: never call the LLM
        return Answer(prompts.NOT_FOUND_MSG, refused=True, reason="not_found", **debug)

    try:
        text = llm.generate(prompts.answer_prompt(q["standalone"], hits)).strip()
    except llm.LLMUnavailable:
        return Answer(prompts.LLM_DOWN_MSG, refused=True, reason="llm_unavailable", **debug)

    if not text or text.startswith(prompts.NOT_FOUND_MARK):
        return Answer(prompts.NOT_FOUND_MSG, refused=True, reason="not_found", **debug)
    text, sources = _cite(text, hits)
    return Answer(text, sources=sources, **debug)
