"""Generation layer: build the prompt and ask the LLM."""
import os
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types
from retrieval import retrieve

load_dotenv()  # reads GEMINI_API_KEY from the .env file
# First model is preferred; the rest are fallbacks if it is overloaded (503/504) or retired (404).
# Set GEMINI_MODEL in .env to put your own choice first.
FALLBACK_MODELS = ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite"]
MODELS = list(dict.fromkeys([m for m in [os.getenv("GEMINI_MODEL")] if m] + FALLBACK_MODELS))
REFUSAL = "I don't know based on the available documents. / لا أعرف بناءً على المستندات المتوفرة."

# Bounded timeout (ms) and few retries, so a busy model fails fast instead of hanging for minutes.
_client = genai.Client(
    api_key=os.environ["GEMINI_API_KEY"],
    http_options=types.HttpOptions(timeout=60_000,
                                   retry_options=types.HttpRetryOptions(attempts=2)),
)


def generate(prompt):
    """Try each model in order; move on when one is unavailable."""
    last_error = None
    for model in MODELS:
        try:
            return _client.models.generate_content(model=model, contents=prompt)
        except errors.APIError as e:
            if e.code not in (404, 429, 500, 503, 504):
                raise                      # e.g. bad API key: don't hide it
            last_error = e
    raise last_error


def build_prompt(question, hits):
    """Augment: instructions + labelled chunks + the question."""
    context = "\n\n".join(f"[{h['source']}, page {h['page']}]\n{h['text']}" for h in hits)
    return f"""You are a helpful assistant that answers ONLY from the context below.
Rules:
- Use only the context. Never use outside knowledge.
- After each fact, cite its source in brackets, for example [handbook.pdf, page 3].
- If the answer is not in the context, reply exactly: {REFUSAL}
- If sources conflict, say so and prefer the most recent one.
- Answer in the same language as the question (Arabic or English), clearly and briefly.

Context:
{context}

Question: {question}"""


def ask(question):
    """Full RAG: retrieve, then generate. Returns (answer, sources)."""
    hits = retrieve(question)
    if not hits:                      # nothing close enough: never call the LLM
        return REFUSAL, []
    response = generate(build_prompt(question, hits))
    sources = sorted({f"{h['source']} (page {h['page']})" for h in hits})
    return response.text or REFUSAL, sources   # .text is None if the reply was blocked/empty


if __name__ == "__main__":
    for q in ["What GPA do I need to graduate?", "شو المعدل اللي بدي إياه عشان أتخرج؟",
              "Who won the 2022 World Cup?"]:
        answer, sources = ask(q)
        print("\nQ:", q)
        print("A:", answer)
        print("Sources:", sources)