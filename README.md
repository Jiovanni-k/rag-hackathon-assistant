# [Team Name] — RAG Assistant

A RAG (Retrieval-Augmented Generation) assistant that answers questions in Arabic and English using only trusted documents, cites its sources, and refuses when the answer is not in the documents.

## Problem
[One or two sentences: who has the problem and why it matters.]

## Architecture

```
documents/ → ingest.py → retrieval.py → generation.py → app.py
 (PDF/TXT)    clean +      embeddings +     prompt +        web
              chunk        hybrid search +   Gemini LLM      interface
                           reranking
```

- **ingest.py** — loads PDF/TXT files, cleans text, splits into 500-character chunks with 100 overlap, keeps source and page number.
- **retrieval.py** — multilingual embeddings (Arabic-friendly) stored in ChromaDB, hybrid search (meaning + BM25 keywords), cross-encoder reranking, and a distance threshold that refuses out-of-scope questions.
- **generation.py** — builds a grounded prompt and calls the LLM; answers with citations.
- **app.py** — Gradio web page with chat, sources, Arabic/English support, and an admin document upload.
- **evaluate.py** — test set measuring Recall@k and refusal accuracy.

## Setup

1. Create a virtual environment and install requirements:
   ```
   python -m venv .venv
   .venv\Scripts\activate          (Windows)
   source .venv/bin/activate       (Mac/Linux)
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and add your Gemini API key (free at aistudio.google.com/apikey).
3. Put your documents (PDF or TXT) in the `documents/` folder. Sample data is included.

## Run

- Web app: `python app.py`, then open the link it prints.
- Evaluation: `python evaluate.py`

The first run downloads the embedding and reranking models (about 1 GB).

## Evaluation results
| Setting | Recall@k | Refusal |
|---|---|---|
| k=1 | [fill in] | [fill in] |
| k=3 | [fill in] | [fill in] |

**What we improved:** [e.g. "Question X failed with k=1, so we used k=3."]

## AI usage disclosure
We used AI assistants (Claude, Anthropic) to explain RAG concepts and to help write and review the code. The team understands and can explain every part. The base structure follows the BinX Tech RAG Bootcamp lecture code, extended with PDF support, multilingual embeddings, hybrid search, reranking, and a web interface.

## Team
- [Name] — Technical development
- [Name] — Research & business
- [Name] — Presentation & demo