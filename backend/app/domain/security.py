"""Password hashing and session tokens. Pure functions, standard library only.

Passwords use scrypt with a random salt per password. Session tokens are random and
only their SHA-256 hash is stored, so a copy of the database cannot be used to sign in.
"""

import base64
import hashlib
import hmac
import re
import secrets

_N, _R, _P = 2**14, 8, 1
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

PASSWORD_MIN = 8
PASSWORD_MAX = 128


def normalize_email(email: str) -> str:
    return email.strip().lower()


def is_valid_email(email: str) -> bool:
    return len(email) <= 254 and bool(_EMAIL.match(email))


def password_problem(password: str, email: str = "") -> str | None:
    """Return a plain-language reason the password is not acceptable, or None."""
    if len(password) < PASSWORD_MIN:
        return f"Password must be at least {PASSWORD_MIN} characters."
    if len(password) > PASSWORD_MAX:
        return f"Password must be at most {PASSWORD_MAX} characters."
    if email and password.lower() == email.lower():
        return "Password must not be the same as your email."
    if password.isdigit() or len(set(password)) < 3:
        return "Password is too easy to guess. Mix letters and numbers."
    return None


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=32)
    return f"scrypt${_N}${_R}${_P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt, digest = stored.split("$")
        if scheme != "scrypt":
            return False
        expected = base64.b64decode(digest)
        actual = hashlib.scrypt(
            password.encode(),
            salt=base64.b64decode(salt),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


# Used when the email is unknown, so a login attempt takes about the same time either way.
DUMMY_HASH = hash_password(secrets.token_urlsafe(8))


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
