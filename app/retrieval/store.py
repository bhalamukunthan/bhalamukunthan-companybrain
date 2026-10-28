"""ChromaDB wrapper. SECURITY: search() ALWAYS filters by tenant and role inside the query."""
import chromadb

from ..config import settings
from ..permissions import ROLES
from .embeddings import embed

_collection = None


def collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=str(settings.chroma_dir))
        _collection = client.get_or_create_collection("chunks", metadata={"hnsw:space": "cosine"})
    return _collection


def add_chunks(doc_id: str, tenant_id: int, title: str, filename: str, department: str,
               allowed_roles: list[str], chunks: list[tuple[int, str]]) -> None:
    """chunks = [(page_number (0 if none), text)]"""
    texts = [t for _, t in chunks]
    # One boolean field per role, because Chroma filters cannot search inside lists.
    role_flags = {f"allow_{r}": (r in allowed_roles) for r in ROLES}
    metadatas = [
        {"doc_id": doc_id, "tenant_id": tenant_id, "title": title, "filename": filename,
         "department": department, "page": page, **role_flags}
        for page, _ in chunks
    ]
    ids = [f"{doc_id}:{i}" for i in range(len(chunks))]
    collection().add(ids=ids, documents=texts, embeddings=embed(texts), metadatas=metadatas)


def delete_document(doc_id: str) -> None:
    collection().delete(where={"doc_id": doc_id})


def search(question: str, tenant_id: int, role: str, k: int) -> list[dict]:
    if role not in ROLES:
        return []
    where = {"$and": [{"tenant_id": tenant_id}, {f"allow_{role}": True}]}
    res = collection().query(query_embeddings=embed([question]), n_results=k, where=where,
                             include=["documents", "metadatas", "distances"])
    out = []
    for text, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        out.append({"text": text, "doc_id": meta["doc_id"], "title": meta["title"],
                    "filename": meta["filename"], "page": meta["page"] or None, "distance": dist})
    return out
