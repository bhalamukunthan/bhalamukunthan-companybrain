"""Password hashing (bcrypt) and signed login tokens (JWT)."""
import time

import bcrypt
import jwt

from ..config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


DUMMY_HASH = hash_password("dummy-password-for-timing")


def create_token(user_id: int, company_id: int) -> str:
    payload = {"sub": str(user_id), "cid": company_id,
               "exp": int(time.time()) + settings.token_minutes * 60}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
