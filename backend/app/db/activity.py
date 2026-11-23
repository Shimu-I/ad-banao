"""Write one line to the activity log. The caller commits, so the event and the change it
describes are saved together or not at all."""

from sqlalchemy.orm import Session

from app.db.models import ActivityEvent
from app.domain.events import clean_detail


def record(
    db: Session,
    event_type: str,
    user_id: int | None,
    *,
    actor_id: int | None = None,
    detail: str | None = None,
) -> None:
    db.add(
        ActivityEvent(
            user_id=user_id, actor_id=actor_id, event_type=event_type, detail=clean_detail(detail)
        )
    )
