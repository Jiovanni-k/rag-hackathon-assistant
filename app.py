"""Interface layer: a simple web page for the RAG assistant."""
import shutil
from pathlib import Path
import gradio as gr
from generation import ask
from retrieval import build_index, get_collection

DOCS = Path("documents")
# Lets each message flow right-to-left for Arabic and left-to-right for English
CSS = ".message, textarea { unicode-bidi: plaintext; text-align: start; }"


def respond(message, history):
    answer, sources = ask(message)
    if sources:
        answer += "\n\n**Sources:** " + ", ".join(sources)
    return answer


def upload(files):
    """Admin feature: add new documents and rebuild the index."""
    for f in files or []:
        shutil.copy(f, DOCS / Path(f).name)
    n = build_index()
    return f"Indexed {n} chunks."


with gr.Blocks(title="RAG Assistant", css=CSS) as demo:
    gr.Markdown("# RAG Assistant\nAsk in Arabic or English. Every answer shows its sources.")
    gr.ChatInterface(respond)
    with gr.Accordion("Admin: add documents", open=False):
        files = gr.File(file_count="multiple", file_types=[".pdf", ".txt"])
        status = gr.Markdown()
        gr.Button("Upload and re-index").click(upload, files, status)


if __name__ == "__main__":
    if get_collection().count() == 0:   # first run: build the index
        build_index()
    demo.launch()