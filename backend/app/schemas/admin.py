"""Shapes returned and accepted by the admin routes. Never includes password hashes."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class UserBrief(BaseModel):
    id: int
    display_name: str
    email: str
    is_demo: bool


class Stat(BaseModel):
    value: int
    previous: int
    change_pct: float | None  # None = nothing to compare to


class DayCount(BaseModel):
    date: str
    count: int


class TopUser(BaseModel):
    user: UserBrief
    sign_ins: int
    actions: int


class Overview(BaseModel):
    start: str
    end: str
    total_users: Stat
    new_signups: Stat
    active_users: Stat
    sign_ins: Stat
    ads_created: Stat
    signups_per_day: list[DayCount]
    active_per_day: list[DayCount]
    top_users: list[TopUser]


class AdminUserRow(BaseModel):
    id: int
    display_name: str
    email: str
    business_name: str | None
    language: str
    role: str
    is_active: bool
    is_demo: bool
    created_at: datetime
    last_active: datetime | None
    sign_ins: int
    brands: int
    products: int


class UserPage(BaseModel):
    items: list[AdminUserRow]
    total: int
    page: int
    per_page: int


class EventRead(BaseModel):
    id: int
    created_at: datetime
    event_type: str
    detail: str | None
    user: UserBrief | None
    actor: UserBrief | None


class EventPage(BaseModel):
    items: list[EventRead]
    total: int
    page: int
    per_page: int


class AdminUserDetail(AdminUserRow):
    model_config = ConfigDict(from_attributes=True)

    phone: str | None
    open_sessions: int
    has_secret_word: bool
    recent_events: list[EventRead]


class AdminUserUpdate(BaseModel):
    """Only the fields that are sent change. Unknown fields are ignored."""

    role: Literal["user", "admin"] | None = None
    is_active: bool | None = None
