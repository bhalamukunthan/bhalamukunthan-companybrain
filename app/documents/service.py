"""Ingestion: validate -> parse -> chunk -> embed+index -> save record. Cleans up if anything fails."""
import uuid
from pathlib import Path

from ..config import settings
from ..permissions import normalize_roles
from ..retrieval import store
from .chunker import chunk_text
from .parser import ParseError, extract_pages


class IngestError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def ingest_document(conn, company_id: int, uploader_id: int | None, filename: str, data: bytes,
                    title: str, department: str, allowed_roles: list[str]) -> dict:
    safe_name = Path(filename or "").name[:200]
    if not safe_name:
        raise IngestError("Missing file name")
    if len(data) > settings.max_upload_bytes:
        raise IngestError(f"File is larger than {settings.max_upload_bytes // (1024 * 1024)} MB", 413)
    try:
        roles = normalize_roles(allowed_roles)
        pages = extract_pages(safe_name, data)
    except (ValueError, ParseError) as e:
        raise IngestError(str(e))

    title = (title or "").strip()[:200] or Path(safe_name).stem
    department = (department or "General").strip()[:100] or "General"
    chunks = [(page or 0, c) for page, text in pages for c in chunk_text(text)]

    doc_id = uuid.uuid4().hex
    stored_path = settings.upload_dir / f"{doc_id}{Path(safe_name).suffix.lower()}"
    try:
        store.add_chunks(doc_id, company_id, title, safe_name, department, roles, chunks)
        stored_path.write_bytes(data)
        conn.execute(
            "INSERT INTO documents (id, company_id, title, filename, department, allowed_roles, "
            "uploader_id, stored_path, num_chunks) VALUES (?,?,?,?,?,?,?,?,?)",
            (doc_id, company_id, title, safe_name, department, ",".join(roles),
             uploader_id, str(stored_path), len(chunks)),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        store.delete_document(doc_id)
        stored_path.unlink(missing_ok=True)
        raise
    return {"id": doc_id, "title": title, "filename": safe_name, "department": department,
            "allowed_roles": roles, "num_chunks": len(chunks)}


def remove_document(conn, doc) -> None:
    store.delete_document(doc["id"])
    Path(doc["stored_path"]).unlink(missing_ok=True)
    conn.execute("DELETE FROM documents WHERE id = ?", (doc["id"],))
    conn.commit()
