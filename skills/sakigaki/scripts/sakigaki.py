#!/usr/bin/env python3
"""SAKIGAKI — the contract comes before the code.  (POKA-MON, principle 3)

Two checks:
  --changed FILES     every changed source file must be named as a producer (or consumer) in a jig.json contract,
                      and every touched contract must have `requirements` and a `guard_test` that exists on disk.
  --planned FILES     the same, for the files the change will create — checked before they exist (with or without --changed).
  --expect-red --cmd  run the guard test and PASS only if it FAILS (red before implementation).

Every path in --changed must exist on disk. If one does not (several paths joined into one argument, git's quoted
form of a non-ASCII path, a deleted file), no file is checked: every such path is printed and the exit code is 2. A gate that
reads a path which names nothing passes without having looked.

Every path in --planned must NOT exist yet, and must be a plain path: no whitespace, double quote, backslash or control
character. Nothing on disk can vouch for a file that is not there, so its text is all there is to check, and those
characters make it indistinguishable from several paths joined into one argument or from git's quoted form. Otherwise
no file is checked: every such path is printed with its reason and the exit code is 2.

Exit codes: 0 = pass   1 = violation (write the contract / put the failing test first)   2 = config/usage error, incl. a --changed path that does not exist or a --planned path that does
"""
import argparse, contextlib, fnmatch, io, json, os, shlex, subprocess, sys, tempfile

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


def missing_changed(changed, root="."):
    """--changed paths that do not exist on disk. A directory or a dangling symlink exists (git lists both);
    an empty argument does not (os.path.join(root, "") would otherwise resolve to the root itself)."""
    return [f for f in changed if not f or not os.path.lexists(os.path.join(root, f))]


def refusal(jig, missing, nothing):
    """What to print (to stderr) when --changed names paths that do not exist. The summary line comes last,
    so a caller that shows only the last line of output still shows why."""
    shown = ["  [" + f.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t") + "]" + ("" if f else "  (empty argument)")
             for f in missing]
    lines = [f"{jig}: --changed names {len(missing)} path(s) that do not exist on disk:", *shown,
             "Common causes:",
             "  - several paths joined into one argument (zsh does not split an unquoted $files), or git's quoted",
             '    form of a non-ASCII path ("docs/00_\\343\\203\\211.md"). In zsh, build an array and pass it quoted:',
             '      files=("${(@f)$(git -c core.quotepath=false diff --name-only BASE HEAD)}")',
             '      ... --changed "${files[@]}"',
             "  - a file deleted in the range rightly does not exist: leave it out with git diff --diff-filter=d"]
    if "" in missing:
        lines.append('  - an empty argument: "${(@f)$(...)}" of an empty output is one empty element; if nothing changed, omit --changed')
    return "\n".join(lines + [f"{jig} refused: {len(missing)} nonexistent path(s) in --changed; {nothing} (exit 2)"])


def unusable_planned(planned, root="."):
    """(path, reason) for each --planned path that cannot be planned: empty, already on disk (a directory or a dangling
    symlink counts, as for --changed), or not a plain path. A planned file does not exist yet, so nothing on disk can
    tell one path from several joined into one argument, or a name from git's quoted form of it: whitespace, a control
    character, a double quote or a backslash is refused rather than guessed at."""
    out = []
    for f in planned:
        if not f:
            out.append((f, "empty argument"))
        elif os.path.lexists(os.path.join(root, f)):
            out.append((f, "exists — an existing file goes in --changed"))
        elif any(ch.isspace() or ord(ch) < 32 or ord(ch) == 127 for ch in f):
            out.append((f, "whitespace or a control character — several paths joined into one argument?"))
        elif '"' in f or "\\" in f:
            out.append((f, "double quote or backslash — git's quoted form of a non-ASCII path? use git -c core.quotepath=false"))
    return out


