export const meta = {
  name: 'poka-mon-gate-loop',
  description: 'HAKARI risk track -> SAKIGAKI contract-first (track B/C) -> implement -> SEKISHO gate loop with bounded auto-fix',
  phases: [
    { title: 'Risk (HAKARI)', detail: 'compute track A/B/C for the files about to change' },
    { title: 'Contract-first (SAKIGAKI)', detail: 'track B/C only: verify or author the contract+guard test BEFORE implementation' },
    { title: 'Implement', detail: 'apply the requested change' },
    { title: 'Gate loop (SEKISHO)', detail: 'run tier gates; on FAIL spawn a fixer agent; up to sekishoMaxAttempts total checks' },
  ],
}

// args = {
//   repoRoot: string (required)        — repo that has this plugin installed and a jig.json
//   pluginRoot: string (default repoRoot) — resolves {plugin} in jig.json gate commands
//   configPath: string (default 'jig.json')
//   changedFiles: string[] (required)  — files this task is about to touch
//   task: string (required)            — description of the change to implement
//   tier: 'commit'|'pr'|'release' (default 'commit')
//   sakigakiMaxAttempts: number (default 2)
//   sekishoMaxAttempts: number (default 3)
// }
//
// Returns one of:
//   { status: 'PASSED', track, sekishoAttempts, sakigakiAttempts, summary }
//   { status: 'BLOCKED_NEEDS_HUMAN', stage: 'sakigaki'|'sekisho', ... }   -- do not commit/merge past this
//   { status: 'BLOCKED_CONFIG_ERROR', stage, detail }                    -- jig.json/usage problem, not a code bug
//
// "Block" here means: the workflow stops making further automatic fix attempts and
// returns an escalation object. There is no synchronous human-in-the-loop pause inside
// a Workflow script — the caller must treat a BLOCKED_* result as "do not proceed".

if (!args || !args.repoRoot || !Array.isArray(args.changedFiles) || args.changedFiles.length === 0 || !args.task) {
  throw new Error('poka-mon-gate-loop requires args: {repoRoot, changedFiles: string[], task}')
}

const repoRoot = args.repoRoot
const pluginRoot = args.pluginRoot || args.repoRoot
const configPath = args.configPath || 'jig.json'
const changedFiles = args.changedFiles
const changedArg = changedFiles.map(f => `"${f}"`).join(' ')
const tier = args.tier || 'commit'
const sakigakiMaxAttempts = args.sakigakiMaxAttempts || 2
const sekishoMaxAttempts = args.sekishoMaxAttempts || 3

const HAKARI_SCHEMA = {
  type: 'object',
  properties: {
    exitCode: { type: 'number' },
    track: { type: 'string', enum: ['A', 'B', 'C'] },
    machineTrack: { type: 'string', enum: ['A', 'B', 'C'] },
    rawOutput: { type: 'string' },
  },
  required: ['exitCode', 'track', 'machineTrack', 'rawOutput'],
}

const SAKIGAKI_CHECK_SCHEMA = {
  type: 'object',
  properties: {
    exitCode: { type: 'number' },
    pass: { type: 'boolean' },
    violation: { type: 'string' },
    rawOutput: { type: 'string' },
  },
  required: ['exitCode', 'pass', 'rawOutput'],
}

const SEKISHO_CHECK_SCHEMA = {
  type: 'object',
  properties: {
    exitCode: { type: 'number' },
    pass: { type: 'boolean' },
    summaryLine: { type: 'string' },
    failedGates: { type: 'array', items: { type: 'string' } },
    skippedGates: { type: 'array', items: { type: 'string' } },
    rawOutput: { type: 'string' },
  },
  required: ['exitCode', 'pass', 'summaryLine', 'failedGates', 'skippedGates', 'rawOutput'],
}

async function checkAgent(prompt, opts) {
  const result = await agent(prompt, opts)
  if (!result) throw new Error(`${opts.label}: agent produced no result (died or was skipped) — treat as a blocking failure, do not assume pass`)
  return result
}

