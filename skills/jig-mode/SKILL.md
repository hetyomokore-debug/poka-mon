---
name: jig-mode
description: Entry point for Jig-Driven Development. Use at the start of ANY change to code, config, or docs — "build X", "fix Y", "refactor Z", "update the table", "add a rule". Runs HAKARI first (risk track, no self-report), routes the work to the right jig (SAKIGAKI for contracts, NAMAMONO for generated tables, POKAYOKE for rules/policies, KARAPPO for checks-of-checks, YAMEDOKI for retiring a jig), and ends every task with SEKISHO's exit-code summary instead of "verified".
---

# /jig-mode — seven monsters that don't work. That's the job.

You are about to change something. Do this in order. Do not skip step 1 because the change "looks small" — that is exactly the self-report HAKARI refuses.

## 1. Ask HAKARI before touching anything

```
python3 <plugin>/skills/hakari/scripts/hakari.py --changed <files you intend to touch>
```

It prints a track. Follow it:

| Track | Meaning | What you do |
|---|---|---|
| **A** | throwaway / exploration, touches no contract | no ceremony; at the end, say "discard" or "promote to B" |
| **B** | normal change (default) | the four steps of SAKIGAKI, then SEKISHO `--tier commit` |
| **C** | new, irreversible, or many contracts | B, plus SEKISHO `--tier pr` before you call it done, and `--tier release` before anything ships |

If you disagree with the track, you may record that with `--override <track> --reason "..."`. The track does not change — the disagreement is logged next to it, and the tier you must pass is still the machine's.

## 2. Route the work

| The task is about... | Use |
|---|---|
| producing or consuming data another file depends on | **sakigaki** — contract first, failing test first, then code |
| a table, list, or count that a human would otherwise maintain by hand | **namamono** — generate it, gate on the diff |
| a rule, policy, or "we don't do X" | **pokayoke** — declaration AND enforcement, paired |
| whether the checks themselves still check anything | **karappo** |
| a gate that is too heavy, too noisy, or no longer needed | **yamedoki** — retire it through the log, never by deletion |

## 3. Finish with SEKISHO, not with a sentence

```
python3 <plugin>/skills/sekisho/scripts/sekisho.py --tier commit --changed <files>
```

Paste its last line (`=== N PASS / M FAIL / K SKIP ===`) in your report. If any gate was **SKIP**ped, say so — a green run does not cover what it did not run. If no gate covers the change, write "no gate covers this" — never "verified".

## Never

- Never write "I checked it", "verified", or "should work" as evidence. Exit codes are evidence.
- Never create a manual checklist. Turn the check into a command or record it as an open item.
- Never delete a test, a contract, a pairing, or an expected value to make a gate green.
- Never lower a track by describing the change as minor.

## The seven, one move each

```
HAKARI   used WEIGH.        Your self-report had no effect.
SEKISHO  used BLOCK.        "I checked it" is not very effective.
SAKIGAKI used WRITE FIRST.
NAMAMONO used ROT.          Nobody noticed.
KARAPPO  used ALARM.        The box was empty.
POKAYOKE used DOESN'T FIT.  It's super effective.
YAMEDOKI asked to be released.
```

On a day when all seven have done their job, the log reads: **nothing happened.** That's the point.
