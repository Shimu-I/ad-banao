"""Admin console: numbers, users, activity log, controls and CSV downloads.

Every route needs an active admin (`require_admin`). Nothing here returns password hashes or
session tokens. Days are UTC days. Every control an admin uses is written to the activity log.
"""

from datetime import UTC, date, datetime, time, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import Select, delete, func, or_, select
from sqlalchemy.orm import Session

from app.api.v1.deps import require_admin
from app.db import activity
from app.db.models import ActivityEvent, Ad, Brand, Product, User, UserSession
from app.db.session import get_db
from app.domain import events
from app.domain.admin_stats import RangeError, fill_days, pct_change, previous_range, resolve_range
from app.domain.csv_export import to_csv
from app.domain.roles import (
    ROLE_ADMIN,
    ROLE_USER,
    is_demo_email,
    role_change_problem,
    status_change_problem,
)
from app.schemas.admin import (
    AdminUserDetail,
    AdminUserRow,
    AdminUserUpdate,
    EventPage,
    EventRead,
    Overview,
    Stat,
    TopUser,
    UserBrief,
    UserPage,
)

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])

EXPORT_LIMIT = 50_000
PER_PAGE_CHOICES = (10, 25, 50, 100)


# ---------- helpers ----------


def _brief(u: User | None) -> UserBrief | None:
    if u is None:
        return None
    return UserBrief(
        id=u.id, display_name=u.display_name, email=u.email, is_demo=is_demo_email(u.email)
    )


def _event(e: ActivityEvent) -> EventRead:
    return EventRead(
        id=e.id,
        created_at=_utc(e.created_at),
        event_type=e.event_type,
        detail=e.detail,
        user=_brief(e.user),
        actor=_brief(e.actor),
    )


def _bounds(d_start: date, d_end: date) -> tuple[datetime, datetime]:
    """[start, end) as UTC datetimes covering whole days."""
    return (
        datetime.combine(d_start, time.min, tzinfo=UTC),
        datetime.combine(d_end + timedelta(days=1), time.min, tzinfo=UTC),
    )


def _range(
    period: str, start: date | None, end: date | None
) -> tuple[date, date]:
    try:
        return resolve_range(period, datetime.now(UTC).date(), start, end)
    except RangeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


def _utc(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:  # SQLite returns naive datetimes (UTC)
        return value.replace(tzinfo=UTC)
    return value


def _as_day(value: datetime) -> date:
    return _utc(value).astimezone(UTC).date()  # type: ignore[union-attr]


def _stat(cur: int, prev: int) -> Stat:
    return Stat(value=cur, previous=prev, change_pct=pct_change(cur, prev))


def _count(db: Session, stmt: Select) -> int:
    return int(db.scalar(stmt) or 0)


def _active_admins(db: Session) -> int:
    return _count(
        db,
        select(func.count(User.id)).where(User.role == ROLE_ADMIN, User.is_active.is_(True)),
    )


def _get_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _signins_sq():
    return (
        select(ActivityEvent.user_id.label("uid"), func.count(ActivityEvent.id).label("n"))
        .where(ActivityEvent.event_type == events.LOGIN)
        .group_by(ActivityEvent.user_id)
        .subquery()
    )


def _last_active_sq():
    return (
        select(ActivityEvent.user_id.label("uid"), func.max(ActivityEvent.created_at).label("t"))
        .where(ActivityEvent.event_type.in_(events.USER_ACTIVITY))
        .group_by(ActivityEvent.user_id)
        .subquery()
    )


def _brands_sq():
    return (
        select(Brand.user_id.label("uid"), func.count(Brand.id).label("n"))
        .group_by(Brand.user_id)
        .subquery()
    )


def _products_sq():
    return (
        select(Brand.user_id.label("uid"), func.count(Product.id).label("n"))
        .join(Product, Product.brand_id == Brand.id)
        .group_by(Brand.user_id)
        .subquery()
    )


def _user_rows_query():
    si, la, br, pr = _signins_sq(), _last_active_sq(), _brands_sq(), _products_sq()
    cols = {
        "sign_ins": func.coalesce(si.c.n, 0),
        "last_active": la.c.t,
        "brands": func.coalesce(br.c.n, 0),
        "products": func.coalesce(pr.c.n, 0),
    }
    stmt = (
        select(
            User,
            cols["sign_ins"].label("sign_ins"),
            cols["last_active"].label("last_active"),
            cols["brands"].label("brands"),
            cols["products"].label("products"),
        )
        .outerjoin(si, si.c.uid == User.id)
        .outerjoin(la, la.c.uid == User.id)
        .outerjoin(br, br.c.uid == User.id)
        .outerjoin(pr, pr.c.uid == User.id)
    )
    return stmt, cols


def _row(u: User, sign_ins: int, last_active: datetime | None, brands: int, products: int):
    return dict(
        id=u.id,
        display_name=u.display_name,
        email=u.email,
        business_name=u.business_name,
        language=u.language,
        role=u.role,
        is_active=u.is_active,
        is_demo=is_demo_email(u.email),
        created_at=_utc(u.created_at),
        last_active=_utc(last_active),
        sign_ins=int(sign_ins or 0),
        brands=int(brands or 0),
        products=int(products or 0),
    )


def _like(q: str) -> str:
    escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped.lower()}%"


