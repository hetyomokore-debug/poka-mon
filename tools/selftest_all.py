#!/usr/bin/env python3
"""Run every jig's --selftest. Exit 1 on the first failure. Used by the repository's own commit tier."""
import os, subprocess, sys

JIGS = ["hakari", "sekisho", "sakigaki", "namamono", "karappo", "pokayoke", "yamedoki"]
root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
for j in JIGS:
    p = subprocess.run([sys.executable, os.path.join(root, "skills", j, "scripts", f"{j}.py"), "--selftest"], capture_output=True, text=True)
    line = (p.stdout.strip() or p.stderr.strip()).splitlines()[-1:] or [""]
    print(("ok   " if p.returncode == 0 else "FAIL ") + line[0])
    if p.returncode != 0:
        sys.exit(1)
