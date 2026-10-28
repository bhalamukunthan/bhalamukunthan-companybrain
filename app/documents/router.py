import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..auth.deps import User, get_current_user
from ..config import settings
from ..database import get_db
from ..permissions import can_delete, can_upload, can_view
from .service import IngestError, ingest_document, remove_document

log = logging.getLogger("companybrain.documents")
router = APIRouter(prefix="/documents", tags=["documents"])


def _get_visible_doc(conn, user: User, doc_id: str):
    """Returns the row, or 404 if missing OR not visible (so existence is never leaked)."""
    doc = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    if doc is None or not can_view(user, doc):
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.post("", status_code=201)
def upload(file: UploadFile = File(...), title: str = Form(""), department: str = Form("General"),
           allowed_roles: str = Form("employee,hr,engineering"),
           user: User = Depends(get_current_user), conn=Depends(get_db)):
    if not can_upload(user):
        raise HTTPException(status_code=403, detail="Your role cannot upload documents")
    data = file.file.read(settings.max_upload_bytes + 1)
    try:
        result = ingest_document(conn, user.company_id, user.id, file.filename, data,
                                 title, department, allowed_roles.split(","))
    except IngestError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    log.info("document uploaded id=%s chunks=%s by user=%s", result["id"], result["num_chunks"], user.id)
    return result


@router.get("")
def list_documents(user: User = Depends(get_current_user), conn=Depends(get_db)):
    rows = conn.execute(
        "SELECT d.*, u.username AS uploader FROM documents d LEFT JOIN users u ON u.id = d.uploader_id "
        "WHERE d.company_id = ? ORDER BY d.uploaded_at DESC", (user.company_id,)
    ).fetchall()
    return [
        {"id": r["id"], "title": r["title"], "filename": r["filename"], "department": r["department"],
         "allowed_roles": r["allowed_roles"].split(","), "uploader": r["uploader"],
         "uploaded_at": r["uploaded_at"], "num_chunks": r["num_chunks"]}
        for r in rows if can_view(user, r)
    ]


@router.get("/{doc_id}/download")
def download(doc_id: str, user: User = Depends(get_current_user), conn=Depends(get_db)):
    doc = _get_visible_doc(conn, user, doc_id)
    path = Path(doc["stored_path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="File missing on server")
    return FileResponse(path, filename=doc["filename"])


@router.delete("/{doc_id}")
def delete(doc_id: str, user: User = Depends(get_current_user), conn=Depends(get_db)):
    doc = _get_visible_doc(conn, user, doc_id)
    if not can_delete(user, doc):
        raise HTTPException(status_code=403, detail="You cannot delete this document")
    remove_document(conn, doc)
    log.info("document deleted id=%s by user=%s", doc_id, user.id)
    return {"deleted": doc_id}
