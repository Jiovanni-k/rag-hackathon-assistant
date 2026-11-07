# [Team Name] — المرشد الأكاديمي الذكي (Smart Academic Advisor)

An academic advisor for Palestinian university students. It answers questions in Arabic, including
spoken dialect, using **only** official university documents. Every answer cites its source, and it
refuses ("لا أجد هذه المعلومة…") when the documents do not contain the answer.

Built for the IEEE RAG Hackathon at Bethlehem University.

## Problem
[One or two sentences with a sourced number: who has the problem and why it matters.]

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

Each layer only calls the layer below it. The RAG core has no Django code, so the evaluation and
the Gradio demo use it directly.

### Frontend (`apps/web/`)
Theme: **the campus cat** 🐾, a friendly senior student who knows every rule and always shows the source.
- **Django templates + plain CSS + vanilla JavaScript.** No npm and no build step: it runs with the
  standard Django commands. Templates are in `apps/web/templates/web/`, and CSS/JS in `apps/web/static/web/`.
- Pages are thin shells. All data comes from the same REST API (`/api/v1`) that other clients use,
  through `fetch` with the session cookie and an `X-CSRFToken` header on every POST/PATCH/DELETE.
- **Chat:** Arabic first (RTL) with an English toggle (LTR); `dir="auto"` handles mixed Arabic/English
  text. Dialect suggestion chips, markdown answers (tables, numbered steps), source cards with a
  collapsible snippet, an amber refusal box (pointing to the Admissions & Registration office), and
  👍/👎 feedback. Saved conversations can be reopened, renamed and deleted. Follow-up questions work
  because each question is sent with its `conversation_id`, and the server adds the earlier turns.
  Loading indicator, and friendly errors for network problems, rate limits and an unavailable
  (or out-of-quota) LLM.
- **Staff pages:** document upload with background indexing, delete, full re-index and index status;
  analytics with question count, refusal rate, average answer time, feedback, questions per day and
  most-asked questions. The Django admin (`/admin/`) manages users and data.
- **Small pieces:** `i18n.js` (UI strings and RTL/LTR), `api.js` (fetch, CSRF and friendly errors),
  `markdown.js` (a safe renderer: everything is escaped first), `chat.js`, `staff_documents.js`,
  `staff_analytics.js`.
- The product name is set in one place: `PRODUCT_NAME` / `PRODUCT_NAME_EN` in `.env`
  (defaults in `config/settings.py`).
- The AI models are loaded in the background when the server starts, so the first question is not slowed down.
- Works on phones (the sidebar becomes a slide-in drawer). The Tajawal font comes from Google Fonts,
  with system fonts as an offline fallback.

### How a question is answered (`rag/application/ask_service.py`)
1. **Rewrite** (one fast LLM call): classify the question (academic, greeting or out of scope),
   turn a follow-up into a standalone question using the chat history, and translate it to English.
2. **Retrieve** (`retrieval_service.py`): vector search (multilingual-e5) and BM25 keyword search
   with both the Arabic and English versions, merged, then reranked by a multilingual cross-encoder.
   Searching in both languages lets dialect Arabic questions match English documents.
3. **Refuse early** if the closest chunk is too far away (`MAX_DIST`), without calling the LLM.
4. **Generate**: strict prompt (only the excerpts, cite `[n]` after every fact, simple formal Arabic,
   name the university, prefer the newest version, steps or tables when useful, otherwise `NOT_FOUND`).
5. **Sources**: only the excerpts the answer actually cites are returned as sources.

### How documents are prepared (`rag/infrastructure/`)
- **PDF** via PyMuPDF, which keeps Arabic word order much better than pypdf. Tables become one line
  per row. Section headings ("11. WITHDRAWAL", "المادة (14)") and running page headers are tracked.
- **TXT** with `# title` and `## section` lines. University study-plan web pages are converted to
  this format by `scripts/plan_to_text.py`, one self-contained line per course with hours and
  prerequisites (codes resolved to names).
- **Arabic normalisation**: diacritics, tatweel, Arabic-Indic digits and PDF presentation forms are
  cleaned. For keyword search, hamza/alef forms, ة/ه and ى/ي are also folded.