def _filtered_users(
    q: str | None, status: str | None, role: str | None, language: str | None
):
    stmt, cols = _user_rows_query()
    if q and q.strip():
        like = _like(q.strip())
        stmt = stmt.where(
            or_(
                func.lower(User.email).like(like, escape="\\"),
                func.lower(User.display_name).like(like, escape="\\"),
                func.lower(func.coalesce(User.business_name, "")).like(like, escape="\\"),
            )
        )
    if status == "active":
        stmt = stmt.where(User.is_active.is_(True))
    elif status == "suspended":
        stmt = stmt.where(User.is_active.is_(False))
    if role in (ROLE_USER, ROLE_ADMIN):
        stmt = stmt.where(User.role == role)
    if language in ("en", "bn"):
        stmt = stmt.where(User.language == language)
    return stmt, cols


def _filtered_events(
    d_start: date | None,
    d_end: date | None,
    group: str | None,
    event_type: str | None,
    user_id: int | None,
):
    stmt = select(ActivityEvent)
    if d_start and d_end:
        lo, hi = _bounds(d_start, d_end)
        stmt = stmt.where(ActivityEvent.created_at >= lo, ActivityEvent.created_at < hi)
    if event_type:
        stmt = stmt.where(ActivityEvent.event_type == event_type)
    elif group in events.GROUPS:
        stmt = stmt.where(ActivityEvent.event_type.in_(events.GROUPS[group]))
    if user_id is not None:
        stmt = stmt.where(
            or_(ActivityEvent.user_id == user_id, ActivityEvent.actor_id == user_id)
        )
    return stmt


# ---------- overview ----------


