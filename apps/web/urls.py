from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "web"

urlpatterns = [
    path("", views.chat, name="chat"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),   # POST only (CSRF)
    path("staff/documents/", views.staff_documents, name="staff_documents"),
    path("staff/analytics/", views.staff_analytics, name="staff_analytics"),
]
