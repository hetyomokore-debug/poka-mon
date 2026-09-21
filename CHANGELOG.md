# Changelog

## 0.1.6 — 2026-09-21

SAKIGAKI checks a file before it exists — through a separate, explicit input. 0.1.5 made every `--changed` path exist on disk and stated the price: a file about to be created could not be checked at all, so its contract could only be confirmed once the code was written, which is the order SAKIGAKI exists to prevent. The `jig-fix-loop` workflow (not yet released) hit it at once: it checks the contract of every file a task will touch before implementation, and a task that creates a file stopped with exit 2.

- **sakigaki `--planned FILES`**: the files the change will create (REQ-CHG-2; contract `planned-paths-absent`, written before the code). They are held to the same rules as `--changed` — a planned code file that no contract names fails, and so does a contract whose `guard_test` is not on disk yet — before the file exists, which is when the check is worth something. 0.1.5's "SAKIGAKI cannot check a file that is about to be created" no longer holds
- **The rule is 0.1.5's mirror image.** A `--planned` path must *not* exist: an existing file goes in `--changed`, where the disk vouches for it. And it must be a plain path. Nothing on disk can vouch for a file that is not there, so its text is all there is: whitespace, a control character, a double quote or a backslash is refused, since such a path cannot be told apart from several paths joined into one argument or from git's quoted form of a non-ASCII name. An empty argument is refused too. Every unusable path is printed with its reason, nothing is checked, and the exit code is 2. A file whose name needs those characters is created first and checked with `--changed`
- **`--changed` is untouched.** No exception was added: a `--changed` path that does not exist is refused exactly as in 0.1.5, with or without a valid `--planned` beside it
- SEKISHO has no `--planned`: it runs once the files exist. A planned file that was never created is for the caller to stop on; SEKISHO refuses it like any other path that names nothing
- Selftests inject nine unusable `--planned` inputs through `main()` — exists, empty, joined (with an existing file, and with new files only), quoted (git), backslash, control character, a valid path mixed with an existing one, and a nonexistent `--changed` beside a valid `--planned` — and fail unless all nine are refused. Five valid inputs must be judged as expected: covered → 0, no contract → 1, guard test not on disk → 1, a non-ASCII doc → 0, a test file → 0. Selftests: 78 checks (was 75)
- Order kept: the contract first, then the selftests — red against 0.1.5, confirmed by `sakigaki --expect-red` — then the flag
- Manifests at 0.1.6

## 0.1.5 — 2026-09-21

A `--changed` path that does not exist is refused, not passed. Found in a downstream repository whose commit tier went green without having looked at what it was given. Two entrances, neither of them inside a gate:

- **The shell.** zsh does not split an unquoted `$files`, so `sekisho.py --tier commit --changed $files` delivered a whole list of changed files as one argument. SAKIGAKI saw a single path that named nothing, matched no contract, and passed — and a new source file whose contract was missing went through. The gate log showed it: `changed` held one element with every path inside it, separated by spaces.
- **git.** Without `-c core.quotepath=false`, `git diff --name-only` prints a non-ASCII path as `"docs/00_\343\203\211.md"` — the quotes and the octal escapes are part of the output. The list splits correctly, but each such element names nothing, and the gates passed without a word.

Both are KARAPPO's enemy — green without having looked — reached from the calling side. As long as a gate that reads `--changed` lets a path that names nothing through, one line written differently by the caller hollows it out.

- **sekisho, sakigaki: every `--changed` path must exist on disk** (REQ-CHG-1; contract `changed-paths-exist`, written before the code). If one does not, SEKISHO runs no gate (`--dry-run` included) and SAKIGAKI checks nothing; every such path is printed with the two usual causes and the zsh idiom that avoids both, and the exit code is 2. A refusal, not a SKIP: a skip is the hollow gate this closes. A directory or a dangling symlink exists (git lists both); an empty argument does not. A refused run writes nothing to the gate log, like any other usage error
- **A deleted file gets no exception.** It rightly does not exist; the caller leaves it out with `git diff --diff-filter=d`. An exception inside the gate would be the next entrance. The cost, stated: a gate fed from `{changed}` no longer sees deletions. SAKIGAKI loses nothing by it (a deleted file needs no contract). HAKARI, in the example commit tier, weighs a deletion where `jig-mode` already puts it — before the edit, while the file still exists; HAKARI itself keeps accepting paths that do not exist yet, since it weighs what you intend to change. 0.1.3's "a changed file that is gone is not a missing script" still holds inside `plan()`; `main()` now stops before planning
- **SAKIGAKI cannot check a file that is about to be created**: it does not exist yet, so `--changed` refuses it. The contract comes first, then the file, then the check; the SKILL says so now
- The zsh idiom in the message and the README — `files=("${(@f)$(git -c core.quotepath=false diff --name-only BASE HEAD)}")`, passed as `"${files[@]}"` — yields one empty element on an empty range. That element is refused like any other path that names nothing; omit `--changed` when nothing changed
- Selftests inject every entrance through `main()` — joined (zsh), quoted (git), absent, empty, a real path mixed with an absent one, and (sekisho) a dry run — print how many were injected against how many were stopped, and fail unless the two are equal. Real paths must still pass, and SAKIGAKI must still find the missing contract that the joined argument hid. Selftests: 75 checks (was 65)
- Order kept: the contract first, then the selftests — red against the unguarded scripts, confirmed by `sakigaki --expect-red` — then the guard
- Manifests at 0.1.5. The plugin entry in `marketplace.json` had stayed at 0.1.3 through 0.1.4; it matches now

## 0.1.4 — 2026-09-10

Cursor Marketplace submission prep.

