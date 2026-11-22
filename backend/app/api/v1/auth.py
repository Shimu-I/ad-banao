"""Sign up, sign in, sign out and the signed-in user's profile."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.v1.deps import SESSION_COOKIE, get_current_session, get_current_user
from app.core.config import get_settings
from app.db.activity import record
from app.db.models import User, UserSession
from app.db.session import get_db
from app.domain import activity as ACT
from app.domain.activity import admin_email_set
from app.domain.security import (
    DUMMY_HASH,
    hash_password,
    hash_token,
    new_session_token,
    verify_password,
)
from app.schemas.auth import (
    LoginRequest,
    PasswordChange,
    SignupRequest,
    UserRead,
    UserUpdate,
)

router = APIRouter(tags=["auth"])

SESSION_DAYS = 14


def _start_session(db: Session, user: User, response: Response) -> None:
    token = new_session_token()
    db.add(
        UserSession(
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=datetime.now(UTC) + timedelta(days=SESSION_DAYS),
        )
    )
    db.commit()
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_DAYS * 86400,
        httponly=True,
        samesite="lax",
        secure=get_settings().app_env == "production",
        path="/",
    )


@router.post("/auth/signup", response_model=UserRead, status_code=201)
def signup(body: SignupRequest, response: Response, db: Session = Depends(get_db)) -> User:
    if db.scalar(select(User).where(User.email == body.email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    settings = get_settings()
    is_admin = settings.app_env != "production" and body.email in admin_email_set(settings.admin_emails)
    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        display_name=body.display_name,
        business_name=body.business_name,
        role="admin" if is_admin else "user",
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # two sign-ups with the same email at the same moment
        db.rollback()
        raise HTTPException(
            status_code=409, detail="An account with this email already exists."
        ) from None
    _start_session(db, user, response)
    record(db, ACT.SIGNED_UP, user.id)
    return user


@router.post("/auth/login", response_model=UserRead)
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)) -> User:
    user = db.scalar(select(User).where(User.email == body.email))
    # Always run one password check so timing does not reveal which emails exist.
    ok = verify_password(body.password, user.password_hash if user else DUMMY_HASH)
    if user is None or not ok:
        record(db, ACT.SIGN_IN_FAILED, user.id if user else None, "failed", None if user else "unknown email")
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    if not user.is_active:
        record(db, ACT.SIGN_IN_FAILED, user.id, "failed", "account suspended")
        raise HTTPException(status_code=403, detail="This account is suspended. Contact the administrator.")
    _start_session(db, user, response)
    record(db, ACT.SIGNED_IN, user.id)
    return user


@router.post("/auth/logout", status_code=204)
def logout(
    response: Response,
    session: UserSession = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> None:
    user_id = session.user_id
    db.delete(session)
    db.commit()
    record(db, ACT.SIGNED_OUT, user_id)
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/users/me", response_model=UserRead)
def read_me(user: User = Depends(get_current_user)) -> User:
    return user


@router.patch("/users/me", response_model=UserRead)
def update_me(
    body: UserUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    for field, value in body.model_dump(exclude_unset=True).items():
        if field in ("display_name", "language") and value is None:
            continue  # these cannot be cleared
        setattr(user, field, value)
    db.commit()
    record(db, ACT.PROFILE_UPDATED, user.id, detail=", ".join(sorted(body.model_dump(exclude_unset=True))))
    return user


@router.post("/users/me/password", status_code=204)
def change_password(
    body: PasswordChange,
    session: UserSession = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> None:
    user = session.user
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    user.password_hash = hash_password(body.new_password)
    # Sign out every other browser; keep this one.
    db.execute(
        delete(UserSession).where(UserSession.user_id == user.id, UserSession.id != session.id)
    )
    db.commit()
    record(db, ACT.PASSWORD_CHANGED, user.id)