- **Chunking** never crosses a section. Every chunk starts with `title | section`, so it always says
  which university and section it comes from.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows   (Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env            # then put your GEMINI_API_KEY in .env
python manage.py migrate
python manage.py create_demo_accounts       # demo student + demo admin (see below)
python manage.py sync_documents --reindex   # register documents/ and build the index (~5 min)
python manage.py runserver                  # open http://localhost:8000
```

The first run downloads the embedding and reranking models (about 1 GB).

### Demo accounts
| Role | Username | Password | Can use |
|---|---|---|---|
| Student | `student` | `student-demo-2026` | Chat, saved conversations, feedback |
| Admin (staff) | `admin` | `admin-demo-2026` | Everything above, plus Documents, Analytics and the Django admin |

These are demo accounts with no real personal data. Override the passwords with
`DEMO_STUDENT_PASSWORD` / `DEMO_ADMIN_PASSWORD` in `.env`, and set `SHOW_DEMO_ACCOUNTS=false` to hide
them from the login page.

## Run

| What | Command |
|---|---|
| **Web app** | `python manage.py runserver` → `http://localhost:8000` |
| API | `http://localhost:8000/api/v1/` (see [docs/API.md](docs/API.md)) |
| Django admin | `http://localhost:8000/admin/` |
| Backup demo UI | `python app.py` (Gradio; kept as a fallback) |
| Evaluation | `python -m evaluation.run_eval` |
| API + web tests (offline, LLM mocked) | `python manage.py test tests` |
| Production static files | `DJANGO_DEBUG=false python manage.py collectstatic` |
| Add a study plan from a web page | `python scripts/plan_to_text.py URL --university "..." --program "..." --out documents/X.txt` |

## Evaluation results

17 questions covering the 7 question types from the hackathon guide
(`evaluation/test_set.json`, full output in `evaluation/results/latest.json`):

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

**Why two questions fail:** the Bethlehem University rule "minimum of 60 credits at Bethlehem
University" is printed under a long program table in the PDF, so its chunk is mostly table and is
ranked too low.

**What we improved, measured with this set:**
| Change | Effect |
|---|---|
| Translating the question to English before search | Arabic questions against the English catalog: about 2.5/7 → 4.5/7 found |
| PyMuPDF instead of pypdf, section-aware chunks | Graduation GPA rule and the Accounting credit table became retrievable |
| Refusal cutoff calibrated on real distances (0.8 → 0.20) | Off-topic questions are now refused (before: answered) |
| Reranking fewer candidates, fast model for rewriting, skip overloaded Gemini models | Average latency 24 s → 13 s |

## Data
All documents and their source URLs are listed in [documents/SOURCES.md](documents/SOURCES.md).
They are public documents from Bethlehem University, An-Najah National University and Palestine
Technical University – Kadoorie. No personal student data is used. No model is fine-tuned: this is RAG.

## Security
- No secrets in code: the API key and Django secret come from `.env` (see `.env.example`), which is git-ignored.
- Session login for the web UI, with CSRF protection on every POST/PATCH/DELETE (logout is POST
  only). Token authentication for other clients. Admin-only pages and endpoints for documents and
  analytics. Per-user rate limit on questions.
- The API key never reaches the browser: the browser only talks to our Django server.
- The answer markdown is escaped before rendering, so documents cannot inject HTML or scripts into the page.
- Uploads are limited to `.pdf`/`.txt` up to 20 MB, and file names are sanitised.

## AI usage disclosure
We used AI assistants (Claude by Anthropic, including Claude Code) to explain RAG concepts and to
help design, write, test and review the code and documentation. **The web frontend (`apps/web/`:
templates, CSS, JavaScript and its tests) was generated by Claude Code** from our theme and feature
brief, and reviewed and tested by the team. The team understands and can explain every part. The
base structure follows the BinX Tech RAG Bootcamp lecture code, extended with the layered RAG core,
Arabic support, the Django API, the web UI and the evaluation.

## Team
- [Name] — Technical development
- [Name] — Frontend
- [Name] — Data & evaluation
- [Name] — Presentation & business plan
