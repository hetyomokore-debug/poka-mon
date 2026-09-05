#!/usr/bin/env python3
"""SAKIGAKI — the contract comes before the code.  (POKA-MON, principle 3)

Two checks:
  --changed FILES     every changed source file must be named as a producer (or consumer) in a jig.json contract,
                      and every touched contract must have `requirements` and a `guard_test` that exists on disk.
  --expect-red --cmd  run the guard test and PASS only if it FAILS (red before implementation).

Exit codes: 0 = pass   1 = violation (write the contract / put the failing test first)   2 = config/usage error
"""
import argparse, fnmatch, json, os, shlex, subprocess, sys, tempfile

EXIT_PASS, EXIT_FAIL, EXIT_CONFIG = 0, 1, 2
DEFAULT_CODE_EXT = [".py", ".js", ".ts", ".tsx", ".go", ".rs", ".rb", ".java", ".kt", ".swift", ".sh"]
DEFAULT_TEST_PATHS = ["tests/**", "test/**", "**/test_*", "**/*_test.*", "**/*.test.*", "**/*.spec.*"]


def load_config(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        sys.exit(f"config error: {path} not found (copy jig.example.json to jig.json)")
    except json.JSONDecodeError as e:
        sys.exit(f"config error: {path}: {e}")


def matches(path, pat):
    path = path.replace(os.sep, "/")
    if pat.endswith("/**"):
        base = pat[:-3].rstrip("/")
        return path == base or path.startswith(base + "/")
    if pat.startswith("**/"):
        tail = pat[3:]
        parts = path.split("/")
        return any(fnmatch.fnmatch("/".join(parts[i:]), tail) for i in range(len(parts)))
    return path == pat or fnmatch.fnmatch(path, pat)


def _as_file(x):
    """A producer/consumer entry is a path string, or an object with a `file` key (registry style)."""
    return x.get("file", "") if isinstance(x, dict) else (x or "")


def normalize_contract(c):
    """Accept two shapes: the jig.example.json shape, and the registry shape older contract checkers use
    (`name` for `id`; `producer: {file, fields}`; `consumers: [{file, reads}]`). Extra keys are kept and ignored."""
    prod = c.get("producer", "")
    return {**c,
            "id": c.get("id") or c.get("name") or _as_file(prod),
            "producer": _as_file(prod),
            "consumers": [_as_file(x) for x in (c.get("consumers") or [])],
            "fields": list(c.get("fields") or (prod.get("fields") if isinstance(prod, dict) else None) or []),
            "business_critical": bool(c.get("business_critical", False))}


def load_contracts(cfg, root="."):
    """`contracts` is a list (or a single string). A string entry names a registry JSON file, relative to root,
    whose top-level `contracts` list is included — so an existing registry stays the single source of truth
    instead of being copied into jig.json by hand (NAMAMONO)."""
    src = cfg.get("contracts", [])
    out = []
    for entry in ([src] if isinstance(src, str) else src):
        if not isinstance(entry, str):
            out.append(normalize_contract(entry)); continue
        try:
            with open(os.path.join(root, entry), encoding="utf-8") as f:
                reg = json.load(f)
        except FileNotFoundError:
            sys.exit(f"config error: contracts registry {entry} not found")
        except json.JSONDecodeError as e:
            sys.exit(f"config error: contracts registry {entry}: {e}")
        items = reg.get("contracts") if isinstance(reg, dict) else reg
        if not isinstance(items, list):
            sys.exit(f"config error: contracts registry {entry} has no `contracts` list")
        out.extend(normalize_contract(c) for c in items)
    return out


def guard_file(gt):
    """`guard_test` is a path, or a command such as `qa/check.py --selftest`; the first token is the file that must exist."""
    try:
        return shlex.split(gt)[0]
    except (ValueError, IndexError):
        return gt


def check(cfg, changed, root="."):
    contracts = load_contracts(cfg, root)
    code_ext = tuple(cfg.get("code_extensions", DEFAULT_CODE_EXT))
    a_paths, test_paths = cfg.get("track_a_paths", []), cfg.get("test_paths", DEFAULT_TEST_PATHS)
    v = []
    for f in changed:
        if any(matches(f, p) for p in a_paths) or any(matches(f, p) for p in test_paths):
            continue
        producing = [c for c in contracts if matches(f, c.get("producer", ""))]
        consuming = [c for c in contracts if any(matches(f, x) for x in c.get("consumers", []))]
        if not producing:
            if not consuming and f.endswith(code_ext):
                v.append(f"{f}: no contract names this file as a producer or consumer — write the contract first")
            continue
        for c in producing:
            if not c.get("requirements"):
                v.append(f"{c['id']}: contract has no `requirements` — which requirement does this serve?")
            gt = c.get("guard_test")
            if not gt:
                v.append(f"{c['id']}: contract has no `guard_test` — put the failing test in place first")
            elif not os.path.exists(os.path.join(root, guard_file(gt))):
                v.append(f"{c['id']}: guard_test {gt} does not exist on disk")
    return v


def expect_red(cmd, root="."):
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=root)
    return p.returncode != 0