// --- Phase 1: HAKARI -------------------------------------------------------
phase('Risk (HAKARI)')
const hakari = await checkAgent(
  `Repo root: ${repoRoot}\nPlugin root: ${pluginRoot}\nConfig: ${configPath}\n\n` +
    `Run exactly this command from the repo root and report the result:\n` +
    `python3 ${pluginRoot}/skills/hakari/scripts/hakari.py --config ${configPath} --changed ${changedArg} --json\n\n` +
    `Parse the JSON line it prints (or the plain-text line if --json is unsupported by this version). Report: ` +
    `exit code as exitCode, the "track" field as track, the "machine_track" field as machineTrack, and the full ` +
    `stdout/stderr as rawOutput. Do NOT edit any files. Do NOT pass --override yourself — this is a read-only measurement.`,
  { label: 'hakari', phase: 'Risk (HAKARI)', schema: HAKARI_SCHEMA }
)
log(`HAKARI: track=${hakari.track} (machine=${hakari.machineTrack}) exit=${hakari.exitCode}`)

if (hakari.exitCode === 2) {
  return { status: 'BLOCKED_CONFIG_ERROR', stage: 'hakari', detail: hakari.rawOutput }
}

// --- Phase 2: SAKIGAKI, track B/C only, strictly before implementation -----
let sakigaki = null
let sakigakiAttempts = 0
if (hakari.track === 'B' || hakari.track === 'C') {
  phase('Contract-first (SAKIGAKI)')
  while (sakigakiAttempts < sakigakiMaxAttempts) {
    sakigakiAttempts++
    sakigaki = await checkAgent(
      `Repo root: ${repoRoot}\nPlugin root: ${pluginRoot}\nConfig: ${configPath}\n\n` +
        `Run: python3 ${pluginRoot}/skills/sakigaki/scripts/sakigaki.py --config ${configPath} --changed ${changedArg}\n` +
        `Report exit code as exitCode, pass=(exitCode===0), the violation message verbatim in "violation" if it failed, ` +
        `and the full output as rawOutput.`,
      { label: `sakigaki-check-${sakigakiAttempts}`, phase: 'Contract-first (SAKIGAKI)', schema: SAKIGAKI_CHECK_SCHEMA }
    )
    log(`SAKIGAKI attempt ${sakigakiAttempts}/${sakigakiMaxAttempts}: exit=${sakigaki.exitCode} pass=${sakigaki.pass}`)
    if (sakigaki.pass) break
    if (sakigaki.exitCode === 2) {
      return { status: 'BLOCKED_CONFIG_ERROR', stage: 'sakigaki', detail: sakigaki.rawOutput }
    }
    if (sakigakiAttempts >= sakigakiMaxAttempts) break
    await agent(
      `SAKIGAKI reported this violation for task "${args.task}":\n${sakigaki.violation || sakigaki.rawOutput}\n\n` +
        `Repo root: ${repoRoot}. Config: ${configPath}. Files about to be touched (NOT YET implemented): ${changedFiles.join(', ')}.\n\n` +
        `Follow SAKIGAKI's contract-first order exactly. Do NOT write any implementation code in this step:\n` +
        `1. Add a contracts[] entry to ${configPath} for the producer file(s) among the changed files: id, producer, consumers, ` +
        `fields, requirements, guard_test. Only name a guard_test path you are about to create in step 2 — never register ` +
        `one that does not exist yet (that is decoration, forbidden by SAKIGAKI).\n` +
        `2. Write the failing guard test for that contract now, then prove it is red:\n` +
        `   python3 ${pluginRoot}/skills/sakigaki/scripts/sakigaki.py --expect-red --cmd "<your test command>"\n` +
        `3. Touch only ${configPath} and the new test file(s) — no implementation files.\n` +
        `Report exactly what you changed.`,
      { label: `sakigaki-fix-${sakigakiAttempts}`, phase: 'Contract-first (SAKIGAKI)' }
    )
  }
  if (!sakigaki.pass) {
    return {
      status: 'BLOCKED_NEEDS_HUMAN',
      stage: 'sakigaki',
      track: hakari.track,
      attempts: sakigakiAttempts,
      detail: sakigaki.rawOutput,
      message: `SAKIGAKI still failing after ${sakigakiAttempts} attempt(s) on track ${hakari.track}. A human must author ` +
        `the contract/guard test before any implementation proceeds — do not implement on top of an unresolved contract violation.`,
    }
  }
}

