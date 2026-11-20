from datetime import timedelta

import bcrypt
import jwt

from app.config import get_settings
from app.models import utcnow

# Used to burn the same CPU time when an email doesn't exist (blunts user enumeration by timing).
_DUMMY_HASH = bcrypt.hashpw(b"not-a-real-password", bcrypt.gensalt()).decode()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str | None) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), (hashed or _DUMMY_HASH).encode()) and hashed is not None
    except ValueError:
        return False


def create_access_token(user_id: str) -> str:
    s = get_settings()
    now = utcnow()
    payload = {"sub": user_id, "iat": now, "exp": now + timedelta(minutes=s.jwt_expire_minutes)}
    return jwt.encode(payload, s.jwt_secret_key, algorithm=s.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    s = get_settings()
    return jwt.decode(
        token, s.jwt_secret_key, algorithms=[s.jwt_algorithm], options={"require": ["exp", "sub"]}
    )
