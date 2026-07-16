# application/customer_service.py
"""
High-level Customer Service - Business logic layer.
Uses injected ChromaClient and OllamaClient (no more global state or duplication).
Now upgraded with LangChain RAG chains.
"""

from typing import Optional, List, Dict, Any

from config.settings import settings
from core.models import Customer
from infrastructure.database.chroma_client import ChromaClient
from infrastructure.llm.ollama_client import OllamaClient


class CustomerService:
    """
    High-level service for customer operations (CRUD + RAG).
    """
    def __init__(self, chroma_client: ChromaClient, ollama_client: OllamaClient):
        self.chroma_client = chroma_client
        self.ollama_client = ollama_client
        self._counter = 0
        self._load_counter()

    def _load_counter(self):
        """Load highest customer ID from database"""
        try:
            results = self.chroma_client.get_all()
            if results and results.get('ids'):
                max_id = 0
                for doc_id in results['ids']:
                    if doc_id.startswith('C'):
                        try:
                            num = int(doc_id[1:])
                            max_id = max(max_id, num)
                        except ValueError:
                            pass
                self._counter = max_id
        except Exception as e:
            print(f"Warning: Could not load counter - {e}")
            self._counter = 0

    def generate_id(self) -> str:
        self._counter += 1
        return f"C{self._counter:03d}"

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using ChromaClient's built-in embeddings (reliable)"""
        try:
            if len(text) > settings.chunk_size:
                # For long text, split and average
                chunks = self.chroma_client.text_splitter.split_text(text)
                chunk_embeddings = self.chroma_client.embeddings.embed_documents(chunks)
                import numpy as np
                return np.mean(chunk_embeddings, axis=0).tolist()
            return self.chroma_client.embeddings.embed_query(text)
        except Exception as e:
            print(f"Embedding error: {e}")
            return [0.0] * 1024  # fallback


    def add_customer(self, customer: Customer) -> str:
        if not customer.customer_id or customer.customer_id == "AUTO-GEN":
            customer.customer_id = self.generate_id()

        doc_text = customer.to_text()
        embedding = self._generate_embedding(doc_text)

        if not embedding:
            embedding = [0.0] * 1024

        self.chroma_client.add_document(
            doc_id=customer.customer_id,
            embedding=embedding,
            document=doc_text,
            metadata=customer.to_dict()
        )

        # 🔥 force disk write
        self.chroma_client.persist()

        return customer.customer_id

    def update_customer(self, customer_id: str, **kwargs) -> bool:
        try:
            existing = self.chroma_client.get_document(customer_id)
            if not existing:
                return False

            meta = existing["metadata"]
            meta.update(kwargs)

            updated_customer = Customer(**meta)
            doc_text = updated_customer.to_text()
            embedding = self._generate_embedding(doc_text)

            if not embedding:
                embedding = [0.0] * 1024

            self.chroma_client.update_document(
                doc_id=customer_id,
                embedding=embedding,
                document=doc_text,
                metadata=updated_customer.to_dict()
            )
            return True
        except Exception as e:
            print(f"Update error: {e}")
            return False

    def delete_customer(self, customer_id: str) -> bool:
        try:
            self.chroma_client.delete_document(customer_id)
            return True
        except Exception as e:
            print(f"Delete error: {e}")
            return False

    def get_customer(self, customer_id: str) -> Optional[Customer]:
        try:
            result = self.chroma_client.get_document(customer_id)
            if result and result.get("metadata"):
                return Customer(**result["metadata"])
            return None
        except Exception:
            return None

    def search(self, query: str, n_results: int = 10) -> List[Customer]:
        if not query.strip():
            return self.get_all()
        try:
            query_embedding = self._generate_embedding(query)
            results = self.chroma_client.query(
                query_embedding=query_embedding,
                n_results=n_results
            )
            customers = []
            if results and results.get('metadatas'):
                for meta in results['metadatas'][0]:
                    customers.append(Customer(**meta))
            return customers
        except Exception as e:
            print(f"Search error: {e}")
            # Fallback to simple text search
            return [c for c in self.get_all() if query.lower() in c.to_text().lower()]

    def get_all(self) -> List[Customer]:
        try:
            results = self.chroma_client.get_all()
            if results and results.get('metadatas'):
                return [Customer(**meta) for meta in results['metadatas']]
            return []
        except Exception:
            return []

    def to_dataframe(self, customers: Optional[List[Customer]] = None) -> List[List]:
        data = customers or self.get_all()
        return [
            [
                c.customer_id,
                c.customer_name,
                c.customer_email,
                c.customer_phone,
                c.customer_company,
                c.customer_address,
                c.customer_notes or ""
            ]
            for c in data
        ]

    def _format_context(self, customers: List[Customer]) -> str:
        """Format customer list into RAG context string"""
        parts = []
        for c in customers:
            parts.append(
                f"Customer {c.customer_id}: {c.customer_name} ({c.customer_email}) | "
                f"Phone: {c.customer_phone} | Company: {c.customer_company} | "
                f"Address: {c.customer_address} | Notes: {c.customer_notes}"
            )
        return "\n".join(parts)

    def rag_search(self, query: str, n_results: int = 5) -> Dict[str, Any]:
        customers = self.search(query, n_results)
        context = self._format_context(customers)

        # 🔥 LangChain RAG Chain
        try:
            chain = self.ollama_client.build_rag_chain(
                system_prompt=(
                    "You are an expert business analyst. Use the provided customer context "
                    "to answer questions accurately and concisely. If the answer is not in "
                    "the context, say so clearly."
                )
            )
            answer = chain.invoke({"context": context, "question": query})
        except Exception as e:
            print(f"LangChain RAG failed: {e}")
            prompt = f"""Use the following customer context to answer the question.

Context:
{context}

Question: {query}

Answer concisely and accurately."""
            answer = self.ollama_client.call_generate(prompt)

        return {
            "query": query,
            "context": context,
            "results": customers,
            "count": len(customers),
            "answer": answer
        }

    def retrieve(self, query: str) -> str:
        """For RAG context retrieval"""
        result = self.rag_search(query)
        return result.get("answer", result["context"])