#!/usr/bin/env python3
"""KARAPPO — the alarm that sounds when a check has nothing left to check.  (POKA-MON, principle 5)

A check that passes because its input became empty is not a checkpoint; it is decoration.
KARAPPO watches the registries the other jigs read (contracts, pairings, ...) and the gate log:
  - a registry below its `min` count           -> HOLLOW (exit 3, distinct from a normal FAIL)
  - a registry path that no longer exists       -> HOLLOW
  - the last gate run executed zero gates       -> HOLLOW (everything was skipped)

Exit codes: 0 = ok   2 = config error   3 = HOLLOW
"""
import argparse, json, os, sys, tempfile

EXIT_OK, EXIT_CONFIG, EXIT_HOLLOW = 0, 2, 3


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_path(obj, dotted):
    for part in dotted.split("."):
        if isinstance(obj, list):
            obj = obj[int(part)]
        else:
            obj = obj[part]
    return obj


def check(cfg, root="."):
    findings = []   # (level, name, message); level in {"hollow", "error"}
    for h in cfg.get("hollow", []):
        name, file = h.get("name", h.get("file")), os.path.join(root, h["file"])
        try:
            data = load_json(file)
        except FileNotFoundError:
            findings.append(("error", name, f"{h['file']} not found")); continue
        except json.JSONDecodeError as e:
            findings.append(("error", name, f"{h['file']}: {e}")); continue
        try:
            items = get_path(data, h["path"])
        except (KeyError, IndexError, ValueError, TypeError):
            findings.append(("hollow", name, f"path '{h['path']}' missing in {h['file']} — the registry has nothing to check")); continue
        if isinstance(items, str):
            findings.append(("error", name, f"path '{h['path']}' in {h['file']} is a reference ({items!r}), not a registry — point `hollow` at that file itself")); continue
        count = len(items) if isinstance(items, (list, dict)) else 1
        if count < int(h.get("min", 1)):
            findings.append(("hollow", name, f"{count} entries < min {h.get('min', 1)} — delete-to-green or never populated"))
    log = os.path.join(root, cfg.get("log", ".jig/gate_log.jsonl"))
    if os.path.exists(log):
        last = None
        for line in open(log, encoding="utf-8"):
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("jig") == "sekisho":
                last = rec
        if last is not None and not any(v in ("pass", "fail") for v in last.get("gates", {}).values()):
            findings.append(("hollow", "gate_log", f"last gate run (tier={last.get('tier')}) executed zero gates — everything was skipped"))
    return findings


def selftest():
    n = 0
    with tempfile.TemporaryDirectory() as d:
        reg = os.path.join(d, "jig.json")
        json.dump({"contracts": [1, 2], "pairings": []}, open(reg, "w"))
        cfg = {"log": "log.jsonl", "hollow": [{"name": "contracts", "file": "jig.json", "path": "contracts", "min": 1}]}
        assert check(cfg, d) == []; n += 1
        # negative case: an emptied registry MUST be detected — the whole point of this jig
        cfg2 = {"log": "log.jsonl", "hollow": [{"name": "pairings", "file": "jig.json", "path": "pairings", "min": 1}]}
        f = check(cfg2, d); assert f and f[0][0] == "hollow" and "0 entries" in f[0][2]; n += 1
        cfg3 = {"log": "log.jsonl", "hollow": [{"name": "gone", "file": "jig.json", "path": "nothing", "min": 1}]}
        f = check(cfg3, d); assert f and f[0][0] == "hollow" and "missing" in f[0][2]; n += 1
        f = check({"log": "log.jsonl", "hollow": [{"name": "x", "file": "nope.json", "path": "a"}]}, d); assert f[0][0] == "error"; n += 1
        open(reg, "w", encoding="utf-8").write(json.dumps({"contracts": "registry.json"}))
        f = check(cfg, d); assert f and f[0][0] == "error" and "reference" in f[0][2]; n += 1   # a string is never counted as entries
        json.dump({"contracts": [1, 2], "pairings": []}, open(reg, "w"))   # restore for the gate-log cases below
        open(os.path.join(d, "log.jsonl"), "w").write(json.dumps({"jig": "sekisho", "tier": "pr", "gates": {"a": "skip", "b": "skip"}}) + "\n")
        f = check(cfg, d); assert f and f[0][1] == "gate_log" and "zero gates" in f[0][2]; n += 1
        open(os.path.join(d, "log.jsonl"), "a").write(json.dumps({"jig": "sekisho", "tier": "pr", "gates": {"a": "pass", "b": "skip"}}) + "\n")
        assert check(cfg, d) == []; n += 1
    print(f"karappo selftest: {n} checks OK")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default="jig.json")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    try:
        cfg = load_json(a.config)
    except FileNotFoundError:
        sys.exit(f"config error: {a.config} not found (copy jig.example.json to jig.json)")
    except json.JSONDecodeError as e:
        sys.exit(f"config error: {a.config}: {e}")
    findings = check(cfg)
    if not findings:
        print(f"KARAPPO ok: {len(cfg.get('hollow', []))} registries populated; last gate run executed gates")
        return EXIT_OK
    for level, name, msg in findings:
        print(f"{level.upper()} {name}: {msg}")
    return EXIT_HOLLOW if any(l == "hollow" for l, _, _ in findings) else EXIT_CONFIG


if __name__ == "__main__":
    sys.exit(main())
