"""Application layer for chat: conversation history in the database + the RAG core."""
import re
import time

from django.db import transaction
from rest_framework import status

from apps.core.errors import ApiError
from apps.documents.models import Document
from rag import config
from rag.application import ask_service
from rag.infrastructure.arabic import normalize

from .models import Conversation, Message


def normalize_question(text):
    """Fold spelling variants and punctuation so similar questions group together."""
    text = re.sub(r"[^\w\s]", " ", normalize(text))
    return " ".join(text.split())[:300]


def make_title(question):
    title = " ".join(question.split())
    return title if len(title) <= 60 else title[:57].rstrip() + "..."


def _history(conversation):
    if conversation is None:
        return []
    recent = conversation.messages.order_by("-created_at", "-id")[:2 * config.HISTORY_TURNS]
    return [{"role": m.role, "content": m.content} for m in reversed(recent)]


def _source_dicts(sources):
    ids = dict(Document.objects.filter(filename__in={s.document for s in sources})
               .values_list("filename", "id"))
    return [{"document_id": ids.get(s.document), "document": s.document, "title": s.title,
             "page": s.page or None, "article": s.section or None, "snippet": s.snippet}
            for s in sources]


def ask(user, question, conversation_id=None):
    """Answer a question inside a conversation. Returns (conversation, question_msg, answer_msg, ms)."""
    conversation = None
    if conversation_id:
        conversation = Conversation.objects.filter(pk=conversation_id, user=user).first()
        if conversation is None:
            raise ApiError("not_found", "Conversation not found.", status.HTTP_404_NOT_FOUND)

    started = time.time()
    answer = ask_service.ask(question, _history(conversation))
    latency_ms = int((time.time() - started) * 1000)
    if answer.reason == "llm_unavailable":
        raise ApiError("llm_unavailable", answer.text, status.HTTP_503_SERVICE_UNAVAILABLE)

    with transaction.atomic():
        if conversation is None:
            conversation = Conversation.objects.create(user=user, title=make_title(question))
        q_msg = Message.objects.create(conversation=conversation, role=Message.Role.USER,
                                       content=question, normalized=normalize_question(question))
        a_msg = Message.objects.create(
            conversation=conversation, role=Message.Role.ASSISTANT, content=answer.text,
            sources=_source_dicts(answer.sources), refused=answer.refused, reason=answer.reason,
            latency_ms=latency_ms, reply_to=q_msg)
        conversation.save(update_fields=["updated_at"])
    return conversation, q_msg, a_msg, latency_ms
