"""Admin routes: who uses the product, how much, and control over accounts.

Every route needs an admin. Day boundaries use the display timezone (Asia/Dhaka by default),
so "today" starts at local midnight. Dates are stored and returned in UTC.
"""

import csv
import io
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import and_, delete, desc, func, or_, select
from sqlalchemy.orm import Session

from app.api.v1.deps import require_admin
from app.core.config import get_settings
from app.db.activity import record
from app.db.models import ActivityLog, Ad, Brand, Product, User, UserSession
from app.db.session import get_db
from app.domain import activity as ACT
from app.schemas.admin import (
    ActivityItem,
    ActivityList,
    ActivityUser,
    AdminUser,
    AdminUserChange,
    AdminUserDetail,
    AdminUserList,
    DayPoint,
    Metric,
    Summary,
    TopUser,
)

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])

MAX_DAYS = 92


def _aware(dt: datetime | None) -> datetime | None:
    """SQLite gives back naive datetimes; everything stored is UTC."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _tz() -> ZoneInfo:
    return ZoneInfo(get_settings().display_timezone)


def _parse_range(start: date | None, end: date | None) -> tuple[date, date]:
    tz = _tz()
    today = datetime.now(tz).date()
    end = end or today
    start = start or end - timedelta(days=6)
    if start > end:
        raise HTTPException(status_code=422, detail="The start date is after the end date.")
    if (end - start).days + 1 > MAX_DAYS:
        raise HTTPException(status_code=422, detail=f"Choose at most {MAX_DAYS} days.")
    return start, end


def _utc_bounds(start: date, end: date) -> tuple[datetime, datetime]:
    """Local midnight of the first day to local midnight after the last day, as UTC."""
    tz = _tz()
    lo = datetime(start.year, start.month, start.day, tzinfo=tz).astimezone(UTC)
    nxt = end + timedelta(days=1)
    hi = datetime(nxt.year, nxt.month, nxt.day, tzinfo=tz).astimezone(UTC)
    return lo, hi


# --------------------------------------------------------------------------- summary


def _count(db: Session, stmt) -> int:
    return int(db.scalar(stmt) or 0)


def _metrics(db: Session, lo: datetime, hi: datetime) -> dict[str, int]:
    ok = ActivityLog.result == "success"
    in_range = and_(ActivityLog.created_at >= lo, ActivityLog.created_at < hi)
    return {
        "total_users": _count(db, select(func.count(User.id)).where(User.created_at < hi)),
        "new_signups": _count(db, select(func.count(User.id)).where(User.created_at >= lo, User.created_at < hi)),
        "active_users": _count(
            db,
            select(func.count(func.distinct(ActivityLog.user_id))).where(
                ok, in_range, ActivityLog.user_id.is_not(None)
            ),
        ),
        "sign_ins": _count(
            db, select(func.count(ActivityLog.id)).where(ok, in_range, ActivityLog.event == ACT.SIGNED_IN)
        ),
        "ads_created": _count(db, select(func.count(Ad.id)).where(Ad.created_at >= lo, Ad.created_at < hi)),
    }


@router.get("/summary", response_model=Summary)
def summary(
    start: date | None = None, end: date | None = None, db: Session = Depends(get_db)
) -> Summary:
    start, end = _parse_range(start, end)
    n = (end - start).days + 1
    lo, hi = _utc_bounds(start, end)
    prev_lo, prev_hi = _utc_bounds(start - timedelta(days=n), start - timedelta(days=1))
    now, before = _metrics(db, lo, hi), _metrics(db, prev_lo, prev_hi)
    tz = _tz()

    days = [start + timedelta(days=i) for i in range(n)]
    signups: dict[date, int] = dict.fromkeys(days, 0)
    for (created,) in db.execute(select(User.created_at).where(User.created_at >= lo, User.created_at < hi)):
        signups[_aware(created).astimezone(tz).date()] += 1
    active: dict[date, set[int]] = {d: set() for d in days}
    rows = db.execute(
        select(ActivityLog.user_id, ActivityLog.created_at).where(
            ActivityLog.result == "success",
            ActivityLog.user_id.is_not(None),
            ActivityLog.created_at >= lo,
            ActivityLog.created_at < hi,
        )
    )
    for uid, created in rows:
        active[_aware(created).astimezone(tz).date()].add(uid)

    counts = db.execute(
        select(ActivityLog.user_id, ActivityLog.event, func.count(ActivityLog.id))
        .where(
            ActivityLog.result == "success",
            ActivityLog.user_id.is_not(None),
            ActivityLog.created_at >= lo,
            ActivityLog.created_at < hi,
        )
        .group_by(ActivityLog.user_id, ActivityLog.event)
    )
    per_user: dict[int, list[int]] = {}
    for uid, event, c in counts:
        entry = per_user.setdefault(uid, [0, 0])
        if event == ACT.SIGNED_IN:
            entry[0] += c
        elif event not in (ACT.SIGNED_OUT, ACT.ADMIN_ACTION):
            entry[1] += c
    ranked = sorted(per_user.items(), key=lambda kv: (-(kv[1][0] + kv[1][1]), kv[0]))[:5]
    users = {u.id: u for u in db.scalars(select(User).where(User.id.in_([uid for uid, _ in ranked])))}
    top = [
        TopUser(id=uid, display_name=users[uid].display_name, email=users[uid].email, sign_ins=c[0], actions=c[1])
        for uid, c in ranked
        if uid in users
    ]

    return Summary(
        start=start.isoformat(),
        end=end.isoformat(),
        timezone=get_settings().display_timezone,
        **{k: Metric(value=now[k], previous=before[k]) for k in now},
        signups_per_day=[DayPoint(date=d.isoformat(), value=signups[d]) for d in days],
        active_per_day=[DayPoint(date=d.isoformat(), value=len(active[d])) for d in days],
        top_users=top,
    )


# --------------------------------------------------------------------------- users

_SORTS = {"name", "email", "joined", "last_active", "sign_ins", "brands", "products", "status"}


def _user_query():
    last_active = (
        select(func.max(ActivityLog.created_at))
        .where(ActivityLog.user_id == User.id, ActivityLog.result == "success")
        .correlate(User)
        .scalar_subquery()
    )
    sign_ins = (
        select(func.count(ActivityLog.id))
        .where(ActivityLog.user_id == User.id, ActivityLog.event == ACT.SIGNED_IN, ActivityLog.result == "success")
        .correlate(User)
        .scalar_subquery()
    )
    brands = select(func.count(Brand.id)).where(Brand.user_id == User.id).correlate(User).scalar_subquery()
    products = (
        select(func.count(Product.id))
        .join(Brand, Product.brand_id == Brand.id)
        .where(Brand.user_id == User.id)
        .correlate(User)
        .scalar_subquery()
    )
    cols = {
        "last_active": last_active.label("last_active"),
        "sign_ins": sign_ins.label("sign_ins"),
        "brands": brands.label("brands"),
        "products": products.label("products"),
    }
    return select(User, *cols.values()), cols


def _admin_user(row) -> AdminUser:
    user, last_active, sign_ins, brands, products = row
    return AdminUser(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        business_name=user.business_name,
        phone=user.phone,
        language=user.language,
        role=user.role,
        status="active" if user.is_active else "suspended",
        created_at=_aware(user.created_at),
        last_active=_aware(last_active),
        sign_ins=int(sign_ins or 0),
        brands=int(brands or 0),
        products=int(products or 0),
    )


def _filtered_users(search, status, language, role):
    stmt, cols = _user_query()
    if search:
        like = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(User.email).like(like),
                func.lower(User.display_name).like(like),
                func.lower(func.coalesce(User.business_name, "")).like(like),
            )
        )
    if status == "active":
        stmt = stmt.where(User.is_active.is_(True))
    elif status == "suspended":
        stmt = stmt.where(User.is_active.is_(False))
    if language:
        stmt = stmt.where(User.language == language)
    if role:
        stmt = stmt.where(User.role == role)
    return stmt, cols


@router.get("/users", response_model=AdminUserList)
def list_users(
    search: str | None = Query(None, max_length=100),
    status: str | None = Query(None, pattern="^(active|suspended)$"),
    language: str | None = Query(None, pattern="^(en|bn)$"),
    role: str | None = Query(None, pattern="^(user|admin)$"),
    sort: str = "joined",
    order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> AdminUserList:
    if sort not in _SORTS:
        raise HTTPException(status_code=422, detail="Unknown sort column.")
    stmt, cols = _filtered_users(search, status, language, role)
    total = _count(db, select(func.count()).select_from(stmt.order_by(None).subquery()))
    key = {
        "name": func.lower(User.display_name),
        "email": User.email,
        "joined": User.created_at,
        "status": User.is_active,
        **cols,
    }[sort]
    ordering = desc(key) if order == "desc" else key.asc()
    stmt = stmt.order_by(ordering.nulls_last(), User.id).limit(limit).offset(offset)
    return AdminUserList(total=total, items=[_admin_user(r) for r in db.execute(stmt)])


def _activity_items(db: Session, stmt) -> list[ActivityItem]:
    out = []
    for entry, user in db.execute(stmt):
        out.append(
            ActivityItem(
                id=entry.id,
                created_at=_aware(entry.created_at),
                event=entry.event,
                result=entry.result,
                detail=entry.detail,
                user=ActivityUser(id=user.id, display_name=user.display_name, email=user.email) if user else None,
            )
        )
    return out


def _activity_select():
    return select(ActivityLog, User).outerjoin(User, ActivityLog.user_id == User.id)


def _get_user_row(db: Session, user_id: int):
    stmt, _ = _user_query()
    row = db.execute(stmt.where(User.id == user_id)).first()
    if row is None:
        raise HTTPException(status_code=404, detail="User not found")
    return row


@router.get("/users/{user_id}", response_model=AdminUserDetail)
def user_detail(user_id: int, db: Session = Depends(get_db)) -> AdminUserDetail:
    row = _get_user_row(db, user_id)
    recent = _activity_items(
        db, _activity_select().where(ActivityLog.user_id == user_id).order_by(desc(ActivityLog.id)).limit(20)
    )
    return AdminUserDetail(user=_admin_user(row), recent_activity=recent)


@router.patch("/users/{user_id}", response_model=AdminUser)
def change_user(
    user_id: int,
    body: AdminUserChange,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> AdminUser:
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot change your own role or status.")
    notes = []
    if body.role is not None and body.role != target.role:
        target.role = body.role
        notes.append(f"role {body.role}")
    if body.is_active is not None and body.is_active != target.is_active:
        target.is_active = body.is_active
        notes.append("activated" if body.is_active else "suspended")
        if not body.is_active:  # suspending signs the person out everywhere
            db.execute(delete(UserSession).where(UserSession.user_id == target.id))
    db.commit()
    if notes:
        record(db, ACT.ADMIN_ACTION, admin.id, detail=f"{', '.join(notes)}: {target.email}")
    return _admin_user(_get_user_row(db, user_id))


@router.post("/users/{user_id}/sign-out-everywhere", status_code=204)
def sign_out_everywhere(
    user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)
) -> None:
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    db.execute(delete(UserSession).where(UserSession.user_id == target.id))
    db.commit()
    record(db, ACT.ADMIN_ACTION, admin.id, detail=f"signed out everywhere: {target.email}")


# --------------------------------------------------------------------------- activity


def _filtered_activity(event, user_id, result, start, end):
    stmt = _activity_select()
    if event:
        stmt = stmt.where(ActivityLog.event == event)
    if user_id:
        stmt = stmt.where(ActivityLog.user_id == user_id)
    if result:
        stmt = stmt.where(ActivityLog.result == result)
    if start or end:
        s, e = _parse_range(start, end) if (start and end) else (start or end, end or start)
        lo, hi = _utc_bounds(s, e)
        stmt = stmt.where(ActivityLog.created_at >= lo, ActivityLog.created_at < hi)
    return stmt.order_by(desc(ActivityLog.id))


@router.get("/activity", response_model=ActivityList)
def list_activity(
    event: str | None = Query(None, pattern="^[a-z_]{1,40}$"),
    user_id: int | None = None,
    result: str | None = Query(None, pattern="^(success|failed)$"),
    start: date | None = None,
    end: date | None = None,
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> ActivityList:
    stmt = _filtered_activity(event, user_id, result, start, end)
    total = _count(db, select(func.count()).select_from(stmt.order_by(None).subquery()))
    return ActivityList(total=total, items=_activity_items(db, stmt.limit(limit).offset(offset)))


# --------------------------------------------------------------------------- CSV

EXPORT_LIMIT = 50_000


def _csv(filename: str, header: list[str], rows) -> Response:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(header)
    for row in rows:
        writer.writerow([ACT.csv_safe(v) for v in row])
    return Response(
        buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/users.csv")
def export_users(db: Session = Depends(get_db), admin: User = Depends(require_admin)) -> Response:
    stmt, _ = _user_query()
    rows = [_admin_user(r) for r in db.execute(stmt.order_by(User.id).limit(EXPORT_LIMIT))]
    record(db, ACT.ADMIN_ACTION, admin.id, detail="downloaded users CSV")
    return _csv(
        "adbanao-users.csv",
        ["id", "name", "email", "business", "language", "role", "status", "joined", "last_active", "sign_ins", "brands", "products"],
        (
            [u.id, u.display_name, u.email, u.business_name, u.language, u.role, u.status,
             u.created_at.isoformat(), u.last_active.isoformat() if u.last_active else "", u.sign_ins, u.brands, u.products]
            for u in rows
        ),
    )


@router.get("/export/activity.csv")
def export_activity(
    event: str | None = Query(None, pattern="^[a-z_]{1,40}$"),
    user_id: int | None = None,
    result: str | None = Query(None, pattern="^(success|failed)$"),
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> Response:
    items = _activity_items(db, _filtered_activity(event, user_id, result, start, end).limit(EXPORT_LIMIT))
    record(db, ACT.ADMIN_ACTION, admin.id, detail="downloaded activity CSV")
    return _csv(
        "adbanao-activity.csv",
        ["time_utc", "user", "email", "event", "result", "detail"],
        (
            [i.created_at.isoformat(), i.user.display_name if i.user else "", i.user.email if i.user else "", i.event, i.result, i.detail or ""]
            for i in items
        ),
    )
