#!/usr/bin/env python3
"""YAMEDOKI — the only jig that asks to be retired.  (POKA-MON, principle 7)

Write the stop conditions on the day you build a jig; evaluate them later from the log, not from feelings.
  --init --jig NAME         register retirement conditions for a jig (created today, review after N days)
  --record EVENT --jig NAME log a bypass / false-positive / escape against a jig
  --evaluate                compute bypass rate, false-positive rate, track-C share; print KEEP / ABOLISH CANDIDATE / REVIEW OVERDUE

Rates (all from the gate log):
  bypass_rate          = bypass events / (gate runs + bypass events)
  false_positive_rate  = false-positive events / gate FAILs of that jig
  track_c_share        = HAKARI verdicts of C / all HAKARI verdicts

Exit codes: 0 = done (advisory: humans decide)   2 = config/usage error
"""
import argparse, datetime, json, os, sys, tempfile

EXIT_OK, EXIT_CONFIG = 0, 2
EVENTS = ("bypass", "false-positive", "escape")


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


def read_log(cfg, root="."):
    p = os.path.join(root, cfg.get("log", ".jig/gate_log.jsonl"))
    if not os.path.exists(p):
        return []
    out = []
    for line in open(p, encoding="utf-8"):
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return out


def init_entry(cfg, jig, today, review_after_days=90, bypass=0.20, fp=0.30, trackc=0.50):
    entries = cfg.setdefault("retirement", [])
    if any(e.get("jig") == jig for e in entries):
        raise ValueError(f"retirement conditions for '{jig}' already exist")
    entries.append({"jig": jig, "created": today.isoformat(), "review_after_days": review_after_days,
                    "abolish_if": {"bypass_rate_gt": bypass, "false_positive_rate_gt": fp, "track_c_share_gt": trackc}})
    return entries[-1]


def evaluate(cfg, log, today):
    reports = []
    hak = [r for r in log if r.get("jig") == "hakari"]
    trackc = sum(1 for r in hak if r.get("machine_track") == "C")
    min_n = int(cfg.get("yamedoki_min_samples", 10))   # below this, a rate is reported but not judged
    for e in cfg.get("retirement", []):
        jig = e["jig"]
        # "sekisho" means the checkpoint itself: every gate run counts. Any other name is a gate inside it.
        runs = [r for r in log if r.get("jig") == "sekisho" and (jig == "sekisho" or jig in r.get("gates", {}))]
        fails = sum(1 for r in runs if (jig == "sekisho" and "fail" in r.get("gates", {}).values()) or r.get("gates", {}).get(jig) == "fail")
        ev = [r for r in log if r.get("jig") == "yamedoki" and r.get("target") == jig]
        bypass = sum(1 for r in ev if r.get("event") == "bypass")
        fps = sum(1 for r in ev if r.get("event") == "false-positive")
        escapes = sum(1 for r in ev if r.get("event") == "escape")
        denom = {"bypass_rate": len(runs) + bypass, "false_positive_rate": fails, "track_c_share": len(hak)}
        rates = {
            "bypass_rate": (bypass / denom["bypass_rate"]) if denom["bypass_rate"] else None,
            "false_positive_rate": (fps / fails) if fails else None,
            "track_c_share": (trackc / len(hak)) if hak else None,
        }
        cond = e.get("abolish_if", {})
        hits, thin = [], []
        for key, val in rates.items():
            limit = cond.get(key + "_gt")
            if limit is None or val is None:
                continue
            if denom[key] < min_n:
                thin.append(f"{key} n={denom[key]}<{min_n}")
                continue
            if val > limit:
                hits.append(f"{key} {val:.2f} > {limit:.2f}")
        created = datetime.date.fromisoformat(e["created"])
        due = created + datetime.timedelta(days=int(e.get("review_after_days", 90)))
        has_data = bool(runs or ev or hak)
        if hits:
            verdict = "ABOLISH CANDIDATE: " + "; ".join(hits)
        elif today >= due and not has_data:
            verdict = "REVIEW OVERDUE (no data: the jig was never run or never logged)"
        elif today >= due:
            verdict = "REVIEW DUE — conditions not met; decide keep / loosen / retire and re-init"
        else:
            verdict = "KEEP"
        if thin:
            verdict += "  [not judged, too few samples: " + ", ".join(thin) + "]"
        reports.append({"jig": jig, "created": e["created"], "due": due.isoformat(), "runs": len(runs), "fails": fails,
                        "bypass": bypass, "false_positives": fps, "escapes": escapes, "rates": rates, "verdict": verdict})
    return reports


def fmt(v):
    return "n/a" if v is None else f"{v:.2f}"


