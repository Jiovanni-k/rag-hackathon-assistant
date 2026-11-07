"""Quick Gradio demo of the RAG core (backup for the Django site)."""
import shutil

import gradio as gr

from rag import config
from rag.application.ask_service import ask
from rag.application.ingest_service import build_index
from rag.infrastructure import vector_store

# Lets each message flow right-to-left for Arabic and left-to-right for English
CSS = ".message, textarea { unicode-bidi: plaintext; text-align: start; }"


def respond(message, history):
    turns = [{"role": m["role"], "content": m["content"]} for m in history
             if isinstance(m, dict) and isinstance(m.get("content"), str)]
    answer = ask(message, turns)
    text = answer.text
    if answer.sources:
        text += "\n\n**المصادر:** " + " · ".join(s.label() for s in answer.sources)
    return text


def upload(files):
    """Admin feature: add new documents and rebuild the index."""
    for f in files or []:
        shutil.copy(f, config.DOCUMENTS_DIR)
    return f"Indexed {build_index()} chunks."


with gr.Blocks(title="المرشد الأكاديمي الذكي", css=CSS) as demo:
    gr.Markdown("# المرشد الأكاديمي الذكي\nاسأل بالعربية أو الإنجليزية. كل إجابة تذكر مصدرها.")
    gr.ChatInterface(respond, type="messages")
    with gr.Accordion("Admin: add documents", open=False):
        files = gr.File(file_count="multiple", file_types=[".pdf", ".txt"])
        status = gr.Markdown()
        gr.Button("Upload and re-index").click(upload, files, status)


if __name__ == "__main__":
    if vector_store.count() == 0:   # first run: build the index
        build_index()
    demo.launch()
