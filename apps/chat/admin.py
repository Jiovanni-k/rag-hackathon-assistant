from django.contrib import admin

from .models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    fields = ["role", "content", "refused", "reason", "feedback", "latency_ms", "created_at"]
    readonly_fields = fields
    extra = 0
    fk_name = "conversation"


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ["title", "user", "updated_at"]
    search_fields = ["title", "user__username"]
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["role", "short", "refused", "reason", "feedback", "latency_ms", "created_at"]
    list_filter = ["role", "refused", "reason", "feedback"]
    search_fields = ["content"]

    @admin.display(description="content")
    def short(self, obj):
        return obj.content[:80]
