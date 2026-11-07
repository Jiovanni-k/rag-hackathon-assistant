# [Team Name] — المرشد الأكاديمي الذكي (Smart Academic Advisor)

An academic advisor for Palestinian university students. It answers questions in Arabic, including
spoken dialect, using **only** official university documents. Every answer cites its source, and it
refuses ("لا أجد هذه المعلومة…") when the documents do not contain the answer.

Built for the IEEE RAG Hackathon at Bethlehem University.

## Problem
[One or two sentences with a sourced number: who has the problem and why it matters.]

## Architecture

```
                         ┌──────────── Django REST API (apps/) ────────────┐
 Frontend  ── HTTPS ──▶  │ accounts · chat · documents · analytics         │
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
python manage.py createsuperuser  # admin account (for document upload + dashboard)
python manage.py sync_documents --reindex   # register documents/ and build the index (~5 min)
```

The first run downloads the embedding and reranking models (about 1 GB).

## Run

| What | Command |
|---|---|
| API server | `python manage.py runserver` → `http://localhost:8000/api/v1/` (see [docs/API.md](docs/API.md)) |
| Django admin | `http://localhost:8000/admin/` |
| Backup demo UI | `python app.py` (Gradio) |
| Evaluation | `python -m evaluation.run_eval` |
| API tests (offline, LLM mocked) | `python manage.py test tests` |
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
- Token authentication. Admin-only endpoints for documents and analytics. Per-user rate limit on questions.
- Uploads are limited to `.pdf`/`.txt` up to 20 MB, and file names are sanitised.

## AI usage disclosure
We used AI assistants (Claude by Anthropic, including Claude Code) to explain RAG concepts and to
help design, write, test and review the code and documentation. The team understands and can
explain every part. The base structure follows the BinX Tech RAG Bootcamp lecture code, extended
with the layered RAG core, Arabic support, the Django API and the evaluation.

## Team
- [Name] — Technical development
- [Name] — Frontend
- [Name] — Data & evaluation
- [Name] — Presentation & business plan