@router.get("/overview", response_model=Overview)
def overview(
    period: Literal["today", "7d", "30d", "custom"] = "7d",
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
) -> Overview:
    d_start, d_end = _range(period, start, end)
    p_start, p_end = previous_range(d_start, d_end)
    lo, hi = _bounds(d_start, d_end)
    plo, phi = _bounds(p_start, p_end)

    def users_until(limit: datetime) -> int:
        return _count(db, select(func.count(User.id)).where(User.created_at < limit))

    def users_between(a: datetime, b: datetime) -> int:
        return _count(
            db, select(func.count(User.id)).where(User.created_at >= a, User.created_at < b)
        )

    def distinct_active(a: datetime, b: datetime) -> int:
        return _count(
            db,
            select(func.count(func.distinct(ActivityEvent.user_id))).where(
                ActivityEvent.event_type.in_(events.USER_ACTIVITY),
                ActivityEvent.created_at >= a,
                ActivityEvent.created_at < b,
                ActivityEvent.user_id.is_not(None),
            ),
        )

    def logins(a: datetime, b: datetime) -> int:
        return _count(
            db,
            select(func.count(ActivityEvent.id)).where(
                ActivityEvent.event_type == events.LOGIN,
                ActivityEvent.created_at >= a,
                ActivityEvent.created_at < b,
            ),
        )

    def ads(a: datetime, b: datetime) -> int:
        return _count(
            db, select(func.count(Ad.id)).where(Ad.created_at >= a, Ad.created_at < b)
        )

    signup_days: dict[date, int] = {}
    for (created,) in db.execute(
        select(User.created_at).where(User.created_at >= lo, User.created_at < hi)
    ):
        d = _as_day(created)
        signup_days[d] = signup_days.get(d, 0) + 1

    active_sets: dict[date, set[int]] = {}
    for uid, created in db.execute(
        select(ActivityEvent.user_id, ActivityEvent.created_at).where(
            ActivityEvent.event_type.in_(events.USER_ACTIVITY),
            ActivityEvent.created_at >= lo,
            ActivityEvent.created_at < hi,
            ActivityEvent.user_id.is_not(None),
        )
    ):
        active_sets.setdefault(_as_day(created), set()).add(uid)

    # Top users: sign-ins and actions in the period, most active first.
    per_user: dict[int, list[int]] = {}
    for uid, etype, n in db.execute(
        select(ActivityEvent.user_id, ActivityEvent.event_type, func.count(ActivityEvent.id))
        .where(
            ActivityEvent.user_id.is_not(None),
            ActivityEvent.created_at >= lo,
            ActivityEvent.created_at < hi,
            ActivityEvent.event_type.in_((events.LOGIN, *events.ACTIONS)),
        )
        .group_by(ActivityEvent.user_id, ActivityEvent.event_type)
    ):
        entry = per_user.setdefault(uid, [0, 0])
        entry[0 if etype == events.LOGIN else 1] += int(n)
    ranked = sorted(per_user.items(), key=lambda kv: (-(kv[1][0] + kv[1][1]), kv[0]))[:5]
    top = []
    for uid, (sign_ins, actions) in ranked:
        u = db.get(User, uid)
        if u is not None:
            top.append(TopUser(user=_brief(u), sign_ins=sign_ins, actions=actions))

    return Overview(
        start=d_start.isoformat(),
        end=d_end.isoformat(),
        total_users=_stat(users_until(hi), users_until(phi)),
        new_signups=_stat(users_between(lo, hi), users_between(plo, phi)),
        active_users=_stat(distinct_active(lo, hi), distinct_active(plo, phi)),
        sign_ins=_stat(logins(lo, hi), logins(plo, phi)),
        ads_created=_stat(ads(lo, hi), ads(plo, phi)),
        signups_per_day=fill_days(d_start, d_end, signup_days),
        active_per_day=fill_days(
            d_start, d_end, {d: len(s) for d, s in active_sets.items()}
        ),
        top_users=top,
    )


# ---------- users ----------

_SORTS = {"joined", "last_active", "name", "email", "sign_ins", "brands", "products"}


