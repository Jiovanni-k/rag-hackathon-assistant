# Latte.py — المرشد الأكاديمي الذكي (Smart Academic Advisor)

An academic advisor for Palestinian university students. It answers questions in Arabic, including
spoken dialect, using **only** official university documents. Every answer cites its source, and it
refuses ("لا أجد هذه المعلومة…") when the documents do not contain the answer.

Built by team **Latte.py** for the IEEE RAG Hackathon at Bethlehem University.

## Problem
Every semester, students need answers that are buried in long university documents: the student
handbook, the study and exam regulations, and the study plans. A first-year student does not know how
many courses she may register for, a student who failed a course worries that it blocks the next one,
and a fourth-year student wants to know exactly what is left before graduation. The information
exists, but it is spread across documents written in formal Arabic (or English), while students ask
in their own dialect. Academic offices spend a lot of time answering the same questions, and a wrong
answer can cost a student credit hours, an extra semester or an academic warning.

To confirm the problem, we ran a short survey among students. The results are presented in our
business plan.

## What it can do
- Answer questions in Arabic (formal or dialect) and English from the university documents only.
- Cite every fact: document, page or section, with the retrieved text one click away.
- Refuse clearly when the documents do not contain the answer, and point the student to the
  Admissions & Registration office. Refuse politely when a request is not academic.
- Understand follow-up questions in the same conversation («وإذا كان معدلي أعلى؟»).
- Read study-plan tables: course codes, credit hours, prerequisites, semester-by-semester plans.
- Web app with an Arabic right-to-left layout and an English toggle, login, saved conversations,
  👍/👎 feedback, a staff page to upload documents and re-index, an analytics dashboard, and the
  Django admin.

## Architecture

```
                         ┌──────── Web UI (apps/web): templates + CSS + JS ─┐
 Browser   ───────────▶  │ login · chat · staff documents · staff analytics │
                         └──────────────────────┬──────────────────────────┘
                                                │ fetch /api/v1 (session + CSRF)
                         ┌──────────── Django REST API (apps/) ────────────┐
 Other clients (Token) ▶ │ accounts · chat · documents · analytics         │
                         └──────────────────────┬──────────────────────────┘
                                                │ calls
                         ┌──────────── RAG core (rag/, no Django) ─────────┐
                         │ application:   ask_service, ingest_service      │
                         │ domain:        Chunk, Hit, Source, Answer       │
                         │ infrastructure: loaders · chunker · arabic ·    │
                         │   vector_store (Chroma) · keyword_index (BM25) ·│
                         │   reranker · llm (Gemini)                       │
                         └─────────────────────────────────────────────────┘
```

Each layer only calls the layer below it. The RAG core has no Django code, so the evaluation script
and the Gradio fallback demo (`app.py`) use it directly.

### Technology choices
| Part | Choice | Why |
|---|---|---|
| Embeddings | `intfloat/multilingual-e5-small` | Arabic (incl. dialect) and English in one vector space; small enough for a laptop CPU; free and local; recommended in the hackathon guide |
| Vector store | ChromaDB (on disk, cosine distance) | No separate server; stores file, title, section and page with every chunk for citations; can replace one document's chunks on upload or delete |
| Keyword search | BM25 (`rank-bm25`) on normalised Arabic | Catches exact course codes and numbers that embeddings blur |
| Reranker | `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` | Multilingual; reads question and chunk together, much more precise than vectors alone |
| LLM | Google Gemini (`gemini-3.5-flash`, with fallbacks) | Free tier; strong Arabic; the fast `flash-lite` model handles the query-rewrite step |
| PDF reading | PyMuPDF | Keeps Arabic word order much better than pypdf; detects tables |
| Web | Django 6 + Django REST Framework, templates, plain CSS, vanilla JS | One project, no npm or build step; runs with the standard Django commands |
| Database | SQLite (PostgreSQL if `DATABASE_URL` is set) | Users, conversations, feedback and document records |

### How a question is answered (`rag/application/ask_service.py`)
1. **Rewrite** (one fast LLM call): classify the question (academic, greeting or out of scope),
   turn a follow-up into a standalone question using the conversation history, and translate it to
   English.
2. **Retrieve** (`retrieval_service.py`): vector search and BM25 keyword search with both the Arabic
   and English versions (8 candidates each), merged, then reranked; the best 6 chunks are kept.
   Searching in both languages lets dialect Arabic questions match English documents.
3. **Refuse early** if even the closest chunk is too far away (cosine distance above 0.20), without
   calling the LLM.
4. **Generate**: strict prompt (only the excerpts, cite `[n]` after every fact, simple formal Arabic,
   name the university, prefer the newest document version, steps or tables when useful, otherwise
   reply `NOT_FOUND`, which becomes the refusal message).
