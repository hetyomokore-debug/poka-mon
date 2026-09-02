---
name: sekisho
description: Run a tier of mechanical gates. Only exit 0 is a pass. Skipped gates are listed and are not a pass. Use instead of I checked it or verified.
---

# SEKISHO

A pass is a signal a machine emits.

```bash
python3 skills/sekisho/scripts/sekisho.py --tier commit --dry-run
python3 skills/sekisho/scripts/sekisho.py --tier commit --changed <files>
python3 skills/sekisho/scripts/sekisho.py --selftest
```

End every task with the summary line the script prints. Never end with "verified."
