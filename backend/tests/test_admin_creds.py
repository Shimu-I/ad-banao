"""The local admin login must never be written into the repository."""
import importlib.util
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load():
    spec = importlib.util.spec_from_file_location("admin_creds", ROOT / "scripts" / "_admin_creds.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_ensure_makes_random_values_once(tmp_path, monkeypatch):
    for k in ("ADBANAO_ADMIN_EMAIL", "ADBANAO_ADMIN_PASSWORD", "ADBANAO_ADMIN_SECRET"):
        monkeypatch.delenv(k, raising=False)
    mod, env = load(), tmp_path / ".env"
    assert mod.ensure(env) is True
    first = mod.load(env)
    assert all(first) and first[1] != first[2]
    assert mod.ensure(env) is False  # second run keeps the same login
    assert mod.load(env) == first


def test_old_published_login_is_replaced(tmp_path, monkeypatch):
    for k in ("ADBANAO_ADMIN_EMAIL", "ADBANAO_ADMIN_PASSWORD", "ADBANAO_ADMIN_SECRET"):
        monkeypatch.delenv(k, raising=False)
    mod, env = load(), tmp_path / ".env"
    env.write_text("ADBANAO_ADMIN_EMAIL=admin@admin-adbanao.com\nADBANAO_ADMIN_PASSWORD=x\nADBANAO_ADMIN_SECRET=y\n")
    assert mod.ensure(env) is True
    assert mod.load(env)[0] not in mod.LEAKED_EMAILS


def test_old_login_text_is_not_in_the_repository():
    files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    needles = ("admin-aa-bb-demo", "nov-25-uuuuu")
    for name in files:
        path = ROOT / name
        if path.suffix in {".py", ".md", ".sh", ".ps1", ".txt", ".yml", ".html"} and path.is_file():
            text = path.read_text(errors="ignore")
            if path.name in {"test_admin_creds.py", "check_start_scripts.sh"}:  # they name the old text on purpose
                continue
            assert not any(n in text for n in needles), name
