"""Date ranges and numbers for the admin dashboard. Pure functions; days are UTC days."""

from datetime import date, timedelta

PRESETS = ("today", "7d", "30d", "custom")
MAX_RANGE_DAYS = 366


class RangeError(ValueError):
    pass


def resolve_range(
    preset: str, today: date, start: date | None = None, end: date | None = None
) -> tuple[date, date]:
    """Inclusive (first_day, last_day) for a preset. 7d means today and the 6 days before."""
    if preset == "today":
        return today, today
    if preset == "7d":
        return today - timedelta(days=6), today
    if preset == "30d":
        return today - timedelta(days=29), today
    if preset == "custom":
        if start is None or end is None:
            raise RangeError("Pick a start and an end date.")
        if start > end:
            raise RangeError("The start date must not be after the end date.")
        if (end - start).days + 1 > MAX_RANGE_DAYS:
            raise RangeError(f"Pick at most {MAX_RANGE_DAYS} days.")
        return start, end
    raise RangeError("Unknown period.")


def previous_range(start: date, end: date) -> tuple[date, date]:
    """The period of the same length that ends the day before `start`."""
    days = (end - start).days + 1
    return start - timedelta(days=days), start - timedelta(days=1)


def pct_change(current: int, previous: int) -> float | None:
    """Percent change, rounded to a whole number. None when there is nothing to compare to."""
    if previous <= 0:
        return None
    return round((current - previous) * 100 / previous)


def day_list(start: date, end: date) -> list[date]:
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def fill_days(start: date, end: date, counts: dict[date, int]) -> list[dict]:
    """One point per day in the range, zero where nothing happened."""
    return [{"date": d.isoformat(), "count": int(counts.get(d, 0))} for d in day_list(start, end)]
