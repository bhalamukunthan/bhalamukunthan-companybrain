"""Admin-only user management. Every endpoint requires role 'admin' and stays inside the admin's company."""
import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from .auth.deps import User, require_roles
from .auth.schemas import CreateUser
from .auth.security import hash_password
from .database import get_db
from .permissions import ROLES

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/users", status_code=201)
def create_user(body: CreateUser, admin: User = Depends(require_roles("admin")), conn=Depends(get_db)):
    role = body.role.strip().lower()
    if role not in ROLES:
        raise HTTPException(status_code=422, detail=f"Role must be one of {', '.join(ROLES)}")
    try:
        cur = conn.execute(
            "INSERT INTO users (company_id, username, password_hash, role) VALUES (?, ?, ?, ?)",
            (admin.company_id, body.username.strip(), hash_password(body.password), role),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Username already exists in this company")
    return {"id": cur.lastrowid, "username": body.username.strip(), "role": role}


@router.get("/users")
def list_users(admin: User = Depends(require_roles("admin")), conn=Depends(get_db)):
    rows = conn.execute(
        "SELECT id, username, role, created_at FROM users WHERE company_id = ? ORDER BY id", (admin.company_id,)
    ).fetchall()
    return [dict(r) for r in rows]


@router.delete("/users/{user_id}")
def delete_user(user_id: int, admin: User = Depends(require_roles("admin")), conn=Depends(get_db)):
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot delete yourself")
    cur = conn.execute("DELETE FROM users WHERE id = ? AND company_id = ?", (user_id, admin.company_id))
    conn.commit()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"deleted": user_id}
