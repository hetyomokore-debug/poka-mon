---
name: jig-mode
description: Entry point for Jig-Driven Development. Weigh first with hakari, route to the jigs that apply, end with a sekisho line instead of verified. Use when the user says jig-mode, ジグ駆動, or starts non-trivial shipping work under POKA-MON.
---

# jig-mode

1. Name the change in one line.
2. Run `hakari.py weigh --changed ...`. Do not ask "is this minor?"
3. Route:
   - A — do the work, still log the track.
   - B — sakigaki check, then the work, then sekisho `--tier commit`.
   - C — sakigaki, pokayoke, the work, sekisho `--tier pr` (or release if shipping).
4. After accidents that look like silent failure, run karappo. After hand-written counts, run namamono.
5. Record bypasses with `yamedoki.py --record bypass`. Evaluate stop conditions when a gate feels heavy.
6. End with SEKISHO's summary line. Never "verified."

Scripts live next to their SKILL.md under `skills/<jig>/scripts/`. Config is the project's `jig.json` (copy `jig.example.json`).
