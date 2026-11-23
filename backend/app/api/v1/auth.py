"""Sign up, sign in, sign out and the signed-in user's profile."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.v1.deps import SESSION_COOKIE, get_current_session, get_current_user
from app.core.config import get_settings
from app.db import activity
from app.db.models import User, UserSession
from app.db.session import get_db
from app.domain import events
from app.domain.roles import (
    ROLE_ADMIN,
    bootstrap_secret_word,
    is_bootstrap_admin,
)
from app.domain.security import (
    DUMMY_HASH,
    hash_password,
    hash_token,
    new_session_token,
    verify_password,
)
from app.schemas.auth import (
    AdminLoginRequest,
    LoginRequest,
    PasswordChange,
    SignupRequest,
    UserRead,
    UserUpdate,
)

router = APIRouter(tags=["auth"])

SESSION_DAYS = 14


def _apply_bootstrap_admin(user: User) -> None:
    """Development and test only: emails in ADMIN_EMAILS become admins."""
    settings = get_settings()
    if user.role != ROLE_ADMIN and is_bootstrap_admin(
        user.email, settings.admin_emails, settings.app_env
    ):
        user.role = ROLE_ADMIN
    word = bootstrap_secret_word(user.email, settings.admin_emails, settings.app_env)
    if word and user.role == ROLE_ADMIN and not user.admin_secret_hash:
        user.admin_secret_hash = hash_password(word)


def _start_session(
    db: Session, user: User, response: Response, admin_verified: bool = False
) -> None:
    token = new_session_token()
    db.add(
        UserSession(
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=datetime.now(UTC) + timedelta(days=SESSION_DAYS),
            admin_verified=admin_verified,
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
    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        display_name=body.display_name,
        business_name=body.business_name,
    )
    _apply_bootstrap_admin(user)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # two sign-ups with the same email at the same moment
        db.rollback()
        raise HTTPException(
            status_code=409, detail="An account with this email already exists."
        ) from None
    activity.record(db, events.SIGNUP, user.id)
    _start_session(db, user, response)
    return user


@router.post("/auth/login", response_model=UserRead)
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)) -> User:
    user = db.scalar(select(User).where(User.email == body.email))
    # Always run one password check so timing does not reveal which emails exist.
    ok = verify_password(body.password, user.password_hash if user else DUMMY_HASH)
    if user is None or not ok:
        # Logged without the typed email, so the log never stores strangers' addresses.
        activity.record(db, events.LOGIN_FAILED, user.id if user else None)
        db.commit()
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    if not user.is_active:
        # Only said after a correct password, so this does not reveal which emails exist.
        activity.record(db, events.LOGIN_BLOCKED, user.id)
        db.commit()
        raise HTTPException(
            status_code=403, detail="This account has been suspended. Contact support."
        )
    _apply_bootstrap_admin(user)
    activity.record(db, events.LOGIN, user.id)
    _start_session(db, user, response)
    return user


@router.post("/auth/admin-login", response_model=UserRead)
def admin_login(
    body: AdminLoginRequest, response: Response, db: Session = Depends(get_db)
) -> User:
    """Second sign-in for admins: email, password and secret word. The three are checked
    together and one message covers every failure, so nothing reveals which part was wrong
    or whether the email belongs to an admin."""
    user = db.scalar(select(User).where(User.email == body.email))
    password_ok = verify_password(body.password, user.password_hash if user else DUMMY_HASH)
    if user is not None and password_ok:
        _apply_bootstrap_admin(user)  # development and test only
    secret_hash = user.admin_secret_hash if user and user.admin_secret_hash else None
    secret_ok = verify_password(body.secret_word.strip(), secret_hash or DUMMY_HASH)
    allowed = bool(
        user and password_ok and secret_ok and secret_hash and user.role == ROLE_ADMIN
    )
    if not allowed or user is None:
        activity.record(db, events.ADMIN_LOGIN_FAILED, user.id if user else None)
        db.commit()
        raise HTTPException(
            status_code=401, detail="Incorrect email, password or secret word."
        )
    if not user.is_active:
        activity.record(db, events.LOGIN_BLOCKED, user.id)
        db.commit()
        raise HTTPException(
            status_code=403, detail="This account has been suspended. Contact support."
        )
    activity.record(db, events.ADMIN_LOGIN, user.id)
    _start_session(db, user, response, admin_verified=True)
    return user


@router.post("/auth/logout", status_code=204)
def logout(
    response: Response,
    session: UserSession = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> None:
    activity.record(db, events.LOGOUT, session.user_id)
    db.delete(session)
    db.commit()
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
    changed = []
    for field, value in body.model_dump(exclude_unset=True).items():
        if field in ("display_name", "language") and value is None:
            continue  # these cannot be cleared
        if getattr(user, field) != value:
            changed.append(field)
        setattr(user, field, value)
    if changed:
        activity.record(db, events.PROFILE_UPDATED, user.id, detail=", ".join(changed))
    db.commit()
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
    activity.record(db, events.PASSWORD_CHANGED, user.id)
    db.commit()
