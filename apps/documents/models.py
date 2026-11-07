from django.conf import settings
from django.db import models


class Document(models.Model):
    class Status(models.TextChoices):
        PROCESSING = "processing"
        READY = "ready"
        FAILED = "failed"

    title = models.CharField(max_length=200)
    filename = models.CharField(max_length=255, unique=True)   # file inside rag.config.DOCUMENTS_DIR
    version_year = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PROCESSING)
    pages = models.PositiveIntegerField(default=0)
    chunk_count = models.PositiveIntegerField(default=0)
    error = models.TextField(null=True, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="documents")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.title
