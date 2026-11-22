"""Names of the events that are written to the activity log, and the rules around them."""

SIGNED_UP = "signed_up"
SIGNED_IN = "signed_in"
SIGN_IN_FAILED = "sign_in_failed"
SIGNED_OUT = "signed_out"
PROFILE_UPDATED = "profile_updated"
PASSWORD_CHANGED = "password_changed"
BRAND_CREATED = "brand_created"
PRODUCT_CREATED = "product_created"
PHOTO_UPLOADED = "photo_uploaded"
TEXT_GENERATED = "text_generated"
ADMIN_ACTION = "admin_action"

ALL_EVENTS = [
    SIGNED_UP,
    SIGNED_IN,
    SIGN_IN_FAILED,
    SIGNED_OUT,
    PROFILE_UPDATED,
    PASSWORD_CHANGED,
    BRAND_CREATED,
    PRODUCT_CREATED,
    PHOTO_UPLOADED,
    TEXT_GENERATED,
    ADMIN_ACTION,
]

ROLES = ("user", "admin")


def admin_email_set(raw: str) -> set[str]:
    """Parse the ADMIN_EMAILS setting: comma separated, case-insensitive."""
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


def csv_safe(value: object) -> str:
    """Stop spreadsheet programs from running a cell as a formula (CSV injection)."""
    text = "" if value is None else str(value)
    if text[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + text
    return text
