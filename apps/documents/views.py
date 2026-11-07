from django.conf import settings
from django.db import transaction
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response

from apps.core.errors import ApiError
from rag.infrastructure import vector_store
from rag.infrastructure.loaders import SUPPORTED

from . import services
from .models import Document
from .serializers import DocumentSerializer, UploadSerializer


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    chunks = vector_store.count()
    return Response({
        "status": "ok" if chunks else "degraded",
        "documents": Document.objects.count(),
        "chunks": chunks,
        "reindexing": services.is_reindexing(),
    })


class DocumentViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                      mixins.DestroyModelMixin, viewsets.GenericViewSet):
    queryset = Document.objects.select_related("uploaded_by")
    serializer_class = DocumentSerializer
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def create(self, request):
        form = UploadSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        upload = form.validated_data["file"]
        filename = services.safe_filename(upload.name)

        if not any(filename.lower().endswith(ext) for ext in SUPPORTED):
            raise ApiError("unsupported_file_type", "Only .pdf and .txt files are allowed.",
                           status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
        if upload.size > settings.MAX_UPLOAD_MB * 1024 * 1024:
            raise ApiError("file_too_large", f"File is larger than {settings.MAX_UPLOAD_MB} MB.",
                           status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
        if Document.objects.filter(filename=filename).exists():
            raise ApiError("validation_error", "A document with this file name already exists. "
                           "Delete it first or rename the file.", details={"file": ["Duplicate file name."]})

        path = services.documents_dir() / filename
        with open(path, "wb") as out:
            for part in upload.chunks():
                out.write(part)

        doc = Document.objects.create(
            title=form.validated_data.get("title") or filename, filename=filename,
            version_year=form.validated_data.get("version_year"), uploaded_by=request.user)
        transaction.on_commit(lambda: services.start_indexing(doc))
        return Response(DocumentSerializer(doc).data, status=status.HTTP_202_ACCEPTED)

    def perform_destroy(self, doc):
        services.delete_document(doc)

    @action(detail=False, methods=["post"])
    def reindex(self, request):
        if not services.start_reindex():
            raise ApiError("conflict", "A re-index is already running.", status.HTTP_409_CONFLICT)
        return Response({"status": "processing", "documents": Document.objects.count()},
                        status=status.HTTP_202_ACCEPTED)
