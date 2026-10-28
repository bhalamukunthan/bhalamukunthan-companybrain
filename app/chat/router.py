import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth.deps import User, get_current_user
from ..config import settings
from ..database import get_db
from ..permissions import can_view
from ..retrieval import store
from .llm import ABSTAIN, LLMError, generate

log = logging.getLogger("companybrain.chat")
router = APIRouter(prefix="/chat", tags=["chat"])


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


@router.post("")
def ask(body: Question, user: User = Depends(get_current_user), conn=Depends(get_db)):
    # Layer 1: tenant + role filter inside the vector search.
    hits = store.search(body.question, user.company_id, user.role, settings.top_k)
    hits = [h for h in hits if h["distance"] <= settings.max_distance]

    # Layer 2 (defence in depth): re-check every hit against the database record.
    safe = []
    for h in hits:
        doc = conn.execute("SELECT * FROM documents WHERE id = ?", (h["doc_id"],)).fetchone()
        if doc is not None and can_view(user, doc):
            safe.append(h)

    # Never log the question text or document content (could be confidential).
    log.info("chat user=%s q_len=%s passages=%s", user.id, len(body.question), len(safe))
    if not safe:
        return {"answer": ABSTAIN, "sources": [], "abstained": True}
    try:
        answer = generate(body.question, safe)
    except LLMError as e:
        raise HTTPException(status_code=502, detail=str(e))

    seen, sources = set(), []
    for h in safe:
        key = (h["doc_id"], h["page"])
        if key not in seen:
            seen.add(key)
            sources.append({"doc_id": h["doc_id"], "title": h["title"],
                            "filename": h["filename"], "page": h["page"]})
    return {"answer": answer, "sources": sources, "abstained": answer.strip() == ABSTAIN}
