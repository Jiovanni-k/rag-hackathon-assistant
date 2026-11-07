from django.contrib import admin
from django.urls import include, path

api_v1 = [
    path("", include("apps.documents.urls")),      # /health/, /documents/...
    path("auth/", include("apps.accounts.urls")),
    path("", include("apps.chat.urls")),           # /chat/ask/, /conversations/, /messages/
    path("analytics/", include("apps.analytics.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(api_v1)),
]
