"""Persistent Chroma storage and retrieval for uploaded PDF documents."""

import os
import uuid
from io import BytesIO
from typing import Any, Dict, List

import chromadb
import requests
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

import memory_engine

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_DIR = os.path.join(ROOT_DIR, "chroma_db")
COLLECTION_NAME = "pdf_documents"
EMBEDDING_MODEL = "nomic-embed-text"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
MAX_DISTANCE = 0.7


def _collection():
    os.makedirs(CHROMA_DIR, exist_ok=True)
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )


def _embeddings(texts: List[str]) -> List[List[float]]:
    base_url = memory_engine.get_setting(
        "ollama_url", "http://localhost:11434"
    ).strip().rstrip("/")
    response = requests.post(
        f"{base_url}/api/embed",
        json={"model": EMBEDDING_MODEL, "input": texts},
        timeout=90
    )
    if response.status_code == 404:
        embeddings = []
        for text in texts:
            legacy_response = requests.post(
                f"{base_url}/api/embeddings",
                json={"model": EMBEDDING_MODEL, "prompt": text},
                timeout=90
            )
            legacy_response.raise_for_status()
            embeddings.append(legacy_response.json()["embedding"])
        return embeddings

    response.raise_for_status()
    embeddings = response.json().get("embeddings")
    if not isinstance(embeddings, list) or len(embeddings) != len(texts):
        raise ValueError("Ollama returned an invalid embedding response")
    return embeddings


def store_pdf(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """Extracts every PDF page, chunks the text, and persists its vectors."""
    reader = PdfReader(BytesIO(file_bytes))
    collection = _collection()
    documents = []
    metadatas = []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        add_start_index=True
    )
    for page_number, page in enumerate(reader.pages, start=1):
        page_text = (page.extract_text() or "").strip()
        if not page_text:
            continue
        for chunk in splitter.split_text(page_text):
            if not chunk.strip():
                continue
            documents.append(chunk)
            metadatas.append({
                "filename": filename,
                "page": page_number
            })

    if not documents:
        raise ValueError("No readable text was found in the PDF.")

    vectors = _embeddings(documents)
    collection.delete(where={"filename": filename})
    collection.add(
        ids=[str(uuid.uuid4()) for _ in documents],
        documents=documents,
        metadatas=metadatas,
        embeddings=vectors
    )
    return {
        "filename": filename,
        "pages": len(reader.pages),
        "chunks_stored": len(documents),
        "storage_path": CHROMA_DIR
    }


def search_pdf_context(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Returns the closest PDF chunks above the cosine relevance threshold."""
    collection = _collection()
    if collection.count() == 0:
        return []

    query_embedding = _embeddings([query])[0]
    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(limit, collection.count()),
        include=["documents", "metadatas", "distances"]
    )

    contexts = []
    documents = (result.get("documents") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]
    for document, metadata, distance in zip(documents, metadatas, distances):
        if document and distance is not None and distance <= MAX_DISTANCE:
            filename = metadata.get("filename", "PDF")
            page = metadata.get("page", "?")
            contexts.append({
                "title": f"{filename} (Page {page})",
                "category": "PDF Document",
                "source": f"pdf:{filename}",
                "content": document,
                "relevance_score": round(1.0 - distance, 3)
            })
    return contexts
