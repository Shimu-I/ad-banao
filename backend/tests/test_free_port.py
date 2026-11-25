"""free_port.py must only ever stop AdBanao's own servers."""
import importlib.util
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "free_port.py"


def load():
    spec = importlib.util.spec_from_file_location("free_port", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_recognises_our_servers_only():
    fp = load()
    assert fp.is_adbanao(f"{ROOT}/.venv/bin/python -m uvicorn app.main:app --port 8000")
    assert fp.is_adbanao(f"{ROOT}/.venv/bin/python scripts/serve_frontend.py 5173")
    assert not fp.is_adbanao("/usr/bin/python3 -m uvicorn app.main:app --port 8000")  # someone else's project
    assert not fp.is_adbanao("postgres: main")
    assert not fp.is_adbanao("python -m http.server 5173")


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_a_foreign_program_is_left_running():
    port = free_port()
    other = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            time.sleep(0.1)
            with socket.socket() as s:
                if s.connect_ex(("127.0.0.1", port)) == 0:
                    break
        r = subprocess.run([sys.executable, str(SCRIPT), str(port)], capture_output=True, text=True)
        assert r.returncode == 2
        assert "did not touch it" in r.stdout
        assert other.poll() is None  # still running
    finally:
        other.kill()
        other.wait()


def test_our_own_page_server_is_stopped():
    port = free_port()
    ours = subprocess.Popen([sys.executable, str(ROOT / "scripts" / "serve_frontend.py"), str(port), "127.0.0.1"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            time.sleep(0.1)
            with socket.socket() as s:
                if s.connect_ex(("127.0.0.1", port)) == 0:
                    break
        r = subprocess.run([sys.executable, str(SCRIPT), str(port)], capture_output=True, text=True)
        assert r.returncode == 0, r.stdout
        assert "stopped the old AdBanao server" in r.stdout
        ours.wait(timeout=5)
    finally:
        if ours.poll() is None:
            ours.kill()
