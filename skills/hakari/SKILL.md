---
name: hakari
description: Risk track (A/B/C) for a change, computed by machine from blast radius, reversibility, and criticality — never from how the change is described. Use BEFORE editing when asked to "fix", "add", "refactor", "migrate", "deploy", or whenever someone (including you) says a change is "minor", "quick", or "safe". Also use when deciding which tier of gates a change must pass.
---

# HAKARI — "I didn't ask for your self-report."

A scale that weighs the danger of a change without listening to anyone's opinion of it. Three axes, all read from `jig.json`:

| Axis | Source | Pushes toward |
|---|---|---|
| **Blast radius** | consumers of every contract whose `producer` you touch | C when large |
| **Reversibility** | files matching `irreversible` patterns (migrations, deploy, send/notify/delete) | C |
| **Criticality** | touched contracts flagged `business_critical` | C |

Track A only if **every** changed file is under `track_a_paths` and no contract is touched. Everything else is B, unless an axis says C.

`contracts` may be inline in `jig.json` or an existing registry file named there (see the README); both shapes are read the same way.

## Run

```
python3 <plugin>/skills/hakari/scripts/hakari.py --changed src/orders/export.py deploy/run.sh
python3 <plugin>/skills/hakari/scripts/hakari.py --changed ... --json        # machine-readable
python3 <plugin>/skills/hakari/scripts/hakari.py --changed ... --dry-run     # do not log
python3 <plugin>/skills/hakari/scripts/hakari.py --selftest
```

Output: `HAKARI track=C (machine=C) blast=2 irreversible=['deploy/run.sh'] critical=['orders_export'] contracts=['orders_export']`

Every verdict is appended to the gate log (`log` in `jig.json`). YAMEDOKI reads it later to compute the track-C share.

## Overriding

```
... --override B --reason "hotfix reviewed live with the on-call engineer"
```

Allowed. Required: `--reason`. Both the machine track and the override are logged, so later you can count how many overridden changes actually blew up. **A jig doesn't forbid the act. It makes sure the act leaves a trace.**

## Never

- Never ask the model or the author "is this change minor?" and act on the answer. Run the script.
- Never edit `track_a_paths` to make a change fall into A. That is a delete-to-green.

Exit codes: `0` judged · `2` config/usage error.
