---
name: karappo
description: Alarm when a check has nothing left to check. Empty input or item count below the floor exits 3 (HOLLOW), not 0. Use when gates might have been deleted to go green.
---

# KARAPPO

It's empty inside.

```bash
python3 skills/karappo/scripts/karappo.py
python3 skills/karappo/scripts/karappo.py --selftest
```

A check that passes silently when its input is empty is decoration. Exit 3 is not a pass.
