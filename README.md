# POKA-MON

**Seven monsters that don't work. That's the job.**

A Cursor / Claude Code plugin for **Jig-Driven Development**: quality lives in machine checkpoints (*jigs*) the worker cannot bypass — not in anyone's attention, and not in the sentence "I checked it."

Seven skills, one principle each, one script each. Every script has `--selftest` and returns machine-readable exit codes; every script that writes anything (hakari, sekisho, namamono `--refresh`, yamedoki `--init` / `--record`) also has `--dry-run`; the ones that judge or run gates append one JSON line to a gate log. No dependencies beyond Python 3.8+.

| Jig | Principle | One move | Script |
|---|---|---|---|
| **HAKARI** | No self-grading | `WEIGH` — risk track A/B/C from blast radius, reversibility, criticality. Overrides are recorded, never silent | `skills/hakari/scripts/hakari.py` |
| **SEKISHO** | "I checked it" is not a pass | `BLOCK` — runs a tier of gates; only exit 0 passes; skipped gates are always listed | `skills/sekisho/scripts/sekisho.py` |
| **SAKIGAKI** | The order is the jig | `WRITE FIRST` — contract before code, failing test before implementation | `skills/sakigaki/scripts/sakigaki.py` |
| **NAMAMONO** | Hand-written tables rot | `ROT` — generate the table, stop on diff | `skills/namamono/scripts/namamono.py` |
| **KARAPPO** | The enemy is breaking quietly | `ALARM` — a check with nothing left to check exits 3, not 0 | `skills/karappo/scripts/karappo.py` |
| **POKAYOKE** | A sign is not a lock | `DOESN'T FIT` — every rule needs a declaration and an enforcement, paired | `skills/pokayoke/scripts/pokayoke.py` |
| **YAMEDOKI** | Write the stop conditions first | `asked to be released` — retirement conditions on day one, evaluated from the log | `skills/yamedoki/scripts/yamedoki.py` |

Plus `/jig-mode`, the entry point that runs HAKARI first, routes to the right jig, and ends every task with SEKISHO's summary line instead of "verified".

On a day when all seven have done their job, the log reads: **nothing happened.** That's the point.

## Quick start

```bash
# 1. in your project root
cp <plugin>/jig.example.json jig.json      # edit contracts / gates / pairings for your repo

# 2. see what the commit tier would run (executes nothing)
python3 <plugin>/skills/sekisho/scripts/sekisho.py --tier commit --dry-run

# 3. run it for real
python3 <plugin>/skills/sekisho/scripts/sekisho.py --tier commit --changed src/thing.py

# 4. prove the jigs themselves work
for s in hakari sekisho sakigaki namamono karappo pokayoke yamedoki; do
  python3 <plugin>/skills/$s/scripts/$s.py --selftest
done
```

`<plugin>` is wherever the plugin is installed. Inside a Cursor or Claude Code session, the skills reference the scripts relative to their own `SKILL.md`, so the agent resolves the path.

## Install

- **Cursor** — from the Marketplace once published; until then, add this repository as a plugin source per Cursor's plugin docs. The manifest is `.cursor-plugin/plugin.json`.
- **Claude Code** — add this repository as a plugin marketplace and install: `/plugin marketplace add hetyomokore-debug/poka-mon`, then `/plugin install poka-mon@poka-mon` (manifests in `.claude-plugin/`). Or copy / symlink `skills/*` into `.claude/skills/` (project) or `~/.claude/skills/` (personal). Claude Code does not read `rules/*.mdc`; the same three rules are carried by the `jig-mode` skill's *Never* list.
- **Anything else that reads Agent Skills** — same `SKILL.md` files.

## Configuration (`jig.json`)

| Key | Read by | Meaning |
|---|---|---|
| `log` | all | path of the JSONL gate log (default `.jig/gate_log.jsonl`) |
| `contracts[]` | hakari, sakigaki | inline entries (`id`, `producer`, `consumers[]`, `fields[]`, `requirements[]`, `guard_test`, `business_critical`) and/or strings naming registry files — see below |
| `irreversible[]` | hakari | glob patterns whose files force track C |
| `track_a_paths[]` | hakari, sakigaki | paths where changes are throwaway (track A) |
| `track_c_contracts`, `track_c_blast_radius` | hakari | thresholds for track C (default 4 contracts / 8 consumers) |
| `gates.{commit,pr,release}[]` | sekisho | `name`, `cmd` (`{plugin}`, `{changed}` expand), optional `requires` |
| `generated[]` | namamono | `target`, `cmd` (must write to `{out}`) |
| `pairings[]` | pokayoke | `declaration{file,contains}`, `enforcement{file,contains}` |
| `hollow[]` | karappo | `file`, `path` (dotted), `min` |
| `retirement[]` | yamedoki | written by `--init`; `abolish_if` thresholds |
| `yamedoki_min_samples` | yamedoki | a rate with fewer samples than this is reported but not judged (default 10) |

