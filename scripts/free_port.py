"""Stops whatever is listening on the given TCP ports. Linux: reads /proc (no lsof needed).
Mac: uses lsof. Usage: python scripts/free_port.py 8000 5173"""
import os
import signal
import subprocess
import sys


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


for arg in sys.argv[1:]:
    port = int(arg)
    try:
        pids = pids_linux(port) if os.path.isdir("/proc") else pids_lsof(port)
    except FileNotFoundError:
        pids = set()
    for pid in pids - {os.getpid()}:
        try:
            os.kill(pid, signal.SIGKILL)
            print(f"Port {port} was busy, freed it (pid {pid}).")
        except OSError:
            pass
