---
name: yamedoki
description: Evaluate jig stop conditions from the gate log. Record bypasses. Use after a gate run, when a jig feels too heavy, or when asked whether to keep a check.
---

# YAMEDOKI

You may not need me anymore. Write that sentence on day one.

```bash
python3 skills/yamedoki/scripts/yamedoki.py --init
python3 skills/yamedoki/scripts/yamedoki.py --record bypass
python3 skills/yamedoki/scripts/yamedoki.py evaluate
python3 skills/yamedoki/scripts/yamedoki.py --selftest
```

Default abolish_if: bypass >20%, false positive >30%, track C share >50%, accident class not down after 90 days. Under min samples, report rates but do not judge.
