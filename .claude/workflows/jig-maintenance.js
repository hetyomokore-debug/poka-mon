export const meta = {
  name: 'jig-maintenance',
  description: 'Scan the repo for producer/consumer and rule/enforcement pairs missing from jig.json contracts[]/pairings[], and register only the ones with real, on-disk evidence',
  phases: [
    { title: 'Scan' },
    { title: 'Update' },
    { title: 'Verify' },
  ],
}

// args = {
//   repoRoot: string (required)
//   pluginRoot: string (default repoRoot)
//   configPath: string (default 'jig.json')
//   scanPaths: string[] (default ['.'])   — directories/globs to scan for candidates, repo-relative
//   dryRun: boolean (default false)       — report candidates only, never write jig.json
// }
//
// What this does NOT do (by design, to stay compliant with SAKIGAKI/POKAYOKE's own rules):
//  - Never invents a guard_test path that doesn't exist on disk (that is "decoration").
//  - Never invents an enforcement mechanism for a declaration that has none (that is a
//    genuine "sign without lock" gap — jig-auditor's job to report, not this workflow's
//    job to paper over). Only registers pairs where BOTH sides are independently verified
//    to already exist; everything else goes to `findings` for a human.
//  - This is a maintenance sweep for registration drift, not a substitute for running
//    SAKIGAKI contract-first on every new change (see poka-mon-gate-loop.js for that).

if (!args || !args.repoRoot) {
  throw new Error('jig-maintenance requires args: {repoRoot}')
}

const repoRoot = args.repoRoot
const pluginRoot = args.pluginRoot || args.repoRoot
const configPath = args.configPath || 'jig.json'
const scanPaths = (args.scanPaths && args.scanPaths.length ? args.scanPaths : ['.']).join(' ')
const dryRun = !!args.dryRun

const CONTRACT_SCAN_SCHEMA = {
  type: 'object',
  properties: {
    candidates: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          suggested_id: { type: 'string' },
          producer: { type: 'string' },
          consumers: { type: 'array', items: { type: 'string' } },
          fields: { type: 'array', items: { type: 'string' } },
          requirements: { type: 'array', items: { type: 'string' } },
          guard_test: { type: 'string' },
          business_critical: { type: 'boolean' },
          evidence: { type: 'string' },
        },
        required: ['suggested_id', 'producer', 'consumers', 'guard_test', 'evidence'],
      },
    },
    findings: { type: 'array', items: { type: 'string' } },
  },
  required: ['candidates', 'findings'],
}

const PAIRING_SCAN_SCHEMA = {
  type: 'object',
  properties: {
    candidates: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          name: { type: 'string' },
          declarationFile: { type: 'string' },
          declarationContains: { type: 'string' },
          enforcementFile: { type: 'string' },
          enforcementContains: { type: 'string' },
          evidence: { type: 'string' },
        },
        required: ['name', 'declarationFile', 'enforcementFile', 'evidence'],
      },
    },
    findings: { type: 'array', items: { type: 'string' } },
  },
  required: ['candidates', 'findings'],
}

const WRITE_SCHEMA = {
  type: 'object',
  properties: {
    applied: { type: 'boolean' },
    addedContracts: { type: 'number' },
    addedPairings: { type: 'number' },
    backupPath: { type: 'string' },
    diffSummary: { type: 'string' },
  },
  required: ['applied', 'addedContracts', 'addedPairings', 'backupPath', 'diffSummary'],
}

const VERIFY_SCHEMA = {
  type: 'object',
  properties: {
    karappoExit: { type: 'number' },
    pokayokeExit: { type: 'number' },
    sakigakiSelftestExit: { type: 'number' },
    ok: { type: 'boolean' },
    rolledBack: { type: 'boolean' },
    detail: { type: 'string' },
  },
  required: ['karappoExit', 'pokayokeExit', 'sakigakiSelftestExit', 'ok', 'rolledBack', 'detail'],
}

