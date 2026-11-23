"""Names of the things we record in the activity log. Pure data and tiny helpers."""

SIGNUP = "signup"
LOGIN = "login"
LOGIN_FAILED = "login_failed"
LOGIN_BLOCKED = "login_blocked"  # right password, but the account is suspended
LOGOUT = "logout"
PASSWORD_CHANGED = "password_changed"
PROFILE_UPDATED = "profile_updated"
BRAND_CREATED = "brand_created"
BRAND_UPDATED = "brand_updated"
BRAND_ARCHIVED = "brand_archived"
BRAND_RESTORED = "brand_restored"
PRODUCT_CREATED = "product_created"
PRODUCT_UPDATED = "product_updated"
PRODUCT_ARCHIVED = "product_archived"
PRODUCT_RESTORED = "product_restored"
ADMIN_ROLE_CHANGED = "admin_role_changed"
ADMIN_SUSPENDED = "admin_suspended"
ADMIN_REACTIVATED = "admin_reactivated"
ADMIN_SIGNED_OUT_USER = "admin_signed_out_user"
ADMIN_LOGIN = "admin_login"
ADMIN_LOGIN_FAILED = "admin_login_failed"

ALL_EVENTS = (
    SIGNUP, LOGIN, LOGIN_FAILED, LOGIN_BLOCKED, LOGOUT, PASSWORD_CHANGED, PROFILE_UPDATED,
    BRAND_CREATED, BRAND_UPDATED, BRAND_ARCHIVED, BRAND_RESTORED,
    PRODUCT_CREATED, PRODUCT_UPDATED, PRODUCT_ARCHIVED, PRODUCT_RESTORED,
    ADMIN_ROLE_CHANGED, ADMIN_SUSPENDED, ADMIN_REACTIVATED, ADMIN_SIGNED_OUT_USER,
    ADMIN_LOGIN, ADMIN_LOGIN_FAILED,
)  # fmt: skip

# Filter groups shown in the admin page.
GROUPS: dict[str, tuple[str, ...]] = {
    "signin": (LOGIN, LOGIN_FAILED, LOGIN_BLOCKED, LOGOUT, SIGNUP),
    "content": (
        BRAND_CREATED, BRAND_UPDATED, BRAND_ARCHIVED, BRAND_RESTORED,
        PRODUCT_CREATED, PRODUCT_UPDATED, PRODUCT_ARCHIVED, PRODUCT_RESTORED,
    ),  # fmt: skip
    "account": (PASSWORD_CHANGED, PROFILE_UPDATED),
    "admin": (
        ADMIN_ROLE_CHANGED, ADMIN_SUSPENDED, ADMIN_REACTIVATED, ADMIN_SIGNED_OUT_USER,
        ADMIN_LOGIN, ADMIN_LOGIN_FAILED,
    ),  # fmt: skip
}

# Events that show a person actually used the product. Failed or blocked sign-ins and things
# an admin did *to* someone do not make that person "active".
_NOT_USER_ACTIVITY = {LOGIN_FAILED, LOGIN_BLOCKED, *GROUPS["admin"]}
USER_ACTIVITY = tuple(e for e in ALL_EVENTS if e not in _NOT_USER_ACTIVITY)

# Events that count as an "action" in the Top users list (work done, not just signing in).
ACTIONS = (*GROUPS["content"], PASSWORD_CHANGED, PROFILE_UPDATED)


def clean_detail(text: str | None, limit: int = 300) -> str | None:
    """Single line, no control characters, shortened. Never raises."""
    if not text:
        return None
    one_line = " ".join("".join(ch if ch.isprintable() else " " for ch in text).split())
    if not one_line:
        return None
    return one_line if len(one_line) <= limit else one_line[: limit - 1] + "…"
