---
name: sakigaki
description: Contract-first, failing-test-first order for any change to code that produces data another file consumes (exports, APIs, reports, dashboards, shared formats). Use when asked to add or change a field, output, schema, or interface, or when starting any track-B/C change. Enforces that the contract exists BEFORE the code and that the guard test is red BEFORE implementation.
---

# SAKIGAKI — "Write it first. Afterwards, you're just tracing."

A contract written after the code merely traces the code that exists. If the code is wrong, the contract copies the wrong thing faithfully and can never detect drift. So the order is the whole point.

## The four steps (track B; track C adds the pr/release tiers)

1. **Write the contract first.** In `jig.json` → `contracts[]`: `id`, `producer`, `consumers`, `fields`, `requirements` (which requirement this serves), `guard_test`. Before any code. If the repository already keeps a contracts registry, name that file in `contracts` instead of copying it (see the README); its entries are accepted as-is.
2. **Put the failing test first.** Write the guard test, then prove it is red:
   ```
   python3 <plugin>/skills/sakigaki/scripts/sakigaki.py --expect-red --cmd "python3 -m pytest tests/test_orders_export.py -q"
   ```
   If this says the test is already green, you implemented first. Stop and fix the order.
3. **Touch only the one section of the spec you are changing.** No full rewrites.
4. **Pass the checkpoint.** `sekisho --tier commit` must be green before you commit.

## Check that the order was kept

```
python3 <plugin>/skills/sakigaki/scripts/sakigaki.py --changed src/orders/export.py --planned src/orders/refunds.py
python3 <plugin>/skills/sakigaki/scripts/sakigaki.py --selftest
```

Fails when a changed or planned source file is named by no contract, when a touched contract has no `requirements`, or when its `guard_test` (a path, or the first token of a command) does not exist on disk. Tests, docs, and `track_a_paths` are exempt; consumer-only changes pass.

Every path given to `--changed` must exist on disk. One that does not — several paths joined into one argument, git's quoted form of a non-ASCII path, a deleted file — stops SAKIGAKI with exit 2 before anything is checked, because a path that names nothing matches no contract and would pass.

A file you are about to create goes in `--planned`, not `--changed`: its contract is checked before the file exists, which is when the check is worth something. A `--planned` path must not exist yet (an existing file goes in `--changed`) and must be a plain path — whitespace, a double quote, a backslash or a control character stops SAKIGAKI with exit 2, because nothing on disk can tell such a path from several joined into one argument or from git's quoted form. A file whose name needs those characters: create it first, then pass it in `--changed`.

## Never

- Never write the code and then "add the contract to match". That contract is decoration.
- Never register a `guard_test` that does not exist yet as if it did.

Exit codes: `0` pass · `1` violation · `2` config/usage error, including a `--changed` path that does not exist and a `--planned` path that does (or is not a plain path).
