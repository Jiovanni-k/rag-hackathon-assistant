"""Web UI tests: page access, login/logout, CSRF on session requests, demo accounts."""
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase

from rag.domain.entities import Answer

User = get_user_model()


class WebPagesTests(TestCase):
    def setUp(self):
        call_command("create_demo_accounts", stdout=StringIO())

    def test_demo_accounts_created(self):
        self.assertFalse(User.objects.get(username="student").is_staff)
        admin = User.objects.get(username="admin")
        self.assertTrue(admin.is_staff and admin.is_superuser)

    def test_login_page_shows_configured_demo_passwords(self):
        with self.settings(DEMO_STUDENT_PASSWORD="s-custom-pass", SHOW_DEMO_ACCOUNTS=True):
            self.assertContains(Client().get("/login/"), "s-custom-pass")
        with self.settings(SHOW_DEMO_ACCOUNTS=False):
            self.assertNotContains(Client().get("/login/"), "student-demo-2026")

    def test_chat_requires_login_and_login_works(self):
        c = Client()
        r = c.get("/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login/", r["Location"])
        r = c.post("/login/", {"username": "student", "password": "student-demo-2026"}, follow=True)
        self.assertContains(r, 'id="composer"')
        self.assertNotContains(r, "/staff/documents/")          # no staff links for students
        r = Client().post("/login/", {"username": "student", "password": "wrong"})
        self.assertEqual(r.status_code, 200)                    # stays on the login page
        self.assertContains(r, "alert-error")

    def test_staff_pages_need_staff(self):
        c = Client()
        c.login(username="student", password="student-demo-2026")
        self.assertEqual(c.get("/staff/documents/").status_code, 302)
        self.assertEqual(c.get("/staff/analytics/").status_code, 302)
        c.login(username="admin", password="admin-demo-2026")
        for path in ["/staff/documents/", "/staff/analytics/", "/"]:
            r = c.get(path)
            self.assertEqual(r.status_code, 200, path)
            self.assertContains(r, "/staff/analytics/")

    def test_logout_is_post_only(self):
        c = Client()
        c.login(username="student", password="student-demo-2026")
        self.assertEqual(c.get("/logout/").status_code, 405)
        self.assertEqual(c.post("/logout/").status_code, 302)
        self.assertEqual(c.get("/").status_code, 302)

    @patch("apps.chat.services.ask_service.ask", return_value=Answer("جواب [1]."))
    def test_session_api_enforces_csrf(self, ask):
        c = Client(enforce_csrf_checks=True)
        c.login(username="student", password="student-demo-2026")
        r = c.post("/api/v1/chat/ask/", {"question": "سؤال"}, content_type="application/json")
        self.assertEqual(r.status_code, 403)                    # no CSRF token
        page = c.get("/")                                       # sets the csrftoken cookie
        token = page.cookies["csrftoken"].value
        r = c.post("/api/v1/chat/ask/", {"question": "سؤال"}, content_type="application/json",
                   HTTP_X_CSRFTOKEN=token)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["answer"]["reason"], "answered")
