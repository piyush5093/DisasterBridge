"""
auth.py — JWT-based authentication helpers for Disaster Bridge.

Design decisions:
- Tokens are signed HS256 JWTs with a 8-hour expiry.
- Passwords are bcrypt-hashed via passlib (work factor 12).
- get_current_commander() is a FastAPI dependency injected into protected routes.
- The SECRET_KEY must be changed in production — it is intentionally explicit here
  rather than buried in an env file so it's easy to find during development.
"""

from datetime import datetime, timedelta
from typing import Optional
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from database import get_db

# ── Crypto settings ────────────────────────────────────────────────────────────
SECRET_KEY = "disaster-bridge-secret-key-change-in-production-2026"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 168   # 7 days — dev-friendly

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


# ── Password helpers ───────────────────────────────────────────────────────────
def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── JWT helpers ────────────────────────────────────────────────────────────────
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


# ── FastAPI dependency ─────────────────────────────────────────────────────────
def get_current_commander(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    """
    Extracts and validates the Bearer token from the Authorization header.
    Returns the Commander ORM object or raises 401.
    Import lazily to avoid circular imports with models.py.
    """
    from models import Commander

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    commander_id = payload.get("sub")
    if commander_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bad token payload")

    commander = db.query(Commander).filter(
        Commander.id == uuid.UUID(commander_id),
        Commander.is_active == True,
    ).first()

    if commander is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Commander not found")

    return commander
