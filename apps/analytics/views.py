from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from . import services


class SummaryParams(serializers.Serializer):
    days = serializers.IntegerField(min_value=1, max_value=365, default=30)


class TopParams(SummaryParams):
    limit = serializers.IntegerField(min_value=1, max_value=50, default=10)


@api_view(["GET"])
@permission_classes([IsAdminUser])
def summary(request):
    params = SummaryParams(data=request.query_params)
    params.is_valid(raise_exception=True)
    return Response(services.summary(params.validated_data["days"]))


@api_view(["GET"])
@permission_classes([IsAdminUser])
def top_questions(request):
    params = TopParams(data=request.query_params)
    params.is_valid(raise_exception=True)
    return Response({"results": services.top_questions(**params.validated_data)})
