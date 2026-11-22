"""Response and request shapes for the admin routes."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class Metric(BaseModel):
    value: int
    previous: int


class DayPoint(BaseModel):
    date: str  # local date, YYYY-MM-DD
    value: int


class TopUser(BaseModel):
    id: int
    display_name: str
    email: str
    sign_ins: int
    actions: int


class Summary(BaseModel):
    start: str
    end: str
    timezone: str
    total_users: Metric
    new_signups: Metric
    active_users: Metric
    sign_ins: Metric
    ads_created: Metric
    signups_per_day: list[DayPoint]
    active_per_day: list[DayPoint]
    top_users: list[TopUser]


class AdminUser(BaseModel):
    id: int
    email: str
    display_name: str
    business_name: str | None
    phone: str | None
    language: str
    role: str
    status: Literal["active", "suspended"]
    created_at: datetime
    last_active: datetime | None
    sign_ins: int
    brands: int
    products: int


class AdminUserList(BaseModel):
    total: int
    items: list[AdminUser]


class ActivityUser(BaseModel):
    id: int
    display_name: str
    email: str


class ActivityItem(BaseModel):
    id: int
    created_at: datetime
    event: str
    result: str
    detail: str | None
    user: ActivityUser | None


class ActivityList(BaseModel):
    total: int
    items: list[ActivityItem]


class AdminUserDetail(BaseModel):
    user: AdminUser
    recent_activity: list[ActivityItem]


class AdminUserChange(BaseModel):
    """Only fields that are sent are changed."""

    role: Literal["user", "admin"] | None = None
    is_active: bool | None = None
