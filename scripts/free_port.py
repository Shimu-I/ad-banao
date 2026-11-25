"""Stops AdBanao's own servers on the given TCP ports. Linux: reads /proc (no lsof needed).
Mac: uses lsof. Usage: python scripts/free_port.py 8000 5173

Anything else on a port (another project, a database tool) is left alone: the script says what it is
and exits with code 2 so the start script can tell you to close it yourself.
"""
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKERS = ("app.main:app", "serve_frontend.py", "multiprocessing.spawn")  # our API, our page server, and the API's auto-reload worker


def pids_linux(port):
    inodes = set()
    for f in ("/proc/net/tcp", "/proc/net/tcp6"):
        try:
            for line in open(f).read().splitlines()[1:]:
                p = line.split()
                if p[3] == "0A" and int(p[1].split(":")[1], 16) == port:  # 0A = LISTEN
                    inodes.add(p[9])
        except OSError:
            pass
    found = set()
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try:
            for fd in os.listdir(f"/proc/{pid}/fd"):
                if os.readlink(f"/proc/{pid}/fd/{fd}").strip("socket:[]") in inodes and inodes:
                    found.add(int(pid))
        except OSError:
            pass
    return found


def pids_lsof(port):
    out = subprocess.run(["lsof", "-ti", f"tcp:{port}", "-sTCP:LISTEN"], capture_output=True, text=True).stdout
    return {int(x) for x in out.split()}


def describe(pid):
    """(command line, working folder) of a process, or ("", "") if it cannot be read."""
    try:
        if os.path.isdir("/proc"):
            cmd = open(f"/proc/{pid}/cmdline").read().replace("\0", " ").strip()
            try:
                cwd = os.readlink(f"/proc/{pid}/cwd")
            except OSError:
                cwd = ""
            return cmd, cwd
        out = subprocess.run(["ps", "-o", "command=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()
        return out, ""
    except OSError:
        return "", ""


def is_adbanao(cmd, cwd=""):
    """True only for our own API or page server (so a different project's server is never touched)."""
    if not any(m in cmd for m in MARKERS):
        return False
    return str(ROOT) in cmd or str(ROOT) in cwd


def stop(pid):
    try:
        os.kill(pid, signal.SIGTERM)  # polite first
    except OSError:
        return
    for _ in range(30):
        time.sleep(0.1)
        try:
            os.kill(pid, 0)
        except OSError:
            return
    try:
        os.kill(pid, signal.SIGKILL)
    except OSError:
        pass


def main(ports):
    blocked = False
    for port in ports:
        try:
            pids = pids_linux(port) if os.path.isdir("/proc") else pids_lsof(port)
        except FileNotFoundError:
            pids = set()
        for pid in pids - {os.getpid()}:
            cmd, cwd = describe(pid)
            if is_adbanao(cmd, cwd):
                stop(pid)
                print(f"Port {port}: stopped the old AdBanao server (pid {pid}).")
            else:
                blocked = True
                print(f"Port {port} is used by another program (pid {pid}: {cmd[:80] or 'unknown'}).")
                print("  I did not touch it. Close that program yourself, then start AdBanao again.")
    return 2 if blocked else 0


if __name__ == "__main__":
    sys.exit(main([int(a) for a in sys.argv[1:]]))