// --- Phase 1: Scan (two independent, self-verifying scanners) --------------
phase('Scan')
const [contractScan, pairingScan] = await parallel([
  () =>
    agent(
      `Repo root: ${repoRoot}. Config: ${configPath}. Scan scope: ${scanPaths} (exclude .git, node_modules, .jig).\n\n` +
        `1. Read ${configPath} and list the "producer" path already registered in each contracts[] entry.\n` +
        `2. Search the scan scope for producer -> consumer relationships NOT already covered by an existing contract: ` +
        `files whose output (exported data structure, generated file, shared schema, public module/API) is read by at ` +
        `least one other file (use grep/ripgrep for imports/requires/reads across files to find real edges — do not guess).\n` +
        `3. For each such relationship, check with the shell whether a plausible guard test for the producer ALREADY EXISTS ` +
        `on disk (e.g. an existing test file covering it). If yes, include it as a candidate with that real guard_test path. ` +
        `If no guard test exists yet, do NOT invent one — instead add a plain-text line to "findings" describing the gap ` +
        `(producer, consumers, and "no guard test yet") so a human can write the guard test first, contract-first.\n` +
        `4. Only return candidates you have verified against the actual files on disk (paths must exist). Never fabricate ` +
        `a producer, consumer, or guard_test path.\n` +
        `Return JSON: candidates[] (suggested_id, producer, consumers, fields, requirements, guard_test, business_critical, ` +
        `evidence — evidence must cite the actual file(s)/lines you found) and findings[] (verified gaps you could not ` +
        `safely turn into a candidate). Do not edit any files.`,
      { label: 'scan-contracts', phase: 'Scan', schema: CONTRACT_SCAN_SCHEMA }
    ),
  () =>
    agent(
      `Repo root: ${repoRoot}. Config: ${configPath}. Scan scope: ${scanPaths} (exclude .git, node_modules, .jig).\n\n` +
        `1. Read ${configPath} and list the pairings[] already registered (by name).\n` +
        `2. Search docs/rule files (CLAUDE.md, AGENTS.md, README.md, rules/*.mdc, docs/**/*.md) for imperative rule ` +
        `sentences ("never do X", "must Y", "always Z", "do not ...").\n` +
        `3. For each declaration, search for a real enforcement artifact elsewhere in the repo (hook config, settings ` +
        `deny-list, lint rule, assertion in code, CI check) whose file content genuinely contains matching text — verify ` +
        `with grep, do not guess.\n` +
        `4. Only include a candidate when BOTH the declaration text AND the enforcement text are verified to exist on ` +
        `disk right now, and the pair is not already registered in pairings[]. If a declaration has no real enforcement ` +
        `anywhere (or an enforcement has no declared rule anywhere), do NOT invent the missing side — add it to findings ` +
        `as "sign without lock" or "lock without sign" for a human to fix, exactly like jig-auditor would report it.\n` +
        `Return JSON: candidates[] (name, declarationFile, declarationContains, enforcementFile, enforcementContains, ` +
        `evidence citing the actual files) and findings[] (verified sign-without-lock / lock-without-sign gaps). ` +
        `Do not edit any files.`,
      { label: 'scan-pairings', phase: 'Scan', schema: PAIRING_SCAN_SCHEMA }
    ),
])

const contracts = contractScan ? contractScan.candidates : []
const pairings = pairingScan ? pairingScan.candidates : []
const findings = [...(contractScan ? contractScan.findings : []), ...(pairingScan ? pairingScan.findings : [])]

log(`Scan: ${contracts.length} contract candidate(s), ${pairings.length} pairing candidate(s), ${findings.length} finding(s) needing a human`)

if (contracts.length === 0 && pairings.length === 0) {
  return { status: 'NOTHING_TO_REGISTER', findings }
}

if (dryRun) {
  return { status: 'DRY_RUN', contracts, pairings, findings }
}

// --- Phase 2: Update (single writer to avoid concurrent edits to one file) --
phase('Update')
const write = await agent(
  `Repo root: ${repoRoot}. Config: ${configPath}. Plugin root: ${pluginRoot}.\n\n` +
    `Contract candidates to register (already verified to exist on disk by a prior scan):\n${JSON.stringify(contracts, null, 2)}\n\n` +
    `Pairing candidates to register (already verified to exist on disk by a prior scan):\n${JSON.stringify(pairings, null, 2)}\n\n` +
    `Steps:\n` +
    `1. Back up first: run \`cp ${configPath} ${configPath}.bak.$(date +%Y%m%d%H%M%S)\` from the repo root. Report the backup path.\n` +
    `2. Re-read ${configPath} now (it may have changed since the scan) and append only the candidates whose id/name is not ` +
    `already present in contracts[]/pairings[] — this must be idempotent.\n` +
    `3. Write the updated ${configPath} preserving existing formatting/ordering as much as possible.\n` +
    `4. Validate it is still valid JSON: \`python3 -c "import json; json.load(open('${configPath}'))"\`.\n` +
    `5. If jig.json declares a "generated" entry for .jig/contract_ids.txt, refresh it: ` +
    `\`python3 ${pluginRoot}/tools/gen_contract_ids.py ${pluginRoot}/.jig/contract_ids.txt ${configPath}\`.\n` +
    `Report applied=true, addedContracts, addedPairings, backupPath, and a diffSummary (short unified-diff-style summary).`,
  { label: 'write-jig-json', phase: 'Update', schema: WRITE_SCHEMA }
)

if (!write || !write.applied) {
  return { status: 'WRITE_FAILED', contracts, pairings, findings, write }
}

// --- Phase 3: Verify the edit didn't break the jig registries --------------
phase('Verify')
const verify = await agent(
  `Repo root: ${repoRoot}. Plugin root: ${pluginRoot}. Config: ${configPath}. Backup: ${write.backupPath}.\n\n` +
    `Run, in this exact order (same order jig-auditor uses):\n` +
    `1. python3 ${pluginRoot}/skills/karappo/scripts/karappo.py --config ${configPath}\n` +
    `2. python3 ${pluginRoot}/skills/pokayoke/scripts/pokayoke.py --config ${configPath}\n` +
    `3. python3 ${pluginRoot}/skills/sakigaki/scripts/sakigaki.py --selftest\n\n` +
    `Report each exit code. If ANY of them fail (karappo exit 3 HOLLOW, pokayoke exit 1, or sakigaki selftest non-zero), ` +
    `the edit broke a registry: restore it with \`cp ${write.backupPath} ${configPath}\`, set rolledBack=true, and explain ` +
    `which check failed and why in detail. Otherwise set ok=true, rolledBack=false.`,
  { label: 'verify-after-write', phase: 'Verify', schema: VERIFY_SCHEMA }
)

return {
  status: verify && verify.ok ? 'REGISTERED' : 'REGISTERED_THEN_ROLLED_BACK',
  addedContracts: write.addedContracts,
  addedPairings: write.addedPairings,
  backupPath: write.backupPath,
  diffSummary: write.diffSummary,
  findings,
  verify,
}
