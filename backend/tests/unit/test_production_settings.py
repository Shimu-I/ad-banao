import pytest

from app.core.config import Settings, check_production_settings

GOOD = dict(
    app_env="production",
    frontend_origin="https://app.example.com",
    database_url="postgresql://u:strongpass@db.example.com/adbanao",
)


def make(**over):
    return Settings(_env_file=None, **{**GOOD, **over})


def test_development_is_never_blocked():
    assert Settings(_env_file=None, app_env="development").production_problems() == []


def test_a_correct_production_setup_passes():
    check_production_settings(make())


@pytest.mark.parametrize(
    "over, word",
    [
        ({"frontend_origin": "http://app.example.com"}, "https"),
        ({"database_url": "sqlite:///x.db"}, "PostgreSQL"),
        ({"database_url": "postgresql://adbanao:adbanao@db/adbanao"}, "development password"),
        ({"admin_emails": "a@b.c"}, "ADMIN_EMAILS"),
    ],
)
def test_unsafe_production_values_stop_the_app(over, word):
    with pytest.raises(RuntimeError, match=word):
        check_production_settings(make(**over))
