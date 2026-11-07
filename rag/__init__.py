"""RAG core: plain Python, no Django imports.

Layers (each one only imports the layers below it):
    application    -> use cases: ingest documents, answer a question
    domain         -> entities and the rules about them
    infrastructure -> PDF/text loading, Arabic normalisation, Chroma, BM25, reranker, Gemini
"""
