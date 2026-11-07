# Smart Academic Advisor — API Reference (v1)

> **Status:** implemented (Django + DRF). Run it locally with `python manage.py runserver` — see README.
> If you need a change, ask before building around it so backend and frontend stay in sync.

---

## 1. Basics

| Item | Value |
|---|---|
| Base URL (local) | `http://localhost:8000/api/v1` |
| Base URL (production) | TBD (will be shared after deployment) |
| Format | JSON (`Content-Type: application/json`), except file upload (`multipart/form-data`) |
| Encoding | UTF-8. Questions and answers are mostly **Arabic** |
| Dates | ISO 8601 in UTC, e.g. `2026-11-07T10:42:13Z` |
| IDs | integers |
| Trailing slash | **required** on every path (`/conversations/`, not `/conversations`) |

### Authentication

Token authentication. Log in once, store the token, send it on every request:

```
Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
```

- Every endpoint needs a token **except** `register`, `login` and `health`.
- Admin endpoints (documents, analytics) also need `user.is_staff == true`.
  Use `is_staff` from `/auth/me/` to decide whether to show the admin pages.
- Missing/invalid token → `401`. Logged in but not admin → `403`.

### CORS

Local dev origins allowed: `http://localhost:3000`, `http://localhost:5173`. Tell the backend if you use another port.

### Pagination

List endpoints are paginated with `?page=N` (20 items per page):

```json
{
  "count": 42,
  "next": "http://localhost:8000/api/v1/conversations/?page=2",
  "previous": null,
  "results": [ ... ]
}
```

### Errors

Every error has the same shape:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Question must not be empty.",
    "details": { "question": ["This field may not be blank."] }
  }
}
```

| HTTP | `code` | When |
|---|---|---|
| 400 | `validation_error` | Bad or missing fields. `details` maps field → messages |
| 401 | `unauthorized` | No token / invalid token / wrong login |
| 403 | `forbidden` | Not an admin |
| 404 | `not_found` | Resource does not exist or belongs to another user |
| 405 | `method_not_allowed` | Wrong HTTP method for this path |
| 409 | `conflict` | A re-index is already running |
| 413 | `file_too_large` | Upload over 20 MB |
| 415 | `unsupported_file_type` | Upload is not `.pdf` or `.txt` |
| 429 | `rate_limited` | Too many questions (limit: 20 per minute per user) |
| 503 | `llm_unavailable` | The AI model is temporarily unavailable; show "try again" |
| 500 | `server_error` | Anything else |

Show `error.message` to the user; it is safe to display.

---

## 2. Data objects

### User
```json
{ "id": 7, "username": "sara", "email": "sara@example.com", "is_staff": false }
```

### Source (a citation attached to an answer)
```json
{
  "document_id": 3,
  "document": "BU_English_Catalog.pdf",
  "title": "جامعة بيت لحم — الدليل الأكاديمي (Bethlehem University Catalog)",
  "page": 29,
  "article": "ACADEMIC REGULATIONS — 11. WITHDRAWAL",
  "snippet": "Students may officially withdraw from a course up to the end of the tenth week of classes..."
}
```
- `page` is `null` for `.txt` documents (they have no pages) — show `article` instead.
- `article` (the section) may be `null` when the section is unknown.
- `document_id` may be `null` if the file is not registered as a Document.
- Suggested chip text: `title · ص {page}` or `title · {article}`.

### Message
```json
{
  "id": 118,
  "role": "assistant",
  "content": "نعم، يمكنك الانسحاب من المادة حتى نهاية الأسبوع العاشر من الفصل...",
  "sources": [ /* Source objects; empty for user messages and refusals */ ],
  "refused": false,
  "feedback": null,
  "created_at": "2026-11-07T10:42:13Z"
}
```
| Field | Notes |
|---|---|
| `role` | `"user"` or `"assistant"` |
| `content` | **Markdown** (may contain lists, bold, tables). Render it as markdown |
| `refused` | `true` when the system could not answer from the documents or the question was out of scope. Style it differently (e.g. neutral/yellow box) |
| `feedback` | `null`, `"up"` or `"down"` (assistant messages only) |

### Conversation
```json
{
  "id": 21,
  "title": "الانسحاب من مادة",
  "created_at": "2026-11-07T10:41:58Z",
  "updated_at": "2026-11-07T10:42:13Z",
  "message_count": 4
}
```
`title` is generated automatically from the first question; the user can rename it.

### Document (admin)
```json
{
  "id": 3,
  "title": "Bethlehem University Catalog",
  "filename": "BU_English_Catalog.pdf",
  "version_year": 2016,
  "status": "ready",
  "pages": 253,
  "chunk_count": 1310,
  "error": null,
  "uploaded_by": "admin",
  "uploaded_at": "2026-11-07T09:10:00Z"
}
```
`status`: `"processing"` → `"ready"` or `"failed"` (then `error` has the reason).

---

## 3. Endpoints

### Summary

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/health/` | — | Server and index status |
| POST | `/auth/register/` | — | Create account, returns token |
| POST | `/auth/login/` | — | Log in, returns token |
| POST | `/auth/logout/` | user | Invalidate token |
| GET | `/auth/me/` | user | Current user |
| POST | `/chat/ask/` | user | **Ask a question** (main endpoint) |
| GET | `/conversations/` | user | List my conversations |
| GET | `/conversations/{id}/` | user | One conversation with all messages |
| PATCH | `/conversations/{id}/` | user | Rename |
| DELETE | `/conversations/{id}/` | user | Delete |
| POST | `/messages/{id}/feedback/` | user | Thumbs up / down on an answer |
| GET | `/documents/` | admin | List documents |
| POST | `/documents/` | admin | Upload a document |
| GET | `/documents/{id}/` | admin | Document status (poll after upload) |
| DELETE | `/documents/{id}/` | admin | Remove a document |
| POST | `/documents/reindex/` | admin | Rebuild the whole index |
| GET | `/analytics/summary/` | admin | Dashboard numbers |
| GET | `/analytics/top-questions/` | admin | Most asked questions |