5. **Sources**: only the excerpts the answer actually cites are returned as sources, and the `[n]`
   markers are renumbered so that `[1]` is the first source card, `[2]` the second, and so on.

### How documents are prepared (`rag/infrastructure/`)
- **PDF** via PyMuPDF. Tables become one line per row, so a row is never split. Section headings
  ("11. WITHDRAWAL", "المادة (14)") and running page headers are tracked for every line.
- **TXT** with `# title` and `## section` lines. University study-plan web pages are converted to
  this format by `scripts/plan_to_text.py`: one self-contained line per course with hours and
  prerequisites (codes resolved to course names).
- **Arabic normalisation**: diacritics, tatweel, Arabic-Indic digits and PDF presentation forms are
  cleaned. For keyword search, hamza/alef forms, ة/ه and ى/ي are also folded.
- **Chunking**: about 900 characters, never crossing a section. Every chunk starts with
  `title | section`, so it always says which university and section it comes from.
- `documents/metadata.json` gives PDFs a readable title (including the university name).

### Web frontend (`apps/web/`)
Theme: **the campus cat** 🐾, a friendly senior student who knows every rule and always shows the source.
- **Django templates + plain CSS + vanilla JavaScript.** Templates are in `apps/web/templates/web/`,
  CSS and JS in `apps/web/static/web/`.
- Pages are thin shells. All data comes from the same REST API (`/api/v1`) that other clients use,
  through `fetch` with the session cookie and an `X-CSRFToken` header on every POST/PATCH/DELETE.
- **Chat:** Arabic first (RTL) with an English toggle (LTR); `dir="auto"` handles mixed Arabic/English
  text. Dialect suggestion chips, markdown answers (tables, numbered steps), source cards with a
  collapsible snippet, an amber refusal box, 👍/👎 feedback, and saved conversations that can be
  reopened, renamed and deleted. Follow-up questions work because each question is sent with its
  `conversation_id`, and the server adds the earlier turns. Loading indicator, and friendly errors
  for network problems, rate limits and an unavailable (or out-of-quota) LLM.
- **Staff pages:** document upload with background indexing, delete, full re-index and index status;
  analytics with question count, refusal rate, average answer time, feedback, questions per day and
  most-asked questions. The Django admin (`/admin/`) manages users and data.
- **JavaScript files:** `i18n.js` (UI strings, RTL/LTR), `api.js` (fetch, CSRF, friendly errors),
  `markdown.js` (a safe renderer: everything is escaped first), `chat.js`, `staff_documents.js`,
  `staff_analytics.js`.
- The product name is set in one place: `PRODUCT_NAME` / `PRODUCT_NAME_EN` in `.env`.
- The AI models are loaded in the background when the server starts, so the first question is not
  slowed down by model loading.
- Works on phones (the sidebar becomes a slide-in drawer). The Tajawal font comes from Google Fonts,
  with system fonts as an offline fallback.

The REST API is documented in [docs/API.md](docs/API.md).

### Project structure
```
rag/            RAG core (plain Python): application/, domain/, infrastructure/, config.py
apps/           Django apps: accounts, chat, documents, analytics, web (templates, CSS, JS), core
config/         Django settings and URLs
documents/      Indexed university documents, metadata.json (titles) and SOURCES.md
test_docs_ar/   Extra Arabic PDFs for testing (not indexed)
evaluation/     Test questions, evaluation script and latest results
scripts/        plan_to_text.py: study-plan web page → indexable text
tests/          Automated API and web tests
docs/           API reference
app.py          Gradio fallback demo
```

## Setup

Requirements: Python 3.12 or newer (developed and tested with Python 3.14 on Windows), about 2 GB of
free RAM for the AI models, an internet connection (the answers come from the Gemini API), and a free
Gemini API key from https://aistudio.google.com/apikey.

```bash
git clone https://github.com/Jiovanni-k/qitta-academic-advisor.git
cd qitta-academic-advisor
python -m venv .venv
.venv\Scripts\activate            # Windows   (Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env            # Mac/Linux: cp .env.example .env — then put your GEMINI_API_KEY in .env
python manage.py migrate
python manage.py create_demo_accounts       # demo student + demo admin (see below)
python manage.py sync_documents --reindex   # register documents/ and build the search index (~5 min)
python manage.py runserver                  # open http://localhost:8000
```

The first run downloads the embedding and reranking models (about 1 GB). After the server starts,
wait about 30 seconds for the models to load before asking the first question.

### Demo accounts
| Role | Username | Password | Can use |
|---|---|---|---|
| Student | `student` | `student-demo-2026` | Chat, saved conversations, feedback |
| Admin (staff) | `admin` | `admin-demo-2026` | Everything above, plus Documents, Analytics and the Django admin |

