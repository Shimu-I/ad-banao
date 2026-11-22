"""Small admin commands.   python -m app.cli make-admin someone@example.com"""

import sys

from sqlalchemy import select

from app.db.models import User
from app.db.session import SessionLocal
from app.domain.security import normalize_email


def _set_role(email: str, role: str) -> int:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == normalize_email(email)))
        if user is None:
            print(f"No user with email {email}. They must sign up first.")
            return 1
        user.role = role
        db.commit()
        print(f"{user.email} is now {role}.")
        return 0


def main(argv: list[str]) -> int:
    if len(argv) == 3 and argv[1] in ("make-admin", "remove-admin"):
        return _set_role(argv[2], "admin" if argv[1] == "make-admin" else "user")
    print("Usage: python -m app.cli make-admin EMAIL | remove-admin EMAIL")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