- `logo` added (`assets/logo.png`, 512x512) — the checklist asks for a logo committed to the repo and referenced by a relative path, and the publish form asks for a 1:1 image
- `category` / `tags` removed from `.cursor-plugin/plugin.json`: neither appears in Cursor's Plugins reference nor in the official `cursor/plugin-template`. `displayName` is kept — the template uses it, even though the reference's field table omits it
- Closes the 0.1.1 known limit "manifest component-path fields have not been validated against a live Marketplace submission" for everything checkable without submitting

## 0.1.3 — 2026-09-10

Six findings from an outside review of 0.1.1/0.1.2, run against the code (selftests, end-to-end probes, and the theory the plugin claims to implement). Four are fixed here, one was withdrawn as intended design after re-reading Principle 1, and the sixth — the cited article does not exist yet — is the author's, not the code's.

- **hakari: `--override` keeps its semantics** — the requested track is applied and the machine track is logged beside it. The review first read this as a contradiction of "no self-grading" and a fix was drafted, then withdrawn: prose ("it's minor") has no effect, an explicit reasoned `--override` does and is counted later — record, don't forbid (Principle 1). SKILL and README now say so in one sentence
- **namamono: `--refresh` backs up before it overwrites.** The previous bytes go to `<log dir>/backup/<UTC ts>/<target>` and the path is printed. Without this the only file-writing path in the plugin failed the reversibility axiom (A3) of the method it implements
- **sekisho: a changed file that is gone is not a missing script.** `not_installed` tokenised the expanded command, so `--changed src/deleted.py` marked hakari and sakigaki "not installed" and SKIPped them. Installed-ness is now judged on the command without `{changed}`
- **karappo runs in the commit tier** (`jig.example.json` and this repository's `jig.json`). A run in which every gate was skipped exits 0; KARAPPO is the alarm for that, and it was only in `pr`
- **`--dry-run` on every script that writes**: namamono `--refresh` and yamedoki `--init` / `--record` gained it (hakari / sekisho already had it; sakigaki / karappo / pokayoke write nothing). README claimed `--dry-run` and gate-log lines for every script; it now says exactly which scripts write what
- New contract `namamono-backup` (REQ-A3-1), written together with the code — SAKIGAKI would otherwise have refused `namamono.py`, which no contract named
- Selftests: 65 checks (was 58)

## 0.1.2 — 2026-09-05

Trial of the schema-migration item from the 0.1.1 checklist: an existing contracts registry (the one the theory was extracted from) was pointed at the jigs. It did not fit — six differences, all of them silent failures rather than errors (`name` vs `id`, `producer`/`consumers` as objects vs strings, `guard_test` as a command vs a path, `business_critical` absent, paths rooted elsewhere, and a hand-copied second table that would rot). This release makes the registry usable without copying it.

- `contracts` may name registry JSON files (strings) alongside inline entries; a bare string is one registry. Read by hakari, sakigaki, and `tools/gen_contract_ids.py`
- Contract entries are normalized from either shape: `name`→`id`, `producer: {file, fields}`→path, `consumers: [{file, reads}]`→paths, `business_critical` defaults to `false`; unknown keys are kept and ignored
- sakigaki: `guard_test` may be a command (`tools/check.py --selftest`); the first token is what must exist on disk
- karappo: a `hollow` path that resolves to a string (a reference, not a registry) is an error, never counted as entries
- LICENSE copyright holder set (was the placeholder "POKA-MON contributors")
- Selftests: 58 checks (was 50)
- `docs/plugin-json-validation.md`: maintainer procedure for checking the manifest against Cursor's reference, the publish form, and a live install
- Dogfooding: a `jig-config-contracts` contract now names `jig.example.json` as the producer of the `contracts` shape and hakari / sakigaki / `gen_contract_ids.py` as its consumers; `.jig/contract_ids.txt` regenerated

What dogfooding found: the commit tier refused this change — SAKIGAKI reported that `sakigaki.py` and `tools/gen_contract_ids.py` were named by no contract. The contract above was written after the code, which is exactly the order the jig exists to catch; the guard (the new selftests) was written together with the code, not after. Recorded here rather than hidden.

## 0.1.1 — 2026-09-02

Scripts committed. 0.1.0 on `main` was README, LICENSE and CHANGELOG only; a parallel commit on `main` described scripts that were not there. This release makes the description true, and resolves that divergence in favor of the code that exists.

- Seven skills with procedures and working scripts: hakari, sekisho, sakigaki, namamono, karappo, pokayoke, yamedoki — standard library only, `--selftest`, `--dry-run` where meaningful, JSONL gate log, exit codes 0/1/2 (karappo adds 3 = HOLLOW)
- `/jig-mode` router skill; three always-on rules under `rules/`; `jig-auditor` subagent
- `jig.example.json` configuration template for target repositories
- `{config}` placeholder in gate commands (sekisho), alongside `{plugin}` and `{changed}`
- yamedoki: a rate with fewer than `yamedoki_min_samples` (default 10) samples is shown but not judged — no day-one abolish verdicts
- **The repository runs its own jigs**: `jig.json` at the root, `.jig/contract_ids.txt` generated by `tools/gen_contract_ids.py` and gated by NAMAMONO, rule→script pairings checked by POKAYOKE, registries watched by KARAPPO, retirement conditions registered for SEKISHO

Known limits (deliberately unhidden):

- Contract matching is glob-based; indirect references through variables or dynamic keys are not seen
- Bypasses that skip the gate entirely (`git commit --no-verify`) are not observed; record them with `yamedoki --record bypass`
- Manifest component-path fields (`skills`, `rules`, `agents`) follow the documented names but have not been validated against a live Marketplace submission

## 0.1.0 — 2026-09-02

Bootstrap: README, LICENSE, CHANGELOG. No scripts.
