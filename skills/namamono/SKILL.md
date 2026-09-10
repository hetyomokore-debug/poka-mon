---
name: namamono
description: Any table, list, count, or index that a human would maintain by hand (test-case tables, coverage tables, "N checks" in prose, feature lists) — replace it with a generator and gate on the diff. Use when asked to "update the table", "keep the docs in sync", "add a row", or when you notice a hand-maintained list; also runs as a pr-tier gate.
---

# NAMAMONO — "I'm a perishable. Still not updated today."

Hand-written tables rot. Not because anyone lies — because they were correct when written and nobody updated them. One reconciliation in the original environment found 17 discrepancies between hand-written documents and the running code.

The fix is not "remember to update". The fix is: **don't write the table. Generate it. Stop when it differs.**

## Register a generated file

```json
"generated": [
  { "target": "docs/testcases.md", "cmd": "python3 tools/gen_testcases.py --out {out}" }
]
```

`{out}` is a temp path the generator must write to. NAMAMONO compares it byte-for-byte with `target`.

## Run

```
python3 <plugin>/skills/namamono/scripts/namamono.py            # STALE / FRESH per target; exit 1 if anything is stale
python3 <plugin>/skills/namamono/scripts/namamono.py --refresh  # overwrite stale targets; the previous bytes go to .jig/backup/<ts>/ first (one move to undo)
python3 <plugin>/skills/namamono/scripts/namamono.py --refresh --dry-run  # say what would be overwritten and where the backup would go; write nothing
python3 <plugin>/skills/namamono/scripts/namamono.py --selftest
```

Put it in the `pr` tier so a stale table blocks the PR, not the commit.

## When asked to "update the table by hand"

Don't. Find or write the generator, register it, run `--refresh`, commit both. If a generator is genuinely impossible right now, say so and record it as an open item — do not hand-edit and move on.

Exit codes: `0` fresh · `1` stale · `2` config error or generator failed.
