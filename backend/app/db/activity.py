"""Write to the activity log. Kept apart from the routes so every route records events the same way."""

from sqlalchemy.orm import Session

from app.db.models import ActivityLog


def record(
    db: Session,
    event: str,
    user_id: int | None = None,
    result: str = "success",
    detail: str | None = None,
) -> None:
    """Add a log row and save it. A logging failure must never break the user's action."""
    try:
        db.add(ActivityLog(user_id=user_id, event=event, result=result, detail=detail[:300] if detail else None))
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()
