from rest_framework import serializers

from .models import Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ["id", "role", "content", "sources", "refused", "reason", "feedback", "created_at"]
        read_only_fields = fields


class ConversationSerializer(serializers.ModelSerializer):
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ["id", "title", "created_at", "updated_at", "message_count"]
        read_only_fields = ["id", "created_at", "updated_at", "message_count"]

    def get_message_count(self, obj):
        count = getattr(obj, "num_messages", None)
        return count if count is not None else obj.messages.count()

    def validate_title(self, value):
        value = " ".join(value.split())
        if not value:
            raise serializers.ValidationError("Title must not be empty.")
        return value


class ConversationDetailSerializer(ConversationSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta(ConversationSerializer.Meta):
        fields = ConversationSerializer.Meta.fields + ["messages"]


class AskSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=1000, trim_whitespace=True)
    conversation_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_question(self, value):
        if not any(ch.isalpha() for ch in value):      # e.g. "????" from a broken encoding
            raise serializers.ValidationError("Question must contain words.")
        return value


class FeedbackSerializer(serializers.Serializer):
    rating = serializers.ChoiceField(choices=["up", "down"], allow_null=True)
    comment = serializers.CharField(max_length=500, required=False, allow_blank=True)