// --- Phase 3: Implement -----------------------------------------------------
phase('Implement')
const implementation = await agent(
  `Repo root: ${repoRoot}. Risk track: ${hakari.track}.\n` +
    (sakigaki ? `SAKIGAKI's contract and guard test are already in place and were proven red before this step.\n` : '') +
    `Task: ${args.task}\n\n` +
    `Implement this change, touching only: ${changedFiles.join(', ')} (plus the guard test file(s) already created for track B/C). ` +
    `Do not run sekisho yourself — the workflow runs it next. Report a short summary of what you changed.`,
  { label: 'implement', phase: 'Implement' }
)
log(`Implement: ${typeof implementation === 'string' ? implementation.slice(0, 200) : 'done'}`)

// --- Phase 4: SEKISHO gate loop with bounded auto-fix ------------------------
phase('Gate loop (SEKISHO)')
let sekisho = null
let sekishoAttempts = 0
while (sekishoAttempts < sekishoMaxAttempts) {
  sekishoAttempts++
  sekisho = await checkAgent(
    `Repo root: ${repoRoot}\n` +
      `Run: python3 ${pluginRoot}/skills/sekisho/scripts/sekisho.py --config ${configPath} --tier ${tier} --changed ${changedArg}\n` +
      `Report exit code as exitCode, pass=(exitCode===0), each FAIL line verbatim in failedGates, each SKIP line verbatim ` +
      `in skippedGates, the "=== N PASS / N FAIL / N SKIP ===" line as summaryLine, and the full output as rawOutput. ` +
      `Quote FAIL lines verbatim — never paraphrase them into "some checks failed".`,
    { label: `sekisho-check-${sekishoAttempts}`, phase: 'Gate loop (SEKISHO)', schema: SEKISHO_CHECK_SCHEMA }
  )
  log(`SEKISHO attempt ${sekishoAttempts}/${sekishoMaxAttempts}: ${sekisho.summaryLine}`)
  if (sekisho.pass) break
  if (sekisho.exitCode === 2) {
    return { status: 'BLOCKED_CONFIG_ERROR', stage: 'sekisho', attempts: sekishoAttempts, detail: sekisho.rawOutput }
  }
  if (sekishoAttempts >= sekishoMaxAttempts) break
  await agent(
    `SEKISHO tier=${tier} failed on attempt ${sekishoAttempts}/${sekishoMaxAttempts}:\n${sekisho.rawOutput}\n\n` +
      `Failed gates verbatim: ${sekisho.failedGates.join(' | ')}\n\n` +
      `Repo root: ${repoRoot}. Task: ${args.task}. Changed files: ${changedFiles.join(', ')}.\n` +
      `Analyze the failure(s) above and fix the underlying defect. Do NOT weaken, skip, delete, or disable the failing ` +
      `gate/test to force a green result — that is exactly the "green by deletion" failure mode KARAPPO exists to catch, ` +
      `and it will be caught. Do not touch files outside this change's scope. Report what you changed and why each failure ` +
      `should now be fixed.`,
    { label: `sekisho-fix-${sekishoAttempts}`, phase: 'Gate loop (SEKISHO)' }
  )
}

if (sekisho.pass) {
  return {
    status: 'PASSED',
    track: hakari.track,
    sakigakiAttempts,
    sekishoAttempts,
    summary: sekisho.summaryLine,
  }
}

return {
  status: 'BLOCKED_NEEDS_HUMAN',
  stage: 'sekisho',
  track: hakari.track,
  sakigakiAttempts,
  sekishoAttempts,
  failedGates: sekisho.failedGates,
  summary: sekisho.summaryLine,
  rawOutput: sekisho.rawOutput,
  message: `SEKISHO tier=${tier} is still failing after ${sekishoMaxAttempts} auto-fix attempts. Escalating to a human — ` +
    `do not commit or merge. Quote the FAIL line(s) verbatim in the report; do not paraphrase them into "some checks failed".`,
}
