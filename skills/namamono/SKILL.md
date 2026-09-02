---
name: namamono
description: Generate tables from source and fail when the saved copy differs. Use when a ledger, inventory, or count would otherwise be typed by hand.
---

# NAMAMONO

Do not write the table. Generate it. Diff is a fail.

```bash
python3 skills/namamono/scripts/namamono.py --dry-run
python3 skills/namamono/scripts/namamono.py
python3 skills/namamono/scripts/namamono.py --selftest
```

Each `generated[]` item must write to `{out}`. Target missing counts as stale.
