from rest_framework import serializers

from .models import Document


class DocumentSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.CharField(source="uploaded_by.username", default=None, read_only=True)

    class Meta:
        model = Document
        fields = ["id", "title", "filename", "version_year", "status", "pages", "chunk_count",
                  "error", "uploaded_by", "uploaded_at"]
        read_only_fields = fields


class UploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    title = serializers.CharField(max_length=200, required=False, allow_blank=True)
    version_year = serializers.IntegerField(min_value=1950, max_value=2100, required=False, allow_null=True)
