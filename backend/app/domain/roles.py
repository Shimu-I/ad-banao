"""Roles and the safeguards for changing them. Pure functions, no web or database imports."""

ROLE_USER = "user"
ROLE_ADMIN = "admin"
ROLES = (ROLE_USER, ROLE_ADMIN)

# Sign-up and sign-in only honor the ADMIN_EMAILS list in these environments.
# In production an admin is made on purpose with the command line (see docs/22-admin.md).
BOOTSTRAP_ENVS = ("development", "test")

DEMO_EMAIL_DOMAIN = "@demo.adbanao.test"


def parse_admin_emails(raw: str) -> frozenset[str]:
    """'A@x.com, b@y.com' -> {'a@x.com', 'b@y.com'}. Blank entries are ignored."""
    return frozenset(p.strip().lower() for p in (raw or "").split(",") if p.strip())


def is_bootstrap_admin(email: str, raw_list: str, app_env: str) -> bool:
    """True when this email is on the admin list and the environment allows the list."""
    if app_env not in BOOTSTRAP_ENVS:
        return False
    return email.strip().lower() in parse_admin_emails(raw_list)


def is_demo_email(email: str) -> bool:
    return email.strip().lower().endswith(DEMO_EMAIL_DOMAIN)


def role_change_problem(
    *,
    actor_id: int,
    target_id: int,
    target_role: str,
    target_active: bool,
    new_role: str,
    active_admins: int,
) -> str | None:
    """Reason an admin may not change this role, or None when it is allowed."""
    if new_role not in ROLES:
        return "Unknown role."
    if new_role == target_role:
        return None
    if actor_id == target_id:
        return "You cannot change your own role. Ask another admin."
    if target_role == ROLE_ADMIN and target_active and active_admins <= 1:
        return "This is the last active admin. Make another admin first."
    return None


def status_change_problem(
    *,
    actor_id: int,
    target_id: int,
    target_role: str,
    target_active: bool,
    new_active: bool,
    active_admins: int,
) -> str | None:
    """Reason an admin may not suspend or reactivate this account, or None."""
    if new_active == target_active:
        return None
    if not new_active:
        if actor_id == target_id:
            return "You cannot suspend your own account."
        if target_role == ROLE_ADMIN and active_admins <= 1:
            return "This is the last active admin. Make another admin first."
    return None
