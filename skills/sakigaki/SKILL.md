---
name: sakigaki
description: Contract-first, failing-test-first order for any change to code that produces data another file consumes (exports, APIs, reports, dashboards, shared formats). Use when asked to add or change a field, output, schema, or interface, or when starting any track-B/C change. Enforces that the contract exists BEFORE the code and that the guard test is red BEFORE implementation.
---

# SAKIGAKI — "Write it first. Afterwards, you're just tracing."

A contract written after the code merely traces the code that exists. If the code is wrong, the contract copies the wrong thing faithfully and can never detect drift. So the order is the whole point.

## The four steps (track B; track C adds the pr/release tiers)

1. **Write the contract first.** In `jig.json` → `contracts[]`: `id`, `producer`, `consumers`, `fields`, `requirements` (which requirement this serves), `guard_test`. Before any code.
2. **Put the failing test first.** Write the guard test, then prove it is red:
   ```
   python3 <plugin>/skills/sakigaki/scripts/sakigaki.py --expect-red --cmd "python3 -m pytest tests/test_orders_export.py -q"
   ```
   If this says the test is already green, you implemented first. Stop and fix the order.
3. **Touch only the one section of the spec you are changing.** No full rewrites.
4. **Pass the checkpoint.** `sekisho --tier commit` must be green before you commit.

## Check that the order was kept

```
python3 <plugin>/skills/sakigaki/scripts/sakigaki.py --changed src/orders/export.py src/new.py
python3 <plugin>/skills/sakigaki/scripts/sakigaki.py --selftest
```

Fails when a changed source file is named by no contract, when a touched contract has no `requirements`, or when its `guard_test` does not exist on disk. Tests, docs, and `track_a_paths` are exempt; consumer-only changes pass.

## Never

- Never write the code and then "add the contract to match". That contract is decoration.
- Never register a `guard_test` that does not exist yet as if it did.

Exit codes: `0` pass · `1` violation · `2` config/usage error.