Glob patterns support `dir/**` (subtree), `**/pattern` (any depth, matched against the path tail), and plain fnmatch.

### Using a contracts registry you already have

`contracts` may name a JSON file instead of (or alongside) inline entries. The file's top-level `contracts` list is read at run time, so the registry stays the single source of truth and is never copied into `jig.json` by hand:

```json
"contracts": ["tools/contracts/registry.json", { "id": "inline-one", "producer": "src/x.py", "consumers": [] }]
```

Entries in either place may use either shape:

| jig.example.json shape | registry shape (also accepted) |
|---|---|
| `"id": "orders_export"` | `"name": "orders_export"` |
| `"producer": "src/orders/export.py"` | `"producer": { "file": "src/orders/export.py", "fields": [...] }` |
| `"consumers": ["src/ui.js"]` | `"consumers": [{ "file": "src/ui.js", "reads": [...] }]` |
| `"guard_test": "tests/test_x.py"` | `"guard_test": "tools/check.py --selftest"` — the first token must exist on disk |
| `"business_critical": true` | absent → `false` |

Keys the jigs do not read (`hint`, `reads`, `notes`, …) are kept and ignored. Paths inside a registry are relative to the directory the jigs run from, which is the directory holding `jig.json`. For KARAPPO, point `hollow[]` at the registry file itself, not at `jig.json`'s `contracts`: a reference string is reported as an error, never counted as entries.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | pass (or, for HAKARI / YAMEDOKI, "judged" — they are advisory) |
| `1` | a gate or check failed |
| `2` | config or usage error — never treated as a pass |
| `3` | HOLLOW (KARAPPO only): a check has nothing left to check |

## The rules (always on)

- `rules/no-manual-checklists.mdc` — every check is a command that blocks
- `rules/never-green-by-deletion.mdc` — never pass a gate by deleting what it checks
- `rules/self-report-is-not-a-pass.mdc` — exit codes are evidence; sentences are not

## Where this comes from

The method and the seven principles are described in *Jig-Driven Development — Stop Telling Your AI to "Be Careful"*. Short version: an AI's memory resets, its output is probabilistic, and its self-reports are unreliable. Those are not flaws to coach away; they are the spec. Address a spec with discipline and the discipline wears out. So: build tools the worker cannot route around, write the conditions for removing each tool before you build it, and treat a check that has nothing to check as an alarm, not a pass.

Half of this is what pstack's "Build the Lever" already says — give agents tools, not markdown. POKA-MON is the other half: what self-verification structurally cannot see (what wasn't done, a standard that was loosened, the danger of one's own change).

## This repository runs its own jigs

`jig.json` at the root configures POKA-MON against POKA-MON. Editing any script is track C (HAKARI: `irreversible`), `.jig/contract_ids.txt` is generated — never hand-edited — and gated by NAMAMONO, the rule files are paired with the scripts that enforce them (POKAYOKE), and the registries are watched by KARAPPO.

```bash
python3 skills/sekisho/scripts/sekisho.py --tier commit    # selftests, sakigaki, pokayoke
python3 skills/sekisho/scripts/sekisho.py --tier pr        # namamono, karappo
python3 skills/sekisho/scripts/sekisho.py --tier release   # yamedoki --evaluate
```

A change to this repository is done when those lines are green. Not when someone says so.

## Before publishing (maintainers)

1. Owner is set in `.cursor-plugin/plugin.json` (`repository`, `homepage`, `author`) and in `LICENSE` (`hetyomokore`); re-check both before the first public release.
2. Validate `plugin.json` fields against Cursor's Plugins Reference; the manifest here follows the documented field names but the component-path fields (`skills`, `rules`, `agents`) should be confirmed. Procedure: `docs/plugin-json-validation.md`.
3. Run every `--selftest`.
4. Run a secrets scan over the tree. The plugin must contain no paths, names, or values from any private environment.

## 日本語

ジグ駆動開発の7原理を、Cursor / Claude Code のスキル7本に落としたものです。各スキルは手順（`SKILL.md`）と最小動作スクリプトの組で、スクリプトはすべて `--selftest` を持ち、書き込みを伴うものはすべて `--dry-run` も持ち、終了コードで結果を返します。設定は対象リポジトリ直下の `jig.json` 1ファイル。理論は記事「ジグ駆動開発 — AIに『気をつけて』と言うのをやめる」を参照してください。

## License

MIT — see `LICENSE`.