These are demo accounts with no real personal data. Override the passwords with
`DEMO_STUDENT_PASSWORD` / `DEMO_ADMIN_PASSWORD` in `.env` (then run `create_demo_accounts` again), and
set `SHOW_DEMO_ACCOUNTS=false` to hide them from the login page.

> **On a public server**, set `SHOW_DEMO_ACCOUNTS=false` and change both passwords (or skip
> `create_demo_accounts`). The admin account can upload and delete documents.

### Deployment
The app runs **locally** (`python manage.py runserver`) and was demonstrated to the judges on our
laptop. It is not deployed to a public server.

## Run

| What | Command |
|---|---|
| **Web app** | `python manage.py runserver` → http://localhost:8000 |
| REST API | http://localhost:8000/api/v1/ (see [docs/API.md](docs/API.md)) |
| Django admin | http://localhost:8000/admin/ |
| Fallback demo UI | `python app.py` (Gradio) |
| Evaluation | `python -m evaluation.run_eval` |
| Automated tests (24 tests, offline, LLM mocked) | `python manage.py test tests` |
| Rebuild the search index only | `python -m rag.application.ingest_service` |
| Add a study plan from a web page | `python scripts/plan_to_text.py URL --university "..." --program "..." --out documents/X.txt` |

## Evaluation results

17 questions covering the 7 question types from the hackathon guide, run end to end (rewrite,
retrieval, answer) on the documents in `documents/` (`evaluation/test_set.json`; full output with
every answer in `evaluation/results/latest.json`):

| Type | Passed |
|---|---|
| Direct | 3/3 |
| Spoken dialect | 2/2 |
| Tables / study plans | 5/5 |
| Multiple documents | 0/1 |
| Follow-up | 1/2 |
| Not in documents (must refuse) | 2/2 |
| Out of scope (must refuse) | 2/2 |
| **Total** | **15/17** |

Each question checks that the right passage was retrieved, that the answer contains the expected
facts (e.g. "139" credit hours), and that out-of-scope or missing information is refused.

**Why two questions fail:** the Bethlehem University rule "minimum of 60 credits at Bethlehem
University" is printed under a long program table in the PDF, so its chunk is mostly table and is
ranked too low.

**What we improved, measured with this set:**
| Change | Effect |
|---|---|
| Translating the question to English before search | Arabic questions against the English catalog: about 2.5/7 → 4.5/7 found |
| PyMuPDF instead of pypdf, section-aware chunks | Graduation GPA rule and the Accounting credit table became retrievable |
| Refusal cutoff calibrated on real distances (0.8 → 0.20) | Off-topic questions are now refused (before: answered) |
| Reranking fewer candidates, fast model for rewriting, skip overloaded Gemini models | Average answer time 24 s → 13 s |

## Data
All documents and their source URLs are listed in [documents/SOURCES.md](documents/SOURCES.md):
public documents from Bethlehem University (catalog, grading rules, exam proctoring rules),
An-Najah National University (Law and Medicine study plans) and Palestine Technical University –
Kadoorie (Computer Science study plan and semester-by-semester advising plan). No personal student
data is used. No model is trained or fine-tuned: this is RAG.

New documents can be added by an admin on the Documents page, or by copying them into `documents/`
and running `python manage.py sync_documents --reindex`.

## Security
- No secrets in code: the Gemini API key and the Django secret key come from `.env`
  (see `.env.example`), which is git-ignored.
- The API key never reaches the browser: the browser only talks to our Django server.
- Session login for the web UI, with CSRF protection on every POST/PATCH/DELETE (logout is POST only).
  Token authentication for other API clients. Admin-only pages and endpoints for documents and
  analytics. Per-user rate limit on questions (20 per minute) and per-IP rate limit on API
  login/register (10 per minute).
- With `DJANGO_DEBUG=false` the server refuses to start without a real `DJANGO_SECRET_KEY`, and
  session/CSRF cookies are HTTPS-only.
- The answer markdown is escaped before rendering, so documents cannot inject HTML or scripts.
- Uploads are limited to `.pdf`/`.txt` up to 20 MB, and file names are sanitised.

## AI usage disclosure
We built this project with **Claude Code** (Anthropic's AI coding assistant). Under our direction,
Claude Code generated most of the code and documentation: the layered RAG core (document loading,
Arabic normalisation, chunking, hybrid search, reranking, prompts), the evaluation set and script,
the study-plan converter, the Django REST API, the web frontend (`apps/web/`), the automated tests,
the API documentation and this README. It also helped research public university documents and
diagnose problems (Arabic PDF extraction, slow responses, refusal threshold). We chose the features
and the theme, reviewed and tested the results, and understand and can explain every part. The
starting point was the BinX Tech RAG Bootcamp lecture code. The app itself uses Google Gemini to
generate answers.

## Team — Latte.py
- Jiovanni Kitlo
- Lour Qumsiyeh
- Rama Jboor
