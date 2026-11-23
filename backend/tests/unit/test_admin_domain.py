from datetime import date

import pytest

from app.domain import events
from app.domain.admin_stats import (
    RangeError,
    fill_days,
    pct_change,
    previous_range,
    resolve_range,
)
from app.domain.csv_export import csv_safe, to_csv
from app.domain.roles import (
    bootstrap_secret_word,
    secret_word_problem,
    is_bootstrap_admin,
    is_demo_email,
    parse_admin_emails,
    role_change_problem,
    status_change_problem,
)

TODAY = date(2026, 11, 22)


def test_presets():
    assert resolve_range("today", TODAY) == (TODAY, TODAY)
    assert resolve_range("7d", TODAY) == (date(2026, 11, 16), TODAY)
    assert resolve_range("30d", TODAY) == (date(2026, 10, 24), TODAY)


def test_custom_range_rules():
    assert resolve_range("custom", TODAY, date(2026, 1, 1), date(2026, 1, 5))[1] == date(2026, 1, 5)
    for args in [(None, None), (date(2026, 2, 1), date(2026, 1, 1)), (date(2024, 1, 1), TODAY)]:
        with pytest.raises(RangeError):
            resolve_range("custom", TODAY, *args)
    with pytest.raises(RangeError):
        resolve_range("yesterday", TODAY)


def test_previous_range_same_length_and_adjacent():
    assert previous_range(date(2026, 11, 16), TODAY) == (date(2026, 11, 9), date(2026, 11, 15))
    assert previous_range(TODAY, TODAY) == (date(2026, 11, 21), date(2026, 11, 21))


def test_pct_change():
    assert pct_change(14, 10) == 40
    assert pct_change(5, 10) == -50
    assert pct_change(0, 0) is None and pct_change(3, 0) is None


def test_fill_days_has_every_day():
    pts = fill_days(date(2026, 11, 20), date(2026, 11, 22), {date(2026, 11, 21): 4})
    assert [p["count"] for p in pts] == [0, 4, 0]
    assert pts[0]["date"] == "2026-11-20"


def test_admin_email_list():
    assert parse_admin_emails(" A@x.com, ,b@Y.com ") == {"a@x.com", "b@y.com"}
    assert is_bootstrap_admin("A@X.com", "a@x.com", "development")
    assert is_bootstrap_admin("a@x.com", "a@x.com", "test")
    assert not is_bootstrap_admin("a@x.com", "a@x.com", "production")
    assert not is_bootstrap_admin("other@x.com", "a@x.com", "development")
    assert not is_bootstrap_admin("a@x.com", "", "development")


def test_admin_list_with_secret_words():
    raw = "a@x.com=Open Sesame, B@y.com , c@z.com="
    assert parse_admin_emails(raw) == {"a@x.com", "b@y.com", "c@z.com"}
    assert bootstrap_secret_word("A@X.com", raw, "development") == "Open Sesame"
    assert bootstrap_secret_word("b@y.com", raw, "test") is None
    assert bootstrap_secret_word("c@z.com", raw, "test") is None
    assert bootstrap_secret_word("a@x.com", raw, "production") is None


def test_secret_word_rules():
    assert secret_word_problem("short")
    assert secret_word_problem("  abcde  ")  # spaces do not count
    assert secret_word_problem("x" * 129)
    assert secret_word_problem("same-as-pass", "same-as-pass")
    assert secret_word_problem("long enough word", "other-password") is None


def test_demo_email():
    assert is_demo_email("Rina@demo.adbanao.test")
    assert not is_demo_email("rina@example.com")


_BASE = dict(actor_id=1, target_id=2, target_role="user", target_active=True)


def test_role_safeguards():
    assert role_change_problem(**_BASE, new_role="admin", active_admins=1) is None
    assert role_change_problem(**{**_BASE, "target_id": 1, "target_role": "admin"},
                               new_role="user", active_admins=2)  # not yourself
    assert role_change_problem(**{**_BASE, "target_role": "admin"},
                               new_role="user", active_admins=1)  # last admin
    assert role_change_problem(**{**_BASE, "target_role": "admin"},
                               new_role="user", active_admins=2) is None
    assert role_change_problem(**_BASE, new_role="root", active_admins=2)


def test_status_safeguards():
    assert status_change_problem(**_BASE, new_active=False, active_admins=1) is None
    assert status_change_problem(**{**_BASE, "target_id": 1}, new_active=False, active_admins=3)
    assert status_change_problem(**{**_BASE, "target_role": "admin"}, new_active=False, active_admins=1)
    assert status_change_problem(**{**_BASE, "target_active": False}, new_active=True, active_admins=1) is None


def test_csv_cells_cannot_run_as_formulas():
    assert csv_safe("=1+1") == "'=1+1"
    assert csv_safe("@SUM(A1)") == "'@SUM(A1)"
    assert csv_safe("-5") == "'-5" and csv_safe("+1") == "'+1"
    assert csv_safe("Rina") == "Rina" and csv_safe(None) == "" and csv_safe(7) == "7"
    out = to_csv(["a", "b"], [["=cmd", "x,y"]])
    assert out.splitlines()[1] == "'=cmd,\"x,y\""


def test_event_groups_are_known_and_activity_excludes_failures():
    flat = [e for g in events.GROUPS.values() for e in g]
    assert sorted(flat) == sorted(events.ALL_EVENTS)
    assert events.LOGIN in events.USER_ACTIVITY
    assert events.LOGIN_FAILED not in events.USER_ACTIVITY
    assert events.ADMIN_SUSPENDED not in events.USER_ACTIVITY


def test_clean_detail():
    assert events.clean_detail(None) is None and events.clean_detail("  \n ") is None
    assert events.clean_detail("a\nb\tc") == "a b c"
    assert len(events.clean_detail("x" * 500)) == 300
