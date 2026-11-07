"""Generation layer: build the prompt and ask the LLM."""
import os
from dotenv import load_dotenv
from google import genai
from retrieval import retrieve

load_dotenv()  # reads GEMINI_API_KEY from the .env file
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
REFUSAL = "I don't know based on the available documents. / لا أعرف بناءً على المستندات المتوفرة."

_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


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
    response = _client.models.generate_content(
        model=MODEL, contents=build_prompt(question, hits)
    )
    sources = sorted({f"{h['source']} (page {h['page']})" for h in hits})
    return response.text, sources


if __name__ == "__main__":
    for q in ["What GPA do I need to graduate?", "شو المعدل اللي بدي إياه عشان أتخرج؟",
              "Who won the 2022 World Cup?"]:
        answer, sources = ask(q)
        print("\nQ:", q)
        print("A:", answer)
        print("Sources:", sources)