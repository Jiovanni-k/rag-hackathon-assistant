from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie


class LoginView(auth_views.LoginView):
    template_name = "web/login.html"
    redirect_authenticated_user = True


@login_required
@ensure_csrf_cookie
def chat(request):
    return render(request, "web/chat.html", {"page": "chat"})


@staff_member_required(login_url="web:login")
@ensure_csrf_cookie
def staff_documents(request):
    return render(request, "web/staff_documents.html", {"page": "documents"})


@staff_member_required(login_url="web:login")
@ensure_csrf_cookie
def staff_analytics(request):
    return render(request, "web/staff_analytics.html", {"page": "analytics"})