---

### 3.1 Health

#### `GET /health/`
```json
{ "status": "ok", "documents": 7, "chunks": 1602, "reindexing": false }
```
`status` is `"ok"` or `"degraded"` (e.g. index empty). `reindexing` is `true` while a full re-index runs.
Useful for a status dot in the admin page.

---

### 3.2 Auth

#### `POST /auth/register/`
Request:
```json
{ "username": "sara", "email": "sara@example.com", "password": "S3cure-pass" }
```
Response `201`:
```json
{ "token": "9944b091...", "user": { "id": 7, "username": "sara", "email": "sara@example.com", "is_staff": false } }
```
Errors: `400` (username taken, weak password; see `details`).

#### `POST /auth/login/`
Request:
```json
{ "username": "sara", "password": "S3cure-pass" }
```
Response `200`: same shape as register. Wrong credentials → `401`.

#### `POST /auth/logout/`
No body. Response `204`. Delete the stored token on the client.

#### `GET /auth/me/`
Response `200`: a **User** object.

---

### 3.3 Chat — the main endpoint

#### `POST /chat/ask/`

Ask a question. Omit `conversation_id` to start a new conversation; send it to continue one
(follow-up questions like «وإذا كان معدلي أعلى؟» only work inside the same conversation).

Request:
```json
{ "question": "هل بقدر أنسحب من مادة؟ ولحد إمتى؟", "conversation_id": 21 }
```
| Field | Type | Required | Notes |
|---|---|---|---|
| `question` | string | yes | 1–1000 characters |
| `conversation_id` | int | no | Omit or `null` for a new conversation |

Response `200`:
```json
{
  "conversation": { "id": 21, "title": "الانسحاب من مادة", "created_at": "2026-11-07T10:41:58Z", "updated_at": "2026-11-07T10:42:13Z", "message_count": 2 },
  "question": {
    "id": 117, "role": "user", "content": "هل بقدر أنسحب من مادة؟ ولحد إمتى؟",
    "sources": [], "refused": false, "feedback": null, "created_at": "2026-11-07T10:42:05Z"
  },
  "answer": {
    "id": 118,
    "role": "assistant",
    "content": "نعم، يمكنك الانسحاب رسميًا من المادة حتى **نهاية الأسبوع العاشر** من الفصل، وبعد ذلك لا يُقبل الانسحاب الرسمي.\n\n[BU_English_Catalog.pdf، صفحة 29]",
    "sources": [
      {
        "document_id": 3,
        "document": "BU_English_Catalog.pdf",
        "page": 29,
        "article": "10. WITHDRAWAL",
        "snippet": "Students may officially withdraw from a course up to the end of the tenth week of classes..."
      }
    ],
    "refused": false,
    "feedback": null,
    "created_at": "2026-11-07T10:42:13Z"
  },
  "latency_ms": 4210
}
```

Refusal example (`200`, not an error):
```json
{
  "conversation": { "id": 22, "title": "موعد امتحان الخوارزميات", "...": "..." },
  "question": { "id": 120, "role": "user", "content": "متى امتحان مادة الخوارزميات الأسبوع القادم؟", "...": "..." },
  "answer": {
    "id": 121,
    "role": "assistant",
    "content": "لا أجد هذه المعلومة في المستندات المتاحة لي. يرجى مراجعة دائرة القبول والتسجيل أو جدول الامتحانات الرسمي.",
    "sources": [],
    "refused": true,
    "feedback": null,
    "created_at": "2026-11-07T10:45:02Z"
  },
  "latency_ms": 900
}
```

