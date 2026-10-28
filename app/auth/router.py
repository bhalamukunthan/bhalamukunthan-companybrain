import logging
import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from ..database import get_db
from .deps import User, get_current_user
from .schemas import Login, RegisterCompany
from .security import DUMMY_HASH, create_token, hash_password, verify_password

log = logging.getLogger("companybrain.auth")
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register-company", status_code=201)
def register_company(body: RegisterCompany, conn=Depends(get_db)):
    """Creates a new company (tenant) and its first Admin. Roles can never be self-chosen."""
    try:
        cur = conn.execute("INSERT INTO companies (name) VALUES (?)", (body.company_name.strip(),))
        company_id = cur.lastrowid
        cur = conn.execute(
            "INSERT INTO users (company_id, username, password_hash, role) VALUES (?, ?, ?, 'admin')",
            (company_id, body.username.strip(), hash_password(body.password)),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback()
        raise HTTPException(status_code=409, detail="Company name already exists")
    log.info("company registered id=%s", company_id)
    return {"access_token": create_token(cur.lastrowid, company_id), "token_type": "bearer"}


@router.post("/login")
def login(body: Login, conn=Depends(get_db)):
    row = conn.execute(
        "SELECT u.id, u.company_id, u.password_hash FROM users u JOIN companies c ON c.id = u.company_id "
        "WHERE c.name = ? AND u.username = ?", (body.company_name.strip(), body.username.strip())
    ).fetchone()
    # Always run a hash check so response time does not reveal whether the user exists.
    ok = verify_password(body.password, row["password_hash"] if row else DUMMY_HASH)
    if not row or not ok:
        log.warning("failed login")
        raise HTTPException(status_code=401, detail="Invalid company, username or password")
    return {"access_token": create_token(row["id"], row["company_id"]), "token_type": "bearer"}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "username": user.username, "role": user.role, "company": user.company_name}
