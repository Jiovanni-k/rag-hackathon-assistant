"""Use case: answer a student's question (with optional conversation history)."""
import re

from rag import config
from rag.application import prompts
from rag.application.retrieval_service import retrieve
from rag.domain.entities import Answer, Source
from rag.infrastructure import llm

CITATION = re.compile(r"\[(\d+(?:\s*[,،]\s*\d+)*)\]")


def rewrite(question, history):
    """One LLM call: classify scope, resolve follow-ups, translate to English."""
    try:
        data = llm.generate(prompts.rewrite_prompt(question, history), json_output=True, fast=True)
        return {"scope": data.get("scope", "academic"),
                "standalone": data.get("standalone") or question,
                "english": data.get("english") or ""}
    except llm.LLMUnavailable:
        return {"scope": "academic", "standalone": question, "english": ""}


def _sources(answer_text, hits):
    cited = []
    for group in CITATION.findall(answer_text):
        for n in re.split(r"\s*[,،]\s*", group):
            i = int(n) - 1
            if 0 <= i < len(hits) and i not in cited:
                cited.append(i)
    sources = []
    for i in cited or [0]:
        c = hits[i].chunk
        body = c.text.split("\n", 1)[-1]
        sources.append(Source(document=c.source, title=c.title, page=c.page, section=c.section,
                              snippet=" ".join(body.split())[:240]))
    return sources


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
    return Answer(text, sources=_sources(text, hits), **debug)
