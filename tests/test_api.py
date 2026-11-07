"""API tests for docs/API.md. The RAG core (LLM + index) is mocked, so these run offline in seconds.

Run:  python manage.py test tests
"""
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from apps.chat.models import Message
from apps.documents import services as doc_services
from apps.documents.models import Document
from rag.domain.entities import Answer, Source

User = get_user_model()
API = "/api/v1"


def fake_answer(text="الحد الأدنى للمعدل هو 2.00 [1].", refused=False, reason="answered"):
    sources = [] if refused else [Source("BU_English_Catalog.pdf", "جامعة بيت لحم", 20,
                                         "3. DEGREE REQUIREMENTS", "minimum GPA of 2.00")]
    return Answer(text, sources=sources, refused=refused, reason=reason)


class ApiTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user("sara", "sara@example.com", "S3cure-pass-123")
        self.admin = User.objects.create_user("admin", "a@example.com", "Adm1n-pass-123", is_staff=True)

    def login(self, user):
        self.client.force_authenticate(user)

    def assertError(self, response, status, code):
        self.assertEqual(response.status_code, status, response.content)
        self.assertEqual(response.json()["error"]["code"], code)


class AuthTests(ApiTestCase):
    def test_register_login_me_logout(self):
        r = self.client.post(f"{API}/auth/register/", {"username": "ahmad", "email": "a@x.com",
                                                       "password": "Strong-pass-987"}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertIn("token", r.json())
        self.assertFalse(r.json()["user"]["is_staff"])

        r = self.client.post(f"{API}/auth/login/", {"username": "ahmad", "password": "Strong-pass-987"},
                             format="json")
        token = r.json()["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        self.assertEqual(self.client.get(f"{API}/auth/me/").json()["username"], "ahmad")
        self.assertEqual(self.client.post(f"{API}/auth/logout/").status_code, 204)
        self.assertError(self.client.get(f"{API}/auth/me/"), 401, "unauthorized")

    def test_wrong_password_and_weak_password(self):
        r = self.client.post(f"{API}/auth/login/", {"username": "sara", "password": "nope"}, format="json")
        self.assertError(r, 401, "unauthorized")
        r = self.client.post(f"{API}/auth/register/", {"username": "x", "password": "123"}, format="json")
        self.assertError(r, 400, "validation_error")
        self.assertIn("password", r.json()["error"]["details"])

    def test_health_is_public(self):
        with patch("apps.documents.views.vector_store.count", return_value=42):
            r = self.client.get(f"{API}/health/")
        self.assertEqual(r.json()["status"], "ok")
        self.assertEqual(r.json()["chunks"], 42)


@patch("apps.chat.services.ask_service.ask")
class ChatTests(ApiTestCase):
    def test_requires_login(self, ask):
        self.assertError(self.client.post(f"{API}/chat/ask/", {"question": "x"}, format="json"),
                         401, "unauthorized")

    def test_ask_new_conversation_and_follow_up(self, ask):
        ask.return_value = fake_answer()
        Document.objects.create(title="Catalog", filename="BU_English_Catalog.pdf", status="ready")
        self.login(self.user)
        r = self.client.post(f"{API}/chat/ask/", {"question": "شو المعدل اللي بدي إياه عشان أتخرج؟"},
                             format="json")
        self.assertEqual(r.status_code, 200, r.content)
        body = r.json()
        self.assertEqual(body["question"]["role"], "user")
        self.assertEqual(body["answer"]["sources"][0]["page"], 20)
        self.assertIsNotNone(body["answer"]["sources"][0]["document_id"])
        self.assertEqual(body["conversation"]["message_count"], 2)
        conv_id = body["conversation"]["id"]

        r = self.client.post(f"{API}/chat/ask/", {"question": "وإذا كان معدلي أعلى؟",
                                                  "conversation_id": conv_id}, format="json")
        self.assertEqual(r.json()["conversation"]["id"], conv_id)
        history = ask.call_args.args[1]
        self.assertEqual([m["role"] for m in history], ["user", "assistant"])

    def test_refusal_is_200_with_flag(self, ask):
        ask.return_value = fake_answer("لا أجد هذه المعلومة...", refused=True, reason="not_found")
        self.login(self.user)
        r = self.client.post(f"{API}/chat/ask/", {"question": "متى امتحان الخوارزميات؟"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["answer"]["refused"])
        self.assertEqual(r.json()["answer"]["sources"], [])

    def test_llm_unavailable_is_503_and_saves_nothing(self, ask):
        ask.return_value = fake_answer("busy", refused=True, reason="llm_unavailable")
        self.login(self.user)
        r = self.client.post(f"{API}/chat/ask/", {"question": "سؤال"}, format="json")
        self.assertError(r, 503, "llm_unavailable")
        self.assertEqual(Message.objects.count(), 0)

    def test_validation_and_other_users_conversation(self, ask):
        ask.return_value = fake_answer()
        self.login(self.user)
        self.assertError(self.client.post(f"{API}/chat/ask/", {"question": ""}, format="json"),
                         400, "validation_error")
        self.assertError(self.client.post(f"{API}/chat/ask/", {"question": "????"}, format="json"),
                         400, "validation_error")         # broken encoding never reaches the LLM
        conv_id = self.client.post(f"{API}/chat/ask/", {"question": "q"}, format="json").json()["conversation"]["id"]
        self.login(self.admin)
        r = self.client.post(f"{API}/chat/ask/", {"question": "q", "conversation_id": conv_id}, format="json")
        self.assertError(r, 404, "not_found")
        self.assertError(self.client.get(f"{API}/conversations/{conv_id}/"), 404, "not_found")

    def test_conversations_crud_and_feedback(self, ask):
        ask.return_value = fake_answer()
        self.login(self.user)
        body = self.client.post(f"{API}/chat/ask/", {"question": "سؤال أول"}, format="json").json()
        conv_id, answer_id, question_id = body["conversation"]["id"], body["answer"]["id"], body["question"]["id"]

        listing = self.client.get(f"{API}/conversations/").json()
        self.assertEqual(listing["count"], 1)
        detail = self.client.get(f"{API}/conversations/{conv_id}/").json()
        self.assertEqual(len(detail["messages"]), 2)

        r = self.client.patch(f"{API}/conversations/{conv_id}/", {"title": "عنوان جديد"}, format="json")
        self.assertEqual(r.json()["title"], "عنوان جديد")

        r = self.client.post(f"{API}/messages/{answer_id}/feedback/", {"rating": "down", "comment": "ناقص"},
                             format="json")
        self.assertEqual(r.json()["feedback"], "down")
        self.assertError(self.client.post(f"{API}/messages/{question_id}/feedback/", {"rating": "up"},
                                          format="json"), 404, "not_found")

        self.assertEqual(self.client.delete(f"{API}/conversations/{conv_id}/").status_code, 204)
        self.assertEqual(self.client.get(f"{API}/conversations/").json()["count"], 0)


class DocumentTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.tmp = Path(tempfile.mkdtemp())
        self.patches = [
            patch("apps.documents.services.config.DOCUMENTS_DIR", self.tmp),
            patch("apps.documents.services.ingest_service.index_file", return_value=(7, 3)),
            patch("apps.documents.services.ingest_service.remove_file"),
            patch("apps.documents.services.close_old_connections"),
            patch.object(doc_services, "start_indexing", lambda doc: doc_services._index_one(doc.pk)),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def upload(self, name="plan.txt", content=b"# title\nhello"):
        return self.client.post(f"{API}/documents/", {"file": SimpleUploadedFile(name, content),
                                                      "title": "خطة", "version_year": 2024},
                                format="multipart")

    def test_admin_only(self):
        self.login(self.user)
        self.assertError(self.client.get(f"{API}/documents/"), 403, "forbidden")

    def test_upload_index_list_delete(self):
        self.login(self.admin)
        with self.captureOnCommitCallbacks(execute=True):
            r = self.upload()
        self.assertEqual(r.status_code, 202, r.content)
        self.assertEqual(r.json()["status"], "processing")
        doc_id = r.json()["id"]
        self.assertTrue((self.tmp / "plan.txt").exists())

        doc = self.client.get(f"{API}/documents/{doc_id}/").json()
        self.assertEqual((doc["status"], doc["chunk_count"], doc["pages"]), ("ready", 7, 3))
        self.assertEqual(self.client.get(f"{API}/documents/").json()["count"], 1)

        self.assertError(self.upload(), 400, "validation_error")          # duplicate name
        self.assertError(self.upload("virus.exe"), 415, "unsupported_file_type")

        self.assertEqual(self.client.delete(f"{API}/documents/{doc_id}/").status_code, 204)
        self.assertFalse((self.tmp / "plan.txt").exists())


@patch("apps.chat.services.ask_service.ask")
class AnalyticsTests(ApiTestCase):
    def test_summary_and_top_questions(self, ask):
        self.login(self.user)
        ask.return_value = fake_answer()
        for q in ["كيف أسجل المواد؟", "كيف اسجل المواد", "ما المعدل المطلوب؟"]:
            self.client.post(f"{API}/chat/ask/", {"question": q}, format="json")
        ask.return_value = fake_answer("لا أجد", refused=True, reason="not_found")
        self.client.post(f"{API}/chat/ask/", {"question": "متى الامتحان؟"}, format="json")

        self.assertError(self.client.get(f"{API}/analytics/summary/"), 403, "forbidden")
        self.login(self.admin)
        s = self.client.get(f"{API}/analytics/summary/?days=7").json()
        self.assertEqual(s["total_questions"], 4)
        self.assertEqual(s["active_users"], 1)
        self.assertEqual(s["refusal_rate"], 0.25)

        top = self.client.get(f"{API}/analytics/top-questions/?limit=5").json()["results"]
        self.assertEqual(top[0]["count"], 2)                 # spelling variants grouped together
        self.assertEqual(sum(t["refused_count"] for t in top), 1)
        self.assertError(self.client.get(f"{API}/analytics/summary/?days=0"), 400, "validation_error")