@router.get("/users", response_model=UserPage)
def list_users(
    q: str | None = Query(default=None, max_length=100),
    status: Literal["all", "active", "suspended"] = "all",
    role: Literal["all", "user", "admin"] = "all",
    language: Literal["all", "en", "bn"] = "all",
    sort: str = "joined",
    direction: Literal["asc", "desc"] = "desc",
    page: int = Query(default=1, ge=1, le=100_000),
    per_page: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
) -> UserPage:
    if sort not in _SORTS:
        raise HTTPException(status_code=422, detail="Unknown sort column.")
    stmt, cols = _filtered_users(q, status, role, language)
    total = _count(db, select(func.count()).select_from(stmt.order_by(None).subquery()))

    sort_col = {
        "joined": User.created_at,
        "last_active": cols["last_active"],
        "name": func.lower(User.display_name),
        "email": User.email,
        "sign_ins": cols["sign_ins"],
        "brands": cols["brands"],
        "products": cols["products"],
    }[sort]
    order = sort_col.asc() if direction == "asc" else sort_col.desc()
    stmt = stmt.order_by(order.nulls_last() if sort == "last_active" else order, User.id.desc())
    rows = db.execute(stmt.limit(per_page).offset((page - 1) * per_page)).all()
    return UserPage(
        items=[AdminUserRow(**_row(*r)) for r in rows], total=total, page=page, per_page=per_page
    )


@router.get("/users/{user_id}", response_model=AdminUserDetail)
def user_detail(user_id: int, db: Session = Depends(get_db)) -> AdminUserDetail:
    stmt, _ = _user_rows_query()
    row = db.execute(stmt.where(User.id == user_id)).first()
    if row is None:
        raise HTTPException(status_code=404, detail="User not found")
    user = row[0]
    recent = db.scalars(
        select(ActivityEvent)
        .where(
            or_(ActivityEvent.user_id == user_id, ActivityEvent.actor_id == user_id),
        )
        .order_by(ActivityEvent.created_at.desc(), ActivityEvent.id.desc())
        .limit(20)
    ).all()
    sessions = _count(
        db,
        select(func.count(UserSession.id)).where(
            UserSession.user_id == user_id, UserSession.expires_at > datetime.now(UTC)
        ),
    )
    return AdminUserDetail(
        **_row(*row),
        phone=user.phone,
        open_sessions=sessions,
        recent_events=[_event(e) for e in recent],
    )


@router.patch("/users/{user_id}", response_model=AdminUserRow)
def update_user(
    user_id: int,
    body: AdminUserUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminUserRow:
    target = _get_user(db, user_id)
    changes = body.model_dump(exclude_unset=True, exclude_none=True)
    if not changes:
        raise HTTPException(status_code=422, detail="Nothing to change.")

    admins = _active_admins(db)
    if "role" in changes:
        problem = role_change_problem(
            actor_id=admin.id,
            target_id=target.id,
            target_role=target.role,
            target_active=target.is_active,
            new_role=changes["role"],
            active_admins=admins,
        )
        if problem:
            raise HTTPException(status_code=409, detail=problem)
    if "is_active" in changes:
        problem = status_change_problem(
            actor_id=admin.id,
            target_id=target.id,
            target_role=target.role,
            target_active=target.is_active,
            new_active=changes["is_active"],
            active_admins=admins,
        )
        if problem:
            raise HTTPException(status_code=409, detail=problem)

    if "role" in changes and changes["role"] != target.role:
        activity.record(
            db,
            events.ADMIN_ROLE_CHANGED,
            target.id,
            actor_id=admin.id,
            detail=f"{target.role} -> {changes['role']}",
        )
        target.role = changes["role"]
    if "is_active" in changes and changes["is_active"] != target.is_active:
        target.is_active = changes["is_active"]
        activity.record(
            db,
            events.ADMIN_REACTIVATED if target.is_active else events.ADMIN_SUSPENDED,
            target.id,
            actor_id=admin.id,
        )
        if not target.is_active:  # suspension takes effect at once
            db.execute(delete(UserSession).where(UserSession.user_id == target.id))
    db.commit()

    stmt, _ = _user_rows_query()
    return AdminUserRow(**_row(*db.execute(stmt.where(User.id == target.id)).first()))


@router.post("/users/{user_id}/sign-out", status_code=204)
def sign_out_everywhere(
    user_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)
) -> None:
    target = _get_user(db, user_id)
    db.execute(delete(UserSession).where(UserSession.user_id == target.id))
    activity.record(db, events.ADMIN_SIGNED_OUT_USER, target.id, actor_id=admin.id)
    db.commit()


