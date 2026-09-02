# Changelog

## 0.1.1 — 2026-09-02

Scripts and rules now exist (they were documented in 0.1.0 but not committed).

- `skills/_lib/jiglib.py` shared helpers (Python 3.8+, no third-party deps)
- Working scripts with `--selftest` and `--dry-run`: hakari, sekisho, sakigaki, namamono, karappo, pokayoke, yamedoki
- `/jig-mode` router skill
- Three always-on rules under `rules/`
- `jig-auditor` subagent
- `jig.example.json` plus generated `.jig/contract_ids.txt`
- JSONL gate log, exit codes 0/1/2 (+3 HOLLOW)

Known limits (deliberately unhidden):

- Contract matching is glob-based; indirect references through variables or dynamic keys are not seen
- Bypasses that skip the gate entirely (`git commit --no-verify`) are not observed; record them with `yamedoki --record bypass`
- Manifest component-path fields (`skills`, `rules`, `agents`) follow the documented names but have not been validated against a live Marketplace submission
- Unregistered work still passes straight through unless `--changed` is passed to sakigaki

## 0.1.0 — 2026-09-02

Skeleton release (private, under review). README and license only.
