"""The ONLY place that talks to ChromaDB.

Every read and delete is forced through a tenant filter (organization_id + chatbot_id), so a
route can't accidentally query across tenants.
"""
from functools import lru_cache

from langchain_chroma import Chroma
from langchain_core.documents import Document

from app.config import get_settings
from app.services.embeddings import get_embeddings


def _where(org_id: str, bot_id: str, doc_id: str | None = None) -> dict:
    if not org_id or not bot_id:
        raise ValueError("org_id and bot_id are required")
    clauses = [{"organization_id": {"$eq": org_id}}, {"chatbot_id": {"$eq": bot_id}}]
    if doc_id:
        clauses.append({"doc_id": {"$eq": doc_id}})
    return {"$and": clauses}


class TenantVectorStore:
    def __init__(self, store: Chroma):
        self._store = store

    def add_chunks(self, org_id: str, bot_id: str, doc_id: str, chunks: list[Document]) -> int:
        for c in chunks:
            c.metadata.update({"organization_id": org_id, "chatbot_id": bot_id, "doc_id": doc_id})
        if chunks:
            self._store.add_documents(chunks)
        return len(chunks)

    def search(self, org_id: str, bot_id: str, query: str, k: int = 4) -> list[Document]:
        return self._store.similarity_search(query, k=k, filter=_where(org_id, bot_id))

    def delete_document(self, org_id: str, bot_id: str, doc_id: str) -> None:
        self._store.delete(where=_where(org_id, bot_id, doc_id))

    def delete_bot(self, org_id: str, bot_id: str) -> None:
        self._store.delete(where=_where(org_id, bot_id))


@lru_cache
def get_vector_store() -> TenantVectorStore:
    s = get_settings()
    chroma = Chroma(
        collection_name="knowledge_base",
        embedding_function=get_embeddings(),
        persist_directory=s.chroma_persist_dir,
        collection_metadata={"hnsw:space": "cosine"},
    )
    return TenantVectorStore(chroma)
