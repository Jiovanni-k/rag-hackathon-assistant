from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

from apps.core.errors import ApiError

from .serializers import LoginSerializer, RegisterSerializer, UserSerializer


class AuthThrottle(SimpleRateThrottle):
    """Per-IP limit on login/register against password guessing (DEFAULT_THROTTLE_RATES["auth"])."""
    scope = "auth"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


def _auth_response(user, code=status.HTTP_200_OK):
    token, _ = Token.objects.get_or_create(user=user)
    return Response({"token": token.key, "user": UserSerializer(user).data}, status=code)


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AuthThrottle])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    return _auth_response(serializer.save(), status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AuthThrottle])
def login(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = authenticate(**serializer.validated_data)
    if user is None:
        raise ApiError("unauthorized", "Wrong username or password.", status.HTTP_401_UNAUTHORIZED)
    return _auth_response(user)


@api_view(["POST"])
def logout(request):
    Token.objects.filter(user=request.user).delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
def me(request):
    return Response(UserSerializer(request.user).data)
