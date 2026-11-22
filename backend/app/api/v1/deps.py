"""Shared request dependencies."""

from datetime import UTC, datetime

from fastapi import Cookie, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import User, UserSession
from app.db.session import get_db
from app.domain.security import hash_token

SESSION_COOKIE = "adbanao_session"


def get_current_session(
    token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    db: Session = Depends(get_db),
) -> UserSession:
    if not token:
        raise HTTPException(status_code=401, detail="Not signed in")
    row = db.scalar(select(UserSession).where(UserSession.token_hash == hash_token(token)))
    if row is None:
        raise HTTPException(status_code=401, detail="Not signed in")
    expires = row.expires_at
    if expires.tzinfo is None:  # SQLite returns naive datetimes
        expires = expires.replace(tzinfo=UTC)
    if expires <= datetime.now(UTC):
        db.delete(row)
        db.commit()
        raise HTTPException(status_code=401, detail="Session expired. Sign in again.")
    return row


def get_current_user(session: UserSession = Depends(get_current_session)) -> User:
    user = session.user
    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account is suspended.")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admins only.")
    return user
