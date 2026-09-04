#!/usr/bin/env python3
"""HAKARI — risk track without self-report.  (POKA-MON / Jig-Driven Development, principle 1)

Computes a risk track (A / B / C) for a set of files you intend to change, from three machine axes:
  blast radius     — how many consumers depend on the producers you touch (from jig.json contracts)
  reversibility    — whether any file matches an irreversible pattern (migrations, deploy, send/notify/delete)
  criticality      — whether any touched contract is business_critical
Nobody can lower the track by describing the change as minor. --override is allowed but RECORDED, never silent.

Exit codes: 0 = judged (see output)   2 = config/usage error
"""
import argparse, datetime, fnmatch, json, os, sys, tempfile

EXIT_OK, EXIT_CONFIG = 0, 2


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


def append_log(cfg, record, root="."):
    p = os.path.join(root, cfg.get("log", ".jig/gate_log.jsonl"))
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
    record = {"ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), **record}
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def assess(cfg, changed, override=None, reason=None):
    contracts = cfg.get("contracts", [])
    touched = [c for c in contracts if any(matches(f, c.get("producer", "")) for f in changed)]
    blast = sum(len(c.get("consumers", [])) for c in touched)
    irreversible = sorted({f for f in changed if any(matches(f, p) for p in cfg.get("irreversible", []))})
    critical = [c["id"] for c in touched if c.get("business_critical")]
    a_paths = cfg.get("track_a_paths", [])
    all_a = bool(changed) and all(any(matches(f, p) for p in a_paths) for f in changed)
    if all_a and not touched and not irreversible:
        machine = "A"
    elif irreversible or critical or len(touched) >= int(cfg.get("track_c_contracts", 4)) \
            or blast >= int(cfg.get("track_c_blast_radius", 8)):
        machine = "C"
    else:
        machine = "B"
    return {
        "jig": "hakari", "track": override or machine, "machine_track": machine,
        "blast_radius": blast, "irreversible": irreversible, "business_critical": critical,
        "touched_contracts": [c["id"] for c in touched], "changed": list(changed),
        "override": ({"track": override, "reason": reason} if override else None),
    }


def render(r):
    ov = f", OVERRIDDEN: {r['override']['reason']}" if r["override"] else ""
    return (f"HAKARI track={r['track']} (machine={r['machine_track']}{ov}) blast={r['blast_radius']} "
            f"irreversible={r['irreversible']} critical={r['business_critical']} contracts={r['touched_contracts']}")


def selftest():
    n = 0
    with tempfile.TemporaryDirectory() as d:
        cfg = {"log": "log.jsonl", "track_a_paths": ["scratch/**"], "irreversible": ["deploy/**", "**/*send*"],
               "contracts": [{"id": "c1", "producer": "src/a.py", "consumers": ["x", "y"]},
                             {"id": "crit", "producer": "src/pay.py", "consumers": [], "business_critical": True}]}
        assert assess(cfg, ["scratch/x.py"])["track"] == "A"; n += 1
        r = assess(cfg, ["src/a.py"]); assert r["track"] == "B" and r["blast_radius"] == 2 and r["touched_contracts"] == ["c1"]; n += 1
        assert assess(cfg, ["deploy/run.sh"])["track"] == "C"; n += 1
        assert assess(cfg, ["src/mail_send.py"])["track"] == "C"; n += 1
        assert assess(cfg, ["src/pay.py"])["track"] == "C"; n += 1
        assert assess(cfg, ["scratch/x.py", "src/a.py"])["track"] == "B"; n += 1   # mixed: not all in A paths
        r = assess(cfg, ["src/pay.py"], override="B", reason="hotfix, reviewed live")
        assert r["track"] == "B" and r["machine_track"] == "C" and r["override"]["reason"]; n += 1
        append_log(cfg, r, root=d)
        line = json.loads(open(os.path.join(d, "log.jsonl"), encoding="utf-8").read().splitlines()[-1])
        assert line["machine_track"] == "C" and line["override"]["track"] == "B"; n += 1   # override is recorded, not hidden
        assert matches("a/b/c.py", "a/**") and not matches("ab/c.py", "a/**"); n += 1
        assert matches("deep/dir/notify_me.py", "**/*notify*") and not matches("deep/dir/note.py", "**/*notify*"); n += 1
    print(f"hakari selftest: {n} checks OK")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--changed", nargs="+", help="files you intend to change (or have changed)")
    ap.add_argument("--config", default="jig.json")
    ap.add_argument("--override", choices=["A", "B", "C"], help="force a track; REQUIRES --reason; recorded in the log")
    ap.add_argument("--reason", help="why you are overriding (logged verbatim)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--dry-run", action="store_true", help="judge but do not append to the gate log")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.changed:
        ap.error("--changed is required (or use --selftest)")
    if a.override and not a.reason:
        ap.error("--override requires --reason: overriding is not forbidden, but it is recorded")
    cfg = load_config(a.config)
    r = assess(cfg, a.changed, a.override, a.reason)
    if not a.dry_run:
        append_log(cfg, r)
    print(json.dumps(r, ensure_ascii=False) if a.json else render(r))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
