from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("conversations", views.ConversationViewSet, basename="conversation")

urlpatterns = [
    path("chat/ask/", views.ask),
    path("messages/<int:pk>/feedback/", views.feedback),
] + router.urls
