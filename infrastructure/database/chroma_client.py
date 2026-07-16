# infrastructure/database/chroma_client.py
"""
Low-level ChromaDB client wrapper with LangChain integration.
Handles connection, embeddings, and basic collection operations.
"""

import chromadb
from chromadb.config import Settings
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pathlib import Path
from typing import List, Dict, Any

from config.settings import settings


class ChromaClient:
    """
    ChromaDB client with LangChain embeddings integration.
    """

    def __init__(self):
        self.persist_dir = settings.chroma_dir / "customers"
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(anonymized_telemetry=False)
        )

        self.collection = self.client.get_or_create_collection(
            name="customers",
            metadata={"hnsw:space": "cosine"}
        )

        self.embeddings = OllamaEmbeddings(
            model=settings.embedding_model,
            base_url=settings.ollama_host
        )

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap
        )

    def get_collection(self):
        return self.collection

    def add_document(self, doc_id: str, embedding: List[float], document: str, metadata: Dict):
        self.collection.add(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[document],
            metadatas=[metadata]
        )

    def update_document(self, doc_id: str, embedding: List[float], document: str, metadata: Dict):
        self.collection.delete(ids=[doc_id])
        self.add_document(doc_id, embedding, document, metadata)

    def delete_document(self, doc_id: str):
        self.collection.delete(ids=[doc_id])

    def get_document(self, doc_id: str) -> Dict:
        result = self.collection.get(ids=[doc_id])
        if result and result["ids"]:
            return {
                "id": result["ids"][0],
                "metadata": result["metadatas"][0],
                "document": result["documents"][0] if result["documents"] else ""
            }
        return {}

    def query(self, query_embedding: List[float], n_results: int = 10) -> Dict:
        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["metadatas", "documents"]
        )

    def count(self) -> int:
        return self.collection.count()

    def get_all(self) -> Dict:
        return self.collection.get(include=["metadatas", "documents"])

    def persist(self):
        try:
            self.client.persist()
        except Exception:
            pass