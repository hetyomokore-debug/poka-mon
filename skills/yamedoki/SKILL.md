---
name: yamedoki
description: Write the stop conditions for a jig on the day you build it, and evaluate them later from the log. Use when adding any new gate or check ("--init"), when a gate was bypassed, gave a false positive, or let a defect escape ("--record"), and in periodic reviews ("--evaluate"). The only jig that asks to be retired — without it, jigs turn into a religion.
---

# YAMEDOKI — "You may not need me anymore."

Right after you introduce a mechanism, the numbers improve even if the mechanism is meaningless — people behave differently when watched. So the metric is not "right after rollout" but "still in use after three months", and the abolition conditions are written **before** the jig has a chance to defend itself.

## On the day you build a jig

```
python3 <plugin>/skills/yamedoki/scripts/yamedoki.py --init --jig sekisho --review-after-days 90
```

Writes into `jig.json`:

```json
"retirement": [{ "jig": "sekisho", "created": "2026-09-02", "review_after_days": 90,
                 "abolish_if": { "bypass_rate_gt": 0.20, "false_positive_rate_gt": 0.30, "track_c_share_gt": 0.50 } }]
```

| Condition | Reading |
|---|---|
| bypass rate > 20% | the gate is too heavy — a **design** failure, not a discipline failure |
| false-positive rate > 30% | trust is gone — loosen it; continued use beats strictness |
| track-C share > 50% | the tiering is not working — raise the thresholds |
| review date passed with no data | the jig was never run or never logged — it is decoration |

## When something happens

```
python3 <plugin>/skills/yamedoki/scripts/yamedoki.py --record bypass         --jig sekisho --note "--no-verify, hotfix"
python3 <plugin>/skills/yamedoki/scripts/yamedoki.py --record false-positive --jig sakigaki --note "flagged a vendored file"
python3 <plugin>/skills/yamedoki/scripts/yamedoki.py --record escape         --jig sekisho --note "prod broke after a green run"
```

Escapes are the one thing only a human can know. Record them the moment you learn of them; an unrecorded escape inflates every other number.

## Periodically

```
python3 <plugin>/skills/yamedoki/scripts/yamedoki.py --evaluate
```

Prints, per jig: runs, fails, bypasses, false positives, escapes, the three rates, and a verdict — `KEEP`, `REVIEW DUE`, `REVIEW OVERDUE (no data)`, or `ABOLISH CANDIDATE: <which condition>`. The verdict is advisory. Humans retire jigs; the jig only asks.

## Never

- Never build a gate without `--init`. A jig without stop conditions cannot be wrong, and a thing that cannot be wrong is a belief.
- Never retire a jig by deleting it from `jig.json`. Record the decision (`--record` a note, then remove the retirement entry in the same change with the reason in the docs).

Exit codes: `0` done · `2` config/usage error.