**Frontend notes**
- Answers take **2–15 seconds**. Show the user's message immediately, then a typing indicator.
  Use a client timeout of **60 s**.
- Disable the send button while waiting (one question at a time per conversation).
- After the first answer, store `conversation.id` and send it with every follow-up.
- Show each source as a chip/badge: `BU_English_Catalog.pdf · ص 29`. Clicking it can expand `snippet`.
- `503 llm_unavailable` → keep the user's text in the input box and show a "try again" button.

---

### 3.4 Conversations (chat history sidebar)

#### `GET /conversations/?page=1`
Paginated list of the current user's **Conversation** objects, newest `updated_at` first.

#### `GET /conversations/{id}/`
```json
{
  "id": 21,
  "title": "الانسحاب من مادة",
  "created_at": "2026-11-07T10:41:58Z",
  "updated_at": "2026-11-07T10:42:13Z",
  "message_count": 2,
  "messages": [ /* Message objects, oldest first */ ]
}
```

#### `PATCH /conversations/{id}/`
Request: `{ "title": "سؤالي عن الانسحاب" }` (1–100 chars). Response `200`: the updated **Conversation**.

#### `DELETE /conversations/{id}/`
Response `204`.

---

### 3.5 Feedback

#### `POST /messages/{id}/feedback/`
Only on assistant messages that belong to the user.

Request:
```json
{ "rating": "down", "comment": "المعلومة ناقصة" }
```
`rating`: `"up"`, `"down"`, or `null` to clear. `comment` optional (max 500 chars).
Response `200`: the updated **Message**.

---

### 3.6 Documents (admin)

#### `GET /documents/`
Paginated list of **Document** objects.

#### `POST /documents/` — `multipart/form-data`
| Field | Type | Required | Notes |
|---|---|---|---|
| `file` | file | yes | `.pdf` or `.txt`, max 20 MB |
| `title` | string | no | Defaults to the filename |
| `version_year` | int | no | e.g. `2024`. Used to prefer the newest document when two conflict |

Response `202` (accepted, processing in the background): a **Document** with `"status": "processing"`.

**Poll** `GET /documents/{id}/` every 3 seconds until `status` is `"ready"` or `"failed"`.
Processing a large PDF can take a few minutes.

#### `GET /documents/{id}/`
Response `200`: a **Document**.

#### `DELETE /documents/{id}/`
Removes the file and its chunks from the index. Response `204`.

#### `POST /documents/reindex/`
Rebuilds the index from all documents (takes ~5 minutes). Files copied into the server's
`documents/` folder by hand are registered automatically. No body. Response `202`:
```json
{ "status": "processing", "documents": 7 }
```
Poll `/health/` until `reindexing` is `false`. A second call while one is running → `409 conflict`.

---

### 3.7 Analytics (admin dashboard)

#### `GET /analytics/summary/?days=30`
`days`: 1–365, default 30.
```json
{
  "period_days": 30,
  "total_questions": 412,
  "active_users": 57,
  "refusal_rate": 0.14,
  "avg_latency_ms": 3850,
  "feedback": { "up": 96, "down": 11 },
  "questions_per_day": [
    { "date": "2026-11-05", "count": 18 },
    { "date": "2026-11-06", "count": 25 }
  ]
}
```
`refusal_rate` is a fraction (0.14 = 14%).

#### `GET /analytics/top-questions/?days=30&limit=10`
`limit`: 1–50, default 10. Similar questions are grouped after normalising the text.
```json
{
  "results": [
    { "question": "كيف أسجل المواد؟", "count": 37, "refused_count": 0 },
    { "question": "متى آخر موعد للانسحاب؟", "count": 22, "refused_count": 1 }
  ]
}
```
A high `refused_count` means the documents are missing that information — useful to show the admin.

---

## 4. UI requirements from the hackathon guide

- **Arabic first, RTL:** set `<html lang="ar" dir="rtl">`. For message bubbles use `dir="auto"` so mixed
  Arabic/English text (document names, course codes) renders correctly.
- Use a font with good Arabic support (e.g. *IBM Plex Sans Arabic*, *Cairo*, *Tajawal*).
- Every answer must visibly show its sources; refusals must look clearly different from answers.
- Pages: Login/Register · Chat (with conversation sidebar) · Admin: Documents · Admin: Dashboard.
- Must work on mobile width.

## 5. Changelog
| Version | Date | Change |
|---|---|---|
| v1 | 2026-11-07 | First version |
| v1.1 | 2026-11-07 | Implemented. Source gains `title`; `page` is `null` for .txt; health gains `reindexing`; reindex may return `409`; questions without letters are rejected (`400`) |
