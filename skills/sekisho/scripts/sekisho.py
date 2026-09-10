#!/usr/bin/env python3
"""SEKISHO — the checkpoint that only accepts exit code 0.  (POKA-MON, principle 2)

Runs the gates registered for a tier in jig.json, in order, and reports one line per gate.
A gate whose command refers to a script that is not installed is SKIPPED and LISTED — never silently dropped,
so a green run never pretends to have covered what it did not run.

Exit codes: 0 = all executed gates passed   1 = at least one gate failed   2 = config/usage error
"""
import argparse, datetime, json, os, shlex, subprocess, sys, tempfile, time

EXIT_PASS, EXIT_FAIL, EXIT_CONFIG = 0, 1, 2
PLUGIN_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))


def load_config(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        sys.exit(f"config error: {path} not found (copy jig.example.json to jig.json)")
    except json.JSONDecodeError as e:
        sys.exit(f"config error: {path}: {e}")


def append_log(cfg, record, root="."):
    p = os.path.join(root, cfg.get("log", ".jig/gate_log.jsonl"))
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
    record = {"ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), **record}
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def not_installed(gate, cmd, root):
    req = gate.get("requires")
    if req and not os.path.exists(os.path.join(root, req)):
        return f"requires {req}"
    for tok in shlex.split(cmd):
        if any(ch in tok for ch in "$*?{"):
            continue   # shell variable or glob: cannot be judged statically, so never excluded on that basis
        if "/" in tok and tok.endswith((".py", ".sh", ".mjs", ".js", ".rb")) and not os.path.exists(os.path.join(root, tok)) and not os.path.isabs(tok):
            return f"{tok} missing"
        if os.path.isabs(tok) and tok.endswith((".py", ".sh", ".mjs", ".js", ".rb")) and not os.path.exists(tok):
            return f"{tok} missing"
    return None


def plan(cfg, tier, changed, root=".", config_path="jig.json"):
    tiers = cfg.get("gates", {})
    if tier not in tiers:
        sys.exit(f"config error: tier '{tier}' not defined (available: {', '.join(tiers) or 'none'})")
    entries = []
    for g in tiers[tier]:
        base = g["cmd"].replace("{plugin}", PLUGIN_ROOT).replace("{config}", shlex.quote(config_path))
        cmd = base.replace("{changed}", " ".join(shlex.quote(f) for f in changed))
        # installed-ness is judged WITHOUT the changed files: a changed file that is gone (deleted, renamed,
        # rooted elsewhere) is not a missing script, and must not turn the gate into a SKIP
        entries.append({"name": g["name"], "cmd": cmd, "skip": not_installed(g, base.replace("{changed}", ""), root)})
    return entries


def run(entries, tier, root=".", timeout=600, out=print):
    results, failed, skipped = {}, [], []
    out(f"== SEKISHO tier={tier} ==")
    for e in entries:
        if e["skip"]:
            out(f"SKIP {e['name']} — not installed ({e['skip']})")
            results[e["name"]] = "skip"; skipped.append(e["name"]); continue
        t0 = time.time()
        try:
            p = subprocess.run(e["cmd"], shell=True, capture_output=True, text=True, cwd=root, timeout=timeout)
            rc, tail = p.returncode, ((p.stderr.strip() or p.stdout.strip()).splitlines() or [""])[-1]
        except subprocess.TimeoutExpired:
            rc, tail = -1, f"timeout after {timeout}s"
        dt = time.time() - t0
        if rc == 0:
            out(f"PASS {e['name']} ({dt:.1f}s)"); results[e["name"]] = "pass"
        else:
            out(f"FAIL {e['name']} ({dt:.1f}s): exit {rc} — {tail[:160]}"); results[e["name"]] = "fail"; failed.append(e["name"])
    if skipped:
        out(f"excluded as not installed: {len(skipped)} ({', '.join(skipped)}) — a green run does not cover these")
    npass = sum(1 for v in results.values() if v == "pass")
    out(f"=== {npass} PASS / {len(failed)} FAIL / {len(skipped)} SKIP (tier={tier}) ===")
    return results, failed, skipped


def selftest():
    n = 0
    with tempfile.TemporaryDirectory() as d:
        cfg = {"log": "log.jsonl", "gates": {"commit": [
            {"name": "ok", "cmd": "true"}, {"name": "bad", "cmd": "exit 3"},
            {"name": "gone", "cmd": "python3 tools/none.py"}, {"name": "needs", "cmd": "true", "requires": "tests"},
            {"name": "cfg", "cmd": "test -n {config}"},
            {"name": "loop", "cmd": "for s in a b; do echo skills/$s/scripts/$s.py; done"},
            {"name": "chg", "cmd": "true {changed}"}]}}
        entries = plan(cfg, "commit", ["gone/deleted.py"], root=d, config_path="my.json")
        assert entries[4]["cmd"] == "test -n my.json"; n += 1
        assert [e["skip"] is not None for e in entries] == [False, False, True, True, False, False, False]; n += 1   # $s is not a missing file; a deleted changed file is not a missing script
        assert entries[6]["cmd"] == "true gone/deleted.py"; n += 1
        lines = []
        results, failed, skipped = run(entries, "commit", root=d, out=lines.append)
        assert results == {"ok": "pass", "bad": "fail", "gone": "skip", "needs": "skip", "cfg": "pass", "loop": "pass", "chg": "pass"}; n += 1
        assert failed == ["bad"] and skipped == ["gone", "needs"]; n += 1
        assert any(l.startswith("excluded as not installed: 2") for l in lines); n += 1   # skipped gates are always listed
        assert lines[-1] == "=== 4 PASS / 1 FAIL / 2 SKIP (tier=commit) ==="; n += 1
        try:
            plan(cfg, "release", [], root=d); assert False
        except SystemExit as e:
            assert "tier 'release' not defined" in str(e); n += 1
        os.makedirs(os.path.join(d, "tests"))
        assert plan(cfg, "commit", [], root=d)[3]["skip"] is None; n += 1
    print(f"sekisho selftest: {n} checks OK")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tier", help="commit | pr | release (as defined in jig.json)")
    ap.add_argument("--changed", nargs="*", default=[], help="changed files, substituted into {changed}")
    ap.add_argument("--config", default="jig.json")
    ap.add_argument("--timeout", type=int, default=600, help="per-gate timeout in seconds")
    ap.add_argument("--dry-run", action="store_true", help="show what would run; execute nothing; log nothing")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.tier:
        ap.error("--tier is required (or use --selftest)")
    cfg = load_config(a.config)
    entries = plan(cfg, a.tier, a.changed, config_path=a.config)
    if a.dry_run:
        print(f"== SEKISHO tier={a.tier} (dry run) ==")
        for e in entries:
            print(("would skip " if e["skip"] else "would run  ") + f"{e['name']}: {e['cmd']}" + (f"  [{e['skip']}]" if e["skip"] else ""))
        return EXIT_PASS
    results, failed, skipped = run(entries, a.tier, timeout=a.timeout)
    append_log(cfg, {"jig": "sekisho", "tier": a.tier, "gates": results, "failed": failed, "unavailable": skipped, "changed": a.changed})
    return EXIT_FAIL if failed else EXIT_PASS


if __name__ == "__main__":
    sys.exit(main())
