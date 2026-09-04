---
name: sekisho
description: The checkpoint. Runs the gates registered for a tier (commit / pr / release) and reports PASS/FAIL/SKIP per gate with a one-line summary; the ONLY acceptable evidence that a change is done. Use before reporting any task complete, before committing, before opening a PR, before a release; also use --dry-run to see what a tier would run. Never accept "I checked it" in its place.
---

# SEKISHO — "'I checked it' is not a pass."

A gatekeeper that opens for exactly one thing: exit code 0 from every gate in the tier. It does not read prose.

## Run

```
python3 <plugin>/skills/sekisho/scripts/sekisho.py --tier commit --changed <files>   # ~seconds; before every commit
python3 <plugin>/skills/sekisho/scripts/sekisho.py --tier pr      --changed <files>   # when the change is complete
python3 <plugin>/skills/sekisho/scripts/sekisho.py --tier release                     # before anything ships
python3 <plugin>/skills/sekisho/scripts/sekisho.py --tier pr --dry-run                # plan only, runs nothing
python3 <plugin>/skills/sekisho/scripts/sekisho.py --selftest
```

Output, always in this shape — one line per gate, one summary line:

```
== SEKISHO tier=commit ==
PASS hakari (0.1s)
FAIL sakigaki (0.2s): exit 1 — src/new.py: no contract names this file as a producer
SKIP unit — not installed (requires tests)
excluded as not installed: 1 (unit) — a green run does not cover these
=== 1 PASS / 1 FAIL / 1 SKIP (tier=commit) ===
```

Paste the summary line in your report. Quote the FAIL line verbatim; never paraphrase it into "some checks failed".

## Rules the gatekeeper lives by

- **A skipped gate is listed, every time.** Gates whose script is not installed are excluded from the plan and *named* in the output. A green run that skipped something is not a full pass, and the output says so.
- **Keep the commit tier under ~15 seconds.** Past that, people route around it (YAMEDOKI will show you the bypass rate). Move heavy gates to `pr` or `release`.
- **A permanently red gate dies.** If a gate cannot pass by design, fix the gate or retire it via YAMEDOKI — do not leave it red, and do not remove it silently.
- **Every run is logged** to `log` in `jig.json` as one JSON line: tier, per-gate result, failures, unavailable gates.

## Configuring gates (`jig.json`)

```json
"gates": {
  "commit": [ { "name": "hakari", "cmd": "python3 {plugin}/skills/hakari/scripts/hakari.py --changed {changed}" } ],
  "pr":     [ { "name": "unit",   "cmd": "python3 -m pytest -q", "requires": "tests" } ]
}
```

`{plugin}` expands to the plugin root, `{changed}` to the quoted changed files, `{config}` to the config path in use. `requires` names a path that must exist for the gate to be considered installed.

Exit codes: `0` all executed gates passed · `1` a gate failed · `2` config/usage error.
