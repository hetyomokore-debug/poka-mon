#!/usr/bin/env python3
"""NAMAMONO — hand-written tables rot; generate them and stop when they differ.  (POKA-MON, principle 4)

For each `generated` entry in jig.json, runs the generator (with {out} substituted by a temp path)
and compares the result byte-for-byte with the committed target.  Any difference is STALE.
`--refresh` overwrites a stale target — but only after copying its current bytes to `<log dir>/backup/<UTC ts>/<target>`
(reversibility: one move to undo). The backup path is printed with the result.

Exit codes: 0 = all fresh (or refreshed with --refresh)   1 = stale   2 = config error or generator failed
"""
import argparse, datetime, json, os, shlex, shutil, subprocess, sys, tempfile

EXIT_PASS, EXIT_FAIL, EXIT_CONFIG = 0, 1, 2


def load_config(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        sys.exit(f"config error: {path} not found (copy jig.example.json to jig.json)")
    except json.JSONDecodeError as e:
        sys.exit(f"config error: {path}: {e}")


def backup_copy(target_rel, root, backup_root):
    """Copy the current bytes of a target aside before overwriting it. Returns the copy's path relative to root."""
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rel = os.path.join(backup_root, ts, target_rel)
    dst = os.path.join(root, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(os.path.join(root, target_rel), dst)
    return rel


def check(cfg, root=".", refresh=False):
    stale, errors, fresh = [], [], []
    backup_root = os.path.join(os.path.dirname(cfg.get("log", ".jig/gate_log.jsonl")) or ".jig", "backup")
    for g in cfg.get("generated", []):
        target = os.path.join(root, g["target"])
        fd, out = tempfile.mkstemp(suffix=".gen"); os.close(fd)
        try:
            p = subprocess.run(g["cmd"].replace("{out}", shlex.quote(out)), shell=True, capture_output=True, text=True, cwd=root)
            if p.returncode != 0:
                errors.append((g["target"], f"generator exit {p.returncode}: {(p.stderr.strip() or p.stdout.strip())[-160:]}")); continue
            new = open(out, "rb").read()
            cur = open(target, "rb").read() if os.path.exists(target) else None
            if cur == new:
                fresh.append(g["target"])
            elif refresh:
                os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
                bak = backup_copy(g["target"], root, backup_root) if cur is not None else None
                open(target, "wb").write(new)
                fresh.append(g["target"] + (f" (refreshed; previous bytes saved to {bak})" if bak else " (created)"))
            else:
                stale.append((g["target"], "missing" if cur is None else "differs from regenerated output"))
        finally:
            os.unlink(out)
    return stale, errors, fresh


def selftest():
    n = 0
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "docs"))
        cfg = {"generated": [{"target": "docs/t.md", "cmd": "printf 'hello\\n' > {out}"}]}
        s, e, f = check(cfg, d); assert s and s[0][1] == "missing" and not e; n += 1
        open(os.path.join(d, "docs", "t.md"), "w").write("old\n")
        s, e, f = check(cfg, d); assert s and "differs" in s[0][1]; n += 1
        s, e, f = check(cfg, d, refresh=True); assert not s and f[0].startswith("docs/t.md (refreshed; previous bytes saved to "); n += 1
        bak = f[0].split("saved to ", 1)[1].rstrip(")")
        assert open(os.path.join(d, bak), encoding="utf-8").read() == "old\n"; n += 1   # A3: the overwritten bytes survive, one copy away
        assert open(os.path.join(d, "docs", "t.md")).read() == "hello\n"; n += 1
        os.remove(os.path.join(d, "docs", "t.md"))
        s, e, f = check(cfg, d, refresh=True); assert f == ["docs/t.md (created)"]; n += 1   # nothing to back up when the target did not exist
        s, e, f = check(cfg, d); assert not s and f == ["docs/t.md"]; n += 1
        s, e, f = check({"generated": [{"target": "docs/t.md", "cmd": "exit 4"}]}, d); assert e and "exit 4" in e[0][1]; n += 1
    print(f"namamono selftest: {n} checks OK")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default="jig.json")
    ap.add_argument("--refresh", action="store_true", help="overwrite stale targets with regenerated output (previous bytes are copied to <log dir>/backup/<ts>/ first)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    cfg = load_config(a.config)
    stale, errors, fresh = check(cfg, refresh=a.refresh)
    for t in fresh:
        print(f"FRESH {t}")
    for t, why in stale:
        print(f"STALE {t} — {why} (regenerate, or run with --refresh)")
    for t, why in errors:
        print(f"ERROR {t} — {why}")
    if errors:
        return EXIT_CONFIG
    return EXIT_FAIL if stale else EXIT_PASS


if __name__ == "__main__":
    sys.exit(main())
