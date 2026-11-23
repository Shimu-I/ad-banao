"""Admin commands for the person running the server.

    python -m app.cli make-admin   someone@example.com [--secret-word WORD]
    python -m app.cli set-secret   someone@example.com [--secret-word WORD]
    python -m app.cli remove-admin someone@example.com
    python -m app.cli list-admins

This is the way to create the first admin in production, where the ADMIN_EMAILS list is ignored.
The person must already have signed up. An admin signs in on the admin page with email,
password and a secret word; the word is stored only as a hash. Without --secret-word the
command asks for it (typing is hidden), which keeps it out of your shell history.
"""

import argparse
import getpass
import sys

from sqlalchemy import select

from app.db import activity
from app.db.models import User
from app.db.session import SessionLocal
from app.domain import events
from app.domain.roles import ROLE_ADMIN, ROLE_USER, secret_word_problem
from app.domain.security import hash_password, normalize_email


def _ask_secret() -> str | None:
    first = getpass.getpass("Secret word for the admin sign-in page: ")
    if first != getpass.getpass("Type it again: "):
        print("The two words are different.", file=sys.stderr)
        return None
    return first


def _set_secret(user: User, word: str | None) -> bool:
    word = (word if word is not None else _ask_secret()) or ""
    problem = secret_word_problem(word)
    if problem:
        print(problem, file=sys.stderr)
        return False
    user.admin_secret_hash = hash_password(word.strip())
    return True


def _make_admin(email: str, word: str | None) -> int:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == normalize_email(email)))
        if user is None:
            print(f"No user with email {email}. They must sign up first.", file=sys.stderr)
            return 1
        if (word is not None or not user.admin_secret_hash) and not _set_secret(user, word):
            return 1
        if user.role != ROLE_ADMIN:
            activity.record(
                db, events.ADMIN_ROLE_CHANGED, user.id, detail="user -> admin (command line)"
            )
            user.role = ROLE_ADMIN
        db.commit()
        print(f"{user.email} is an admin and can sign in on the admin page.")
        return 0


def _set_secret_cmd(email: str, word: str | None) -> int:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == normalize_email(email)))
        if user is None:
            print(f"No user with email {email}.", file=sys.stderr)
            return 1
        if user.role != ROLE_ADMIN:
            print("That user is not an admin. Use make-admin first.", file=sys.stderr)
            return 1
        if not _set_secret(user, word):
            return 1
        # Browsers verified with the old word are signed out of the admin area.
        for s in user.sessions:
            s.admin_verified = False
        db.commit()
        print(f"Secret word changed for {user.email}.")
        return 0


def _remove_admin(email: str) -> int:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == normalize_email(email)))
        if user is None:
            print(f"No user with email {email}.", file=sys.stderr)
            return 1
        if user.role == ROLE_USER:
            print(f"{user.email} is already a normal user.")
            return 0
        others = db.scalar(
            select(User.id)
            .where(User.role == ROLE_ADMIN, User.is_active.is_(True), User.id != user.id)
            .limit(1)
        )
        if others is None:
            print("Refusing: this is the last active admin.", file=sys.stderr)
            return 1
        activity.record(
            db, events.ADMIN_ROLE_CHANGED, user.id, detail="admin -> user (command line)"
        )
        user.role = ROLE_USER
        user.admin_secret_hash = None
        for s in user.sessions:
            s.admin_verified = False
        db.commit()
        print(f"{user.email} is now a normal user.")
        return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("make-admin", "set-secret"):
        p = sub.add_parser(name)
        p.add_argument("email")
        p.add_argument("--secret-word", default=None)
    sub.add_parser("remove-admin").add_argument("email")
    sub.add_parser("list-admins")
    args = parser.parse_args(argv)

    if args.cmd == "make-admin":
        return _make_admin(args.email, args.secret_word)
    if args.cmd == "set-secret":
        return _set_secret_cmd(args.email, args.secret_word)
    if args.cmd == "remove-admin":
        return _remove_admin(args.email)
    with SessionLocal() as db:
        for u in db.scalars(select(User).where(User.role == ROLE_ADMIN).order_by(User.id)):
            state = "active" if u.is_active else "suspended"
            print(f"{u.email}\t{state}\t{'secret word set' if u.admin_secret_hash else 'NO secret word'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
