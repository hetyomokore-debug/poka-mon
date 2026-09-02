---
name: hakari
description: Weigh change danger into track A/B/C from blast radius, reversibility, and criticality. Never ask the worker if the change is minor. Use when starting work, jig-mode, or classifying risk.
---

# HAKARI

Do not let the person doing the work say "this one's easy."

```bash
python3 skills/hakari/scripts/hakari.py weigh --changed <files>
python3 skills/hakari/scripts/hakari.py weigh --changed <files> --override-track B --reason "..."
python3 skills/hakari/scripts/hakari.py --selftest
```

Tracks: A throwaway, B normal (sakigaki then sekisho), C new or irreversible (full procedure). Override is recorded, never silent. Advisory exit 0 means judged, not safe.
