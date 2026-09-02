# POKA-MON

**Seven monsters that don't work. That's the job.**

A Cursor / Claude Code plugin for **Jig-Driven Development**: quality lives in machine checkpoints (*jigs*) the worker cannot bypass — not in anyone's attention, and not in the sentence "I checked it."

Seven skills, one principle each, one script each. Every script has `--selftest` and `--dry-run`, returns machine-readable exit codes, and appends one JSON line to a gate log. No dependencies beyond Python 3.8+.

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
- **Claude Code** — the `skills/*/SKILL.md` files are standard Agent Skills. Copy or symlink `skills/*` into `.claude/skills/` (project) or `~/.claude/skills/` (personal); the `rules/*.mdc` content maps to `CLAUDE.md` guidance.
- **Anything else that reads Agent Skills** — same `SKILL.md` files.

## Configuration (`jig.json`)

| Key | Read by | Meaning |
|---|---|---|
| `log` | all | path of the JSONL gate log (default `.jig/gate_log.jsonl`) |
| `contracts[]` | hakari, sakigaki | `id`, `producer`, `consumers[]`, `fields[]`, `requirements[]`, `guard_test`, `business_critical` |
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

## Before publishing (maintainers)

1. Set the real owner in `.cursor-plugin/plugin.json` (`repository`, `homepage`, `author`) and in `LICENSE`.
2. Validate `plugin.json` fields against Cursor's Plugins Reference; the manifest here follows the documented field names but the component-path fields (`skills`, `rules`, `agents`) should be confirmed.
3. Run every `--selftest`.
4. Run a secrets scan over the tree. The plugin must contain no paths, names, or values from any private environment.

## 日本語

ジグ駆動開発の7原理を、Cursor / Claude Code のスキル7本に落としたものです。各スキルは手順（`SKILL.md`）と最小動作スクリプトの組で、スクリプトはすべて `--selftest` と `--dry-run` を持ち、終了コードで結果を返します。設定は対象リポジトリ直下の `jig.json` 1ファイル。理論は記事「ジグ駆動開発 — AIに『気をつけて』と言うのをやめる」を参照してください。

## License

MIT — see `LICENSE`.
