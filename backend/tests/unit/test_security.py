from app.domain.security import (
    hash_password,
    hash_token,
    is_valid_email,
    new_session_token,
    normalize_email,
    password_problem,
    verify_password,
)


def test_hash_roundtrip_and_salt():
    a, b = hash_password("correct horse 9"), hash_password("correct horse 9")
    assert a != b  # random salt
    assert verify_password("correct horse 9", a)
    assert not verify_password("correct horse 8", a)


def test_verify_rejects_garbage_hash():
    assert not verify_password("x", "not-a-hash")
    assert not verify_password("x", "md5$1$2$3$4$5")
    assert not verify_password("x", "")


def test_token_hash_is_stable_and_not_the_token():
    t = new_session_token()
    assert hash_token(t) == hash_token(t) != t
    assert new_session_token() != t


def test_email_helpers():
    assert normalize_email("  Ana@Example.COM ") == "ana@example.com"
    assert is_valid_email("a@b.co")
    for bad in ("", "a", "a@b", "a b@c.com", "@b.com", "a@@b.com"):
        assert not is_valid_email(bad)


def test_password_rules():
    assert password_problem("short1") is not None
    assert password_problem("x" * 129) is not None
    assert password_problem("12345678") is not None
    assert password_problem("aaaaaaaa") is not None
    assert password_problem("me@x.com", "ME@x.com") is not None
    assert password_problem("blue-River-42") is None
