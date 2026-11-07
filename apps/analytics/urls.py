from django.urls import path

from . import views

urlpatterns = [
    path("summary/", views.summary),
    path("top-questions/", views.top_questions),
]
