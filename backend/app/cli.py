"""Admin commands for the person running the server.

    python -m app.cli make-admin  someone@example.com
    python -m app.cli remove-admin someone@example.com
    python -m app.cli list-admins

This is the way to create the first admin in production, where the ADMIN_EMAILS list is ignored.
The person must already have signed up.
"""

import argparse
import sys

from sqlalchemy import select

from app.db import activity
from app.db.models import User
from app.db.session import SessionLocal
from app.domain import events
from app.domain.roles import ROLE_ADMIN, ROLE_USER
from app.domain.security import normalize_email


def _set_role(email: str, role: str) -> int:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == normalize_email(email)))
        if user is None:
            print(f"No user with email {email}. They must sign up first.", file=sys.stderr)
            return 1
        if user.role == role:
            print(f"{user.email} is already {role}.")
            return 0
        if role == ROLE_USER:
            others = db.scalar(
                select(User.id)
                .where(User.role == ROLE_ADMIN, User.is_active.is_(True), User.id != user.id)
                .limit(1)
            )
            if others is None:
                print("Refusing: this is the last active admin.", file=sys.stderr)
                return 1
        activity.record(
            db, events.ADMIN_ROLE_CHANGED, user.id, detail=f"{user.role} -> {role} (command line)"
        )
        user.role = role
        db.commit()
        print(f"{user.email} is now {role}.")
        return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("make-admin", "remove-admin"):
        sub.add_parser(name).add_argument("email")
    sub.add_parser("list-admins")
    args = parser.parse_args(argv)

    if args.cmd == "make-admin":
        return _set_role(args.email, ROLE_ADMIN)
    if args.cmd == "remove-admin":
        return _set_role(args.email, ROLE_USER)
    with SessionLocal() as db:
        for u in db.scalars(select(User).where(User.role == ROLE_ADMIN).order_by(User.id)):
            print(f"{u.email}\t{'active' if u.is_active else 'suspended'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
