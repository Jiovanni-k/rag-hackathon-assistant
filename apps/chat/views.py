from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework import mixins, viewsets
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from . import services
from .models import Conversation, Message
from .serializers import (AskSerializer, ConversationDetailSerializer, ConversationSerializer,
                          FeedbackSerializer, MessageSerializer)


class AskThrottle(UserRateThrottle):
    """Per-user limit on questions (settings: DEFAULT_THROTTLE_RATES["ask"])."""
    scope = "ask"


@api_view(["POST"])
@throttle_classes([AskThrottle])
def ask(request):
    form = AskSerializer(data=request.data)
    form.is_valid(raise_exception=True)
    conversation, q_msg, a_msg, latency_ms = services.ask(
        request.user, form.validated_data["question"], form.validated_data.get("conversation_id"))
    return Response({
        "conversation": ConversationSerializer(conversation).data,
        "question": MessageSerializer(q_msg).data,
        "answer": MessageSerializer(a_msg).data,
        "latency_ms": latency_ms,
    })


class ConversationViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin,
                          mixins.DestroyModelMixin, viewsets.GenericViewSet):
    http_method_names = ["get", "patch", "delete"]

    def get_queryset(self):
        qs = (Conversation.objects.filter(user=self.request.user)
              .annotate(num_messages=Count("messages"))
              .order_by("-updated_at", "-id"))          # aggregates drop Meta.ordering
        if self.action == "retrieve":
            qs = qs.prefetch_related("messages")
        return qs

    def get_serializer_class(self):
        return ConversationDetailSerializer if self.action == "retrieve" else ConversationSerializer


@api_view(["POST"])
def feedback(request, pk):
    message = get_object_or_404(Message, pk=pk, role=Message.Role.ASSISTANT,
                                conversation__user=request.user)
    form = FeedbackSerializer(data=request.data)
    form.is_valid(raise_exception=True)
    message.feedback = form.validated_data["rating"]
    message.feedback_comment = form.validated_data.get("comment", "") if message.feedback else ""
    message.save(update_fields=["feedback", "feedback_comment"])
    return Response(MessageSerializer(message).data)
