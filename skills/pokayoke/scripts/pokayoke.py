#!/usr/bin/env python3
"""POKAYOKE — a sign can be ignored; a lock can't. Every rule needs both.  (POKA-MON, principle 6)

For each `pairing` in jig.json, checks that the DECLARATION (a rule written in a document) and the
ENFORCEMENT (a setting, hook, or deny-list that makes the rule physically hold) are BOTH present.
  sign without lock  -> the rule is written but nothing enforces it (the most dangerous state)
  lock without sign  -> something is enforced and nobody knows why

Exit codes: 0 = every pairing intact   1 = a pairing is broken   2 = config error
"""
import argparse, json, os, sys, tempfile

EXIT_PASS, EXIT_FAIL, EXIT_CONFIG = 0, 1, 2


def load_config(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        sys.exit(f"config error: {path} not found (copy jig.example.json to jig.json)")
    except json.JSONDecodeError as e:
        sys.exit(f"config error: {path}: {e}")


def present(root, side):
    p = os.path.join(root, side["file"])
    if not os.path.exists(p):
        return False
    needle = side.get("contains")
    if not needle:
        return True
    try:
        return needle in open(p, encoding="utf-8", errors="replace").read()
    except OSError:
        return False


def check(cfg, root="."):
    findings = []
    for pr in cfg.get("pairings", []):
        name = pr.get("name", pr["declaration"]["file"])
        d, e = present(root, pr["declaration"]), present(root, pr["enforcement"])
        if d and e:
            findings.append(("ok", name, f"sign {pr['declaration']['file']} + lock {pr['enforcement']['file']}"))
        elif d and not e:
            findings.append(("fail", name, f"SIGN WITHOUT LOCK — declared in {pr['declaration']['file']} but {pr['enforcement']['file']} does not enforce it"))
        elif e and not d:
            findings.append(("fail", name, f"LOCK WITHOUT SIGN — enforced in {pr['enforcement']['file']} but not declared in {pr['declaration']['file']}"))
        else:
            findings.append(("fail", name, "neither declaration nor enforcement present"))
    return findings


def selftest():
    n = 0
    with tempfile.TemporaryDirectory() as d:
        def w(name, text):
            open(os.path.join(d, name), "w", encoding="utf-8").write(text)
        pairing = {"name": "p", "declaration": {"file": "RULES.md", "contains": "no external hosting"},
                   "enforcement": {"file": "settings.json", "contains": "\"Artifact\""}}
        cfg = {"pairings": [pairing]}
        w("RULES.md", "policy: no external hosting\n"); w("settings.json", '{"deny": ["Artifact"]}')
        assert check(cfg, d)[0][0] == "ok"; n += 1
        w("settings.json", '{"deny": []}')
        f = check(cfg, d); assert f[0][0] == "fail" and "SIGN WITHOUT LOCK" in f[0][2]; n += 1
        w("settings.json", '{"deny": ["Artifact"]}'); w("RULES.md", "policy: nothing\n")
        f = check(cfg, d); assert "LOCK WITHOUT SIGN" in f[0][2]; n += 1
        os.remove(os.path.join(d, "RULES.md")); os.remove(os.path.join(d, "settings.json"))
        f = check(cfg, d); assert "neither" in f[0][2]; n += 1
    print(f"pokayoke selftest: {n} checks OK")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default="jig.json")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    cfg = load_config(a.config)
    findings = check(cfg)
    for level, name, msg in findings:
        print(f"{'OK  ' if level == 'ok' else 'FAIL'} {name}: {msg}")
    if not findings:
        print("POKAYOKE: no pairings registered (add some, or KARAPPO will flag this registry as hollow)")
    return EXIT_FAIL if any(l == "fail" for l, _, _ in findings) else EXIT_PASS


if __name__ == "__main__":
    sys.exit(main())