def selftest():
    n = 0
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "tests")); open(os.path.join(d, "tests", "test_a.py"), "w").close()
        cfg = {"contracts": [
            {"id": "c1", "producer": "src/a.py", "consumers": ["src/ui.js"], "requirements": ["R-1"], "guard_test": "tests/test_a.py"},
            {"id": "c2", "producer": "src/b.py", "consumers": [], "requirements": [], "guard_test": "tests/test_b.py"}]}
        assert check(cfg, ["src/a.py"], d) == []; n += 1
        assert check(cfg, ["src/ui.js"], d) == []; n += 1                       # consumer-only change is fine
        assert check(cfg, ["tests/test_new.py"], d) == []; n += 1               # tests are not producers
        assert check(cfg, ["README.md"], d) == []; n += 1                       # not code
        assert len(check(cfg, ["src/new.py"], d)) == 1; n += 1                  # code with no contract
        vb = check(cfg, ["src/b.py"], d); assert len(vb) == 2 and "requirements" in vb[0] and "does not exist" in vb[1]; n += 1
        assert expect_red("exit 1", d) and not expect_red("true", d); n += 1
        # registry shape, referenced by path, with a guard_test that is a command (first token must exist)
        os.makedirs(os.path.join(d, "qa")); open(os.path.join(d, "qa", "check.py"), "w").close()
        reg = {"contracts": [{"name": "gov", "producer": {"file": "qa/reg.json", "fields": ["a"]},
                              "consumers": [{"file": "qa/check.py", "reads": ["a"]}],
                              "guard_test": "qa/check.py --selftest", "requirements": ["G-1"]}]}
        json.dump(reg, open(os.path.join(d, "registry.json"), "w", encoding="utf-8"))
        assert check({"contracts": ["registry.json"]}, ["qa/reg.json"], d) == []; n += 1
        assert check({"contracts": ["registry.json"]}, ["qa/check.py"], d) == []; n += 1      # consumer-only
        assert guard_file("qa/check.py --selftest") == "qa/check.py" and guard_file("tests/t.py") == "tests/t.py"; n += 1
        vm = check({"contracts": [{"id": "c", "producer": "qa/reg.json", "requirements": ["R"], "guard_test": "qa/missing.py --selftest"}]}, ["qa/reg.json"], d)
        assert len(vm) == 1 and "does not exist" in vm[0]; n += 1
    print(f"sakigaki selftest: {n} checks OK")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--changed", nargs="*", help="changed files")
    ap.add_argument("--expect-red", action="store_true", help="run --cmd and pass only if it fails")
    ap.add_argument("--cmd", help="guard test command for --expect-red")
    ap.add_argument("--config", default="jig.json")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if a.expect_red:
        if not a.cmd:
            ap.error("--expect-red requires --cmd")
        if expect_red(a.cmd):
            print(f"SAKIGAKI red confirmed: `{a.cmd}` fails before implementation — proceed"); return EXIT_PASS
        print(f"SAKIGAKI FAIL: `{a.cmd}` is already green — the test was written after the code, so it cannot detect drift"); return EXIT_FAIL
    if a.changed is None:
        ap.error("--changed FILES or --expect-red --cmd is required (or --selftest)")
    cfg = load_config(a.config)
    v = check(cfg, a.changed)
    for line in v:
        print("SAKIGAKI FAIL " + line)
    if not v:
        print(f"SAKIGAKI ok: {len(a.changed)} file(s) covered by contracts with requirements and guard tests")
    return EXIT_FAIL if v else EXIT_PASS


if __name__ == "__main__":
    sys.exit(main())
