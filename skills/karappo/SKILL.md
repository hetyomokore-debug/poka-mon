---
name: karappo
description: The jig that watches the jigs. Detects hollowed-out checks — a registry emptied so a gate passes, a check whose input vanished, a gate run where everything was skipped. Use when asked "are the gates still working?", after deleting or moving anything the gates read, in the pr tier, and in any periodic audit. Exit 3 (HOLLOW) is distinct from a normal failure on purpose.
---

# KARAPPO — "It's empty inside."

The most dangerous failure is the one that keeps reporting success. A check that lost its input and kept returning "pass" for four days is the founding incident of this jig.

> A check that passes silently when its input is empty is not a checkpoint. It's decoration.

## What it watches

```json
"hollow": [
  { "name": "contracts", "file": "jig.json", "path": "contracts", "min": 1 },
  { "name": "pairings",  "file": "jig.json", "path": "pairings",  "min": 1 }
]
```

- A registry with fewer than `min` entries → **HOLLOW**
- A registry `path` that no longer exists → **HOLLOW**
- The last SEKISHO run executed zero gates (all skipped) → **HOLLOW**

## Run

```
python3 <plugin>/skills/karappo/scripts/karappo.py
python3 <plugin>/skills/karappo/scripts/karappo.py --selftest
```

`--selftest` includes the negative case: an emptied registry **must** be detected. Every check of this kind ships with deliberately broken input in its own selftest — you check that the check is working.

## Lowering `min` is allowed, silently is not

If a registry genuinely needs fewer entries, write the reason in the project's documentation and lower `min` in the same change. Lowering it to make the alarm stop, without the reason, is the delete-to-green this jig exists to catch.

Exit codes: `0` ok · `2` config error · `3` HOLLOW.