def selftest():
    n = 0
    with tempfile.TemporaryDirectory() as d:
        cfg = {"log": "log.jsonl"}
        t0 = datetime.date(2026, 9, 2)
        e = init_entry(cfg, "sekisho", t0); assert e["created"] == "2026-09-02"; n += 1
        try:
            init_entry(cfg, "sekisho", t0); assert False
        except ValueError:
            n += 1
        # no data, before due
        r = evaluate(cfg, [], t0 + datetime.timedelta(days=10)); assert r[0]["verdict"] == "KEEP"; n += 1
        # no data, after due
        r = evaluate(cfg, [], t0 + datetime.timedelta(days=91)); assert r[0]["verdict"].startswith("REVIEW OVERDUE"); n += 1
        log = [{"jig": "sekisho", "gates": {"sekisho": "pass"}}] * 6 + [{"jig": "sekisho", "gates": {"sekisho": "fail"}}] * 2 \
            + [{"jig": "yamedoki", "target": "sekisho", "event": "bypass"}] * 4 \
            + [{"jig": "hakari", "machine_track": "B"}] * 3 + [{"jig": "hakari", "machine_track": "C"}]
        r = evaluate(cfg, log, t0 + datetime.timedelta(days=30))[0]
        assert abs(r["rates"]["bypass_rate"] - 4 / 12) < 1e-9 and r["verdict"].startswith("ABOLISH CANDIDATE: bypass_rate"); n += 1
        assert r["rates"]["false_positive_rate"] == 0.0 and abs(r["rates"]["track_c_share"] - 0.25) < 1e-9; n += 1
        log2 = [{"jig": "sekisho", "gates": {"x": "fail"}}] * 10 + [{"jig": "yamedoki", "target": "sekisho", "event": "false-positive"}] * 10
        r = evaluate(cfg, log2, t0)[0]; assert r["rates"]["false_positive_rate"] == 1.0 and "false_positive_rate 1.00 > 0.30" in r["verdict"]; n += 1
        # too few samples: rate is shown but NOT judged (no day-one abolish verdicts)
        r = evaluate(cfg, [{"jig": "hakari", "machine_track": "C"}], t0)[0]
        assert r["rates"]["track_c_share"] == 1.0 and r["verdict"].startswith("KEEP") and "too few samples" in r["verdict"]; n += 1
        append_log(cfg, {"jig": "yamedoki", "event": "escape", "target": "sekisho", "note": "prod broke"}, root=d)
        assert read_log(cfg, d)[-1]["event"] == "escape"; n += 1
        # --dry-run: --init and --record write nothing
        cwd = os.getcwd(); os.chdir(d)
        try:
            json.dump({"log": "dry.jsonl"}, open("dry.json", "w")); before = open("dry.json").read()
            assert main(["--config", "dry.json", "--init", "--jig", "gate-x", "--dry-run"]) == 0 and open("dry.json").read() == before; n += 1
            assert main(["--config", "dry.json", "--record", "bypass", "--jig", "gate-x", "--dry-run"]) == 0 and not os.path.exists("dry.jsonl"); n += 1
        finally:
            os.chdir(cwd)
    print(f"yamedoki selftest: {n} checks OK")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default="jig.json")
    ap.add_argument("--init", action="store_true", help="register retirement conditions for --jig (writes jig.json)")
    ap.add_argument("--record", choices=EVENTS, help="log an event against --jig")
    ap.add_argument("--evaluate", action="store_true")
    ap.add_argument("--jig")
    ap.add_argument("--note", default="")
    ap.add_argument("--review-after-days", type=int, default=90)
    ap.add_argument("--today", help="YYYY-MM-DD (default: today; used for deterministic evaluation)")
    ap.add_argument("--dry-run", action="store_true", help="show what --init / --record would write; write nothing; exit 0")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    today = datetime.date.fromisoformat(a.today) if a.today else datetime.date.today()
    cfg = load_config(a.config)
    if a.init:
        if not a.jig:
            ap.error("--init requires --jig")
        try:
            e = init_entry(cfg, a.jig, today, a.review_after_days)
        except ValueError as err:
            sys.exit(f"config error: {err}")
        if a.dry_run:
            print(f"DRY-RUN would register {a.jig} in {a.config}: review after {e['review_after_days']} days; abolish if {json.dumps(e['abolish_if'])}")
            return EXIT_OK
        with open(a.config, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2); f.write("\n")
        print(f"YAMEDOKI registered {a.jig}: review after {e['review_after_days']} days; abolish if {json.dumps(e['abolish_if'])}")
        return EXIT_OK
    if a.record:
        if not a.jig:
            ap.error("--record requires --jig")
        if a.dry_run:
            print(f"DRY-RUN would record {a.record} against {a.jig} in {cfg.get('log', '.jig/gate_log.jsonl')}")
            return EXIT_OK
        append_log(cfg, {"jig": "yamedoki", "event": a.record, "target": a.jig, "note": a.note})
        print(f"YAMEDOKI recorded {a.record} against {a.jig}")
        return EXIT_OK
    if a.evaluate:
        reports = evaluate(cfg, read_log(cfg), today)
        if not reports:
            print("YAMEDOKI: no retirement conditions registered — a jig without stop conditions is a religion (run --init --jig NAME)")
            return EXIT_OK
        for r in reports:
            print(f"YAMEDOKI {r['jig']}: created {r['created']}, review due {r['due']}")
            rt = r["rates"]
            print(f"  runs={r['runs']} fails={r['fails']} bypass={r['bypass']} false_positives={r['false_positives']} escapes={r['escapes']}")
            print(f"  bypass_rate {fmt(rt['bypass_rate'])}  false_positive_rate {fmt(rt['false_positive_rate'])}  track_c_share {fmt(rt['track_c_share'])}")
            print(f"  verdict: {r['verdict']}")
        return EXIT_OK
    ap.error("one of --init / --record / --evaluate is required (or --selftest)")


if __name__ == "__main__":
    sys.exit(main())