# ---------- activity ----------


@router.get("/activity", response_model=EventPage)
def list_activity(
    period: Literal["all", "today", "7d", "30d", "custom"] = "all",
    start: date | None = None,
    end: date | None = None,
    group: Literal["all", "signin", "content", "account", "admin"] = "all",
    event_type: str | None = Query(default=None, max_length=40),
    user_id: int | None = Query(default=None, ge=1),
    page: int = Query(default=1, ge=1, le=100_000),
    per_page: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
) -> EventPage:
    if event_type and event_type not in events.ALL_EVENTS:
        raise HTTPException(status_code=422, detail="Unknown event type.")
    d_start = d_end = None
    if period != "all":
        d_start, d_end = _range(period, start, end)
    stmt = _filtered_events(d_start, d_end, group, event_type, user_id)
    total = _count(db, select(func.count()).select_from(stmt.order_by(None).subquery()))
    rows = db.scalars(
        stmt.order_by(ActivityEvent.created_at.desc(), ActivityEvent.id.desc())
        .limit(per_page)
        .offset((page - 1) * per_page)
    ).all()
    return EventPage(items=[_event(e) for e in rows], total=total, page=page, per_page=per_page)


# ---------- CSV downloads ----------


def _csv_response(name: str, body: str) -> Response:
    stamp = datetime.now(UTC).strftime("%Y%m%d")
    return Response(
        content="﻿" + body,  # BOM so Excel shows Bangla names correctly
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{name}-{stamp}.csv"'},
    )


@router.get("/export/users.csv")
def export_users(
    q: str | None = Query(default=None, max_length=100),
    status: Literal["all", "active", "suspended"] = "all",
    role: Literal["all", "user", "admin"] = "all",
    language: Literal["all", "en", "bn"] = "all",
    db: Session = Depends(get_db),
) -> Response:
    stmt, _ = _filtered_users(q, status, role, language)
    rows = db.execute(stmt.order_by(User.id).limit(EXPORT_LIMIT)).all()
    body = to_csv(
        [
            "id", "name", "email", "business", "language", "role", "status", "demo",
            "joined", "last_active", "sign_ins", "brands", "products",
        ],  # fmt: skip
        (
            (
                r.id, r.display_name, r.email, r.business_name, r.language, r.role,
                "active" if r.is_active else "suspended", "yes" if r.is_demo else "no",
                r.created_at.isoformat(),
                r.last_active.isoformat() if r.last_active else "",
                r.sign_ins, r.brands, r.products,
            )  # fmt: skip
            for r in (AdminUserRow(**_row(*row)) for row in rows)
        ),
    )
    return _csv_response("adbanao-users", body)


@router.get("/export/activity.csv")
def export_activity(
    period: Literal["all", "today", "7d", "30d", "custom"] = "30d",
    start: date | None = None,
    end: date | None = None,
    group: Literal["all", "signin", "content", "account", "admin"] = "all",
    event_type: str | None = Query(default=None, max_length=40),
    user_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
) -> Response:
    d_start = d_end = None
    if period != "all":
        d_start, d_end = _range(period, start, end)
    stmt = _filtered_events(d_start, d_end, group, event_type, user_id)
    rows = db.scalars(
        stmt.order_by(ActivityEvent.created_at.desc(), ActivityEvent.id.desc()).limit(EXPORT_LIMIT)
    ).all()
    body = to_csv(
        ["id", "time_utc", "event", "detail", "user_id", "user_email", "by_admin_email"],
        (
            (
                e.id,
                e.created_at.isoformat(),
                e.event_type,
                e.detail,
                e.user_id,
                e.user.email if e.user else "",
                e.actor.email if e.actor else "",
            )
            for e in rows
        ),
    )
    return _csv_response("adbanao-activity", body)


