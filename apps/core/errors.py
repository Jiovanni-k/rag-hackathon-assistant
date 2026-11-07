"""One error shape for the whole API (see docs/API.md §1):

    {"error": {"code": "validation_error", "message": "...", "details": {...}}}
"""
import logging

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response

log = logging.getLogger("apps")


class ApiError(exceptions.APIException):
    """Raise anywhere to return a specific error code and HTTP status."""

    def __init__(self, code, message, status_code=status.HTTP_400_BAD_REQUEST, details=None):
        super().__init__(message)
        self.code, self.message, self.status_code, self.details = code, message, status_code, details or {}


CODES = [
    (exceptions.ValidationError, "validation_error", "Some fields are invalid."),
    (exceptions.NotAuthenticated, "unauthorized", "Authentication credentials were not provided."),
    (exceptions.AuthenticationFailed, "unauthorized", "Invalid or expired token."),
    (exceptions.PermissionDenied, "forbidden", "You do not have permission to do this."),
    (exceptions.NotFound, "not_found", "Not found."),
    (exceptions.Throttled, "rate_limited", "Too many requests. Please slow down."),
    (exceptions.UnsupportedMediaType, "unsupported_file_type", "Unsupported media type."),
    (exceptions.MethodNotAllowed, "method_not_allowed", "Method not allowed."),
    (exceptions.ParseError, "validation_error", "Malformed request body."),
]


def _first_message(details):
    if isinstance(details, dict):
        for value in details.values():
            return _first_message(value)
    if isinstance(details, list) and details:
        return _first_message(details[0])
    return str(details)


def _body(code, message, details=None):
    return {"error": {"code": code, "message": message, "details": details or {}}}


def exception_handler(exc, context):
    if isinstance(exc, ApiError):
        return Response(_body(exc.code, exc.message, exc.details), status=exc.status_code)
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, DjangoPermissionDenied):
        exc = exceptions.PermissionDenied()

    for cls, code, default in CODES:
        if isinstance(exc, cls):
            if cls is exceptions.ValidationError:
                details = exc.detail if isinstance(exc.detail, dict) else {"non_field_errors": exc.detail}
                return Response(_body(code, _first_message(details), details), status=exc.status_code)
            message = str(exc.detail) if getattr(exc, "detail", None) else default
            response = Response(_body(code, message), status=exc.status_code)
            if isinstance(exc, exceptions.Throttled) and exc.wait:
                response["Retry-After"] = str(int(exc.wait))
            return response

    if isinstance(exc, exceptions.APIException):
        return Response(_body("server_error", str(exc.detail)), status=exc.status_code)
    log.exception("Unhandled API error", exc_info=exc)
    return Response(_body("server_error", "Something went wrong. Please try again."),
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR)
