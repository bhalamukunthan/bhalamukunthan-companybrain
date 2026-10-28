"""Who is calling? Runs on every protected endpoint (server-side)."""
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..database import get_db
from .security import decode_token

bearer = HTTPBearer(auto_error=False)


@dataclass
class User:
    id: int
    company_id: int
    company_name: str
    username: str
    role: str


def get_current_user(creds: HTTPAuthorizationCredentials = Depends(bearer), conn=Depends(get_db)) -> User:
    unauthorized = HTTPException(status_code=401, detail="Not authenticated")
    if creds is None:
        raise unauthorized
    try:
        payload = decode_token(creds.credentials)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise unauthorized
    # Role is read from the database every time, so role changes apply immediately.
    row = conn.execute(
        "SELECT u.id, u.company_id, u.username, u.role, c.name AS company_name "
        "FROM users u JOIN companies c ON c.id = u.company_id WHERE u.id = ?", (user_id,)
    ).fetchone()
    if row is None or row["company_id"] != payload.get("cid"):
        raise unauthorized
    return User(row["id"], row["company_id"], row["company_name"], row["username"], row["role"])


def require_roles(*roles: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="You do not have permission for this action")
        return user
    return checker
