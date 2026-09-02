# Changelog

## 0.1.0 — 2026-09-02

Skeleton release (private, under review).

- Seven skills with procedures and minimal working scripts: hakari, sekisho, sakigaki, namamono, karappo, pokayoke, yamedoki
- `/jig-mode` router skill
- Three always-on rules: no manual checklists, never green by deletion, self-report is not a pass
- `jig-auditor` subagent
- `jig.example.json` configuration template
- Every script: `--selftest`, `--dry-run` where meaningful, JSONL gate log, exit codes 0/1/2 (+3 HOLLOW for karappo)

Known limits (deliberately unhidden):

- Contract matching is glob-based; indirect references through variables or dynamic keys are not seen
- Bypasses that skip the gate entirely (`git commit --no-verify`) are not observed; record them with `yamedoki --record bypass`
- Manifest component-path fields (`skills`, `rules`, `agents`) follow the documented names but have not been validated against a live Marketplace submission