def planned_refusal(bad):
    """What to print (to stderr) when --planned names paths that cannot be planned. Summary line last, as in refusal()."""
    shown = ["  [" + f.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t") + "]  (" + why + ")" for f, why in bad]
    lines = [f"SAKIGAKI: --planned names {len(bad)} path(s) that cannot be planned:", *shown,
             "A planned file does not exist yet, so its text is all there is to check: it must name nothing on disk",
             "and be a plain path. A file whose name needs whitespace, a double quote or a backslash: create it first,",
             "then pass it in --changed."]
    return "\n".join(lines + [f"SAKIGAKI refused: {len(bad)} unusable path(s) in --planned; no file was checked (exit 2)"])


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

    # --changed guard (REQ-CHG-1): every path in --changed must exist on disk, or nothing is checked.
    old_cwd = os.getcwd()
    injected = detected = valid_ok = valid = 0
    try:
        with tempfile.TemporaryDirectory() as d2:
            os.chdir(d2)
            open("README.md", "w").close(); open("CHANGELOG.md", "w").close()
            os.makedirs("src")
            open(os.path.join("src", "a.py"), "w").close()
            open(os.path.join("src", "new.py"), "w").close()
            os.makedirs("docs"); open(os.path.join("docs", "00_ド.md"), "w").close()
            os.makedirs("tests"); open(os.path.join("tests", "test_a.py"), "w").close()
            cfg2 = {"contracts": [{"id": "c1", "producer": "src/a.py", "consumers": [],
                                   "requirements": ["R-1"], "guard_test": "tests/test_a.py"}]}
            with open("jig.json", "w", encoding="utf-8") as f:
                json.dump(cfg2, f)

            # hole demonstration on check() itself (unchanged): a joined argument that happens to end
            # in a non-code extension slips past every producer/consumer test; split properly, the
            # same missing contract is found. This is why the guard below exists.
            assert check(cfg2, ["src/new.py README.md"], d2) == []; n += 1
            assert len(check(cfg2, ["src/new.py", "README.md"], d2)) == 1; n += 1

            def run_main(argv):
                out, err = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    try:
                        rc = main(argv)
                    except SystemExit as e:
                        rc = e.code
                return rc, out.getvalue(), err.getvalue()

            broken = [
                ("joined (zsh)", ["src/new.py README.md"], ["src/new.py README.md"]),
                ("quoted (git)", ['"docs/00_\\343\\203\\211.md"'], ['"docs/00_\\343\\203\\211.md"']),
                ("absent", ["src/gone.py"], ["src/gone.py"]),
                ("empty", [""], [""]),
                ("mixed", ["src/a.py", "src/gone.py"], ["src/gone.py"]),
            ]
            bad = []
            for name, case, missing in broken:
                injected += 1
                rc, out, err = run_main(["--config", "jig.json", "--changed", *case])
                errlines = err.splitlines()
                ok = (rc == 2 and "SAKIGAKI ok" not in out and "SAKIGAKI FAIL" not in out
                      and all(("[" + m + "]") in err for m in missing)
                      and (name != "mixed" or "[src/a.py]" not in err)
                      and bool(errlines) and errlines[-1].startswith("SAKIGAKI refused:"))
                detected += ok
                if not ok:
                    bad.append(name)
            assert detected == injected, f"sakigaki --changed guard did not stop these broken cases: {bad}"; n += 1

            valid = 2
            rc, out, err = run_main(["--config", "jig.json", "--changed", "src/a.py", "README.md", "docs/00_ド.md"])
            ok1 = rc == 0 and "SAKIGAKI ok" in out
            valid_ok += ok1
            if not ok1:
                bad.append("valid: covered files")

            rc, out, err = run_main(["--config", "jig.json", "--changed", "src/new.py", "README.md"])
            ok2 = rc == 1 and "SAKIGAKI FAIL src/new.py: no contract names this file" in out
            valid_ok += ok2
            if not ok2:
                bad.append("valid: missing contract")

            assert valid_ok == valid, f"sakigaki valid --changed inputs regressed: {bad}"; n += 1

            # direct helper checks
            assert missing_changed(["README.md", "", "src/gone.py", "src"], root=d2) == ["", "src/gone.py"]; n += 1
            os.symlink("nowhere", os.path.join(d2, "dangling"))
            assert missing_changed(["dangling"], root=d2) == []; n += 1

            os.chdir(old_cwd)
    finally:
        os.chdir(old_cwd)

    # --planned guard (REQ-CHG-2): a file the change will create cannot go in --changed (it does not exist yet), so it
    # is named in --planned — which must not name an existing file and must be a plain path, or nothing is checked.
    # A planned code file is held to the same contract rules as a changed one, before it exists.
    p_injected = p_refused = p_valid_ok = p_valid = 0
    try:
        with tempfile.TemporaryDirectory() as d3:
            os.chdir(d3)
            open("README.md", "w").close()
            os.makedirs("src"); open(os.path.join("src", "a.py"), "w").close()
            os.makedirs("tests"); open(os.path.join("tests", "test_c.py"), "w").close()
            with open("jig.json", "w", encoding="utf-8") as f:
                json.dump({"contracts": [
                    {"id": "c1", "producer": "src/a.py", "consumers": [], "requirements": ["R-1"], "guard_test": "tests/test_c.py"},
                    {"id": "c2", "producer": "src/c2.py", "consumers": ["src/a.py"], "requirements": ["R-2"], "guard_test": "tests/test_c.py"},
                    {"id": "c3", "producer": "src/c3.py", "consumers": [], "requirements": ["R-3"], "guard_test": "tests/test_c3.py"}]}, f)

            # each case: (name, argv after the config, paths the refusal must show, paths it must not show)
            broken = [
                ("exists", ["--planned", "README.md"], ["README.md"], []),
                ("empty", ["--planned", ""], [""], []),
                ("joined (zsh)", ["--planned", "src/new.py README.md"], ["src/new.py README.md"], []),
                ("joined, all new", ["--planned", "src/new.py docs/new.md"], ["src/new.py docs/new.md"], []),
                ("quoted (git)", ["--planned", '"docs/01_\\343\\203\\211.md"'], ['"docs/01_\\343\\203\\211.md"'], []),
                ("backslash", ["--planned", "src\\new.py"], ["src\\new.py"], []),
                ("control character", ["--planned", "src/a\tb.py"], ["src/a\\tb.py"], []),
                ("mixed", ["--planned", "src/c2.py", "README.md"], ["README.md"], ["src/c2.py"]),
                ("--changed still guarded", ["--changed", "src/gone.py", "--planned", "src/c2.py"], ["src/gone.py"], ["src/c2.py"]),
            ]
            bad = []
            for name, argv, shown, hidden in broken:
                p_injected += 1
                rc, out, err = run_main(["--config", "jig.json", *argv])
                errlines = err.splitlines()
                ok = (rc == 2 and "SAKIGAKI ok" not in out and "SAKIGAKI FAIL" not in out
                      and all(("[" + m + "]") in err for m in shown)
                      and not any(("[" + m + "]") in err for m in hidden)
                      and bool(errlines) and errlines[-1].startswith("SAKIGAKI refused:"))
                p_refused += ok
                if not ok:
                    bad.append(name)
            assert p_refused == p_injected, f"sakigaki --planned guard did not stop these broken cases: {bad}"; n += 1

            # each case: (name, argv after the config, expected exit code, text that must appear in stdout)
            valid_cases = [
                ("planned, contract in place", ["--changed", "src/a.py", "--planned", "src/c2.py"], 0, "SAKIGAKI ok: 2 file(s)"),
                ("planned, no contract", ["--planned", "src/nocontract.py"], 1, "SAKIGAKI FAIL src/nocontract.py: no contract names this file"),
                ("planned, guard test missing", ["--planned", "src/c3.py"], 1, "SAKIGAKI FAIL c3: guard_test tests/test_c3.py does not exist on disk"),
                ("planned, non-ASCII doc", ["--planned", "docs/新規.md"], 0, "SAKIGAKI ok: 1 file(s)"),
                ("planned, test file", ["--planned", "tests/test_new.py"], 0, "SAKIGAKI ok: 1 file(s)"),
            ]
            for name, argv, want_rc, want in valid_cases:
                p_valid += 1
                rc, out, err = run_main(["--config", "jig.json", *argv])
                ok = rc == want_rc and want in out
                p_valid_ok += ok
                if not ok:
                    bad.append("valid: " + name)
            assert p_valid_ok == p_valid, f"sakigaki valid --planned inputs misjudged: {bad}"; n += 1

            # direct helper check: each unusable path is reported with its reason, a usable one is not reported
            why = [w for _f, w in unusable_planned(["README.md", "", "src/x y.py", '"q.md"', "src/ok.py"], root=d3)]
            assert (len(why) == 4 and why[0].startswith("exists") and why[1].startswith("empty")
                    and why[2].startswith("whitespace") and why[3].startswith("double quote")), why; n += 1

            os.chdir(old_cwd)
    finally:
        os.chdir(old_cwd)

    print(f"sakigaki selftest: {n} checks OK — --changed guard: {injected} broken inputs injected, "
          f"{detected} refused before checking; {valid_ok}/{valid} valid inputs judged as expected; "
          f"--planned guard: {p_injected} broken inputs injected, {p_refused} refused before checking; "
          f"{p_valid_ok}/{p_valid} valid inputs judged as expected")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--changed", nargs="*", help="changed files (each must exist on disk)")
    ap.add_argument("--planned", nargs="*", help="files the change will create (each must NOT exist yet, and be a plain path)")
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
    if a.changed is None and a.planned is None:
        ap.error("--changed FILES and/or --planned FILES, or --expect-red --cmd, is required (or --selftest)")
    changed, planned = a.changed or [], a.planned or []
    gone, unusable = missing_changed(changed), unusable_planned(planned)
    if gone:
        print(refusal("SAKIGAKI", gone, "no file was checked"), file=sys.stderr)
    if unusable:
        print(planned_refusal(unusable), file=sys.stderr)
    if gone or unusable:
        return EXIT_CONFIG
    cfg = load_config(a.config)
    v = check(cfg, changed + planned)
    for line in v:
        print("SAKIGAKI FAIL " + line)
    if not v:
        print(f"SAKIGAKI ok: {len(changed) + len(planned)} file(s) covered by contracts with requirements and guard tests"
              + (f" ({len(planned)} planned, not on disk yet)" if planned else ""))
    return EXIT_FAIL if v else EXIT_PASS


if __name__ == "__main__":
    sys.exit(main())
