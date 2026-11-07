from django.conf import settings
from django.db import models


class Conversation(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversations")
    title = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title


class Message(models.Model):
    class Role(models.TextChoices):
        USER = "user"
        ASSISTANT = "assistant"

    class Feedback(models.TextChoices):
        UP = "up"
        DOWN = "down"

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=10, choices=Role.choices)
    content = models.TextField()
    sources = models.JSONField(default=list, blank=True)
    refused = models.BooleanField(default=False)
    reason = models.CharField(max_length=20, blank=True)      # answered | not_found | out_of_scope | greeting
    feedback = models.CharField(max_length=4, choices=Feedback.choices, null=True, blank=True)
    feedback_comment = models.CharField(max_length=500, blank=True)
    latency_ms = models.PositiveIntegerField(null=True, blank=True)
    normalized = models.CharField(max_length=300, blank=True, db_index=True)  # for "top questions"
    reply_to = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE,
                                 related_name="replies")       # assistant message -> its question
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.role}: {self.content[:50]}"
