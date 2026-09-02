---
name: sakigaki
description: Enforce write-first order. Contract and failing guard exist before implementation. Use on track B/C before writing code.
---

# SAKIGAKI

Write the contract first. Afterwards you are just tracing.

```bash
python3 skills/sakigaki/scripts/sakigaki.py check --changed <files>
python3 skills/sakigaki/scripts/sakigaki.py --selftest
```

Fail if a changed file matches no producer (and is not track A). Fail if requirements or guard_test are missing.
