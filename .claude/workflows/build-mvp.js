/*
 * PHASE SPECIFICATION -- NOT AN EXECUTABLE.
 *
 * This file is not runnable and never was in this environment. It calls
 * `agent()`, `phase()`, `capability()` and `reportProgress()`, which are
 * primitives injected by a workflow host that Claude Code does not provide,
 * and it uses a top-level `return` -- Node rejects it with
 * "SyntaxError: Illegal return statement" before any of that matters.
 *
 * Read it as the authoritative phase order, gate placement and per-phase
 * prompt wording for an autonomous MVP build. The `mvp-builder` skill drives
 * those phases using the real Skill and Agent tools; see its Execution
 * Sequence for the phase-to-mechanism mapping.
 */

export const meta = {
  name: 'build-mvp',
  description: 'Autonomous, zero-checkpoint MVP build: PRD -> architecture -> scaffold -> implement -> pre-deploy gate -> QA -> deploy -> handoff',
  phases: [
    { title: 'Intake', detail: 'workspace setup, complexity triage' },
    { title: 'PRD', detail: 'requirements-analyst' },
    { title: 'Architecture', detail: 'stack-selector' },
    { title: 'Scaffold', detail: 'repo-onboarding, conventions' },
    { title: 'Implement', detail: 'per-feature: implement -> code-review (incl. no-slop-check), with recovery' },
    { title: 'Pre-deploy Gate', detail: 'code-review whole-repo pass' },
    { title: 'QA', detail: 'acceptance-criteria-driven verification' },
    { title: 'Deploy', detail: 'deployment-pilot' },
    { title: 'Handoff', detail: 'knowledge-manager' },
  ],
}

// Hand-maintained, mirrors each skill's frontmatter provides/requires block.
// Workflow scripts have no filesystem access, so this can't be read from
// SKILL.md at runtime -- keep it in sync by hand when a skill's capabilities change.
// Absolute path, deliberately not '~/...' -- subagents dispatched via agent() are told
// to Read this path, and the Read tool requires an absolute path (no tilde expansion).
//
// This pointed at 'C:/Users/VikasVijigiri/.claude/skills' until 2026-07-31 -- the global
// layer, which was deleted on 2026-07-30. All 22 CAPABILITY_MANIFEST paths below
// therefore resolved to a directory that does not exist, and every subagent dispatched
// with one was told to Read nothing. It points into this repo now, because this repo is
// where every skill lives.
//
// Still machine-specific: whoever drives these phases must substitute the real absolute
// path to this checkout before handing a path to a subagent. Verify one path resolves
// before dispatching twenty-two of them.
const REPO_ROOT = 'c:/Users/VikasVijigiri/Documents/FDE_Vikas/Notes'
const SKILLS_ROOT = `${REPO_ROOT}/.claude/skills`
const CAPABILITY_MANIFEST = {
  'prd': { skill: 'requirements-analyst', path: `${SKILLS_ROOT}/requirements-analyst/SKILL.md` },
  'acceptance-criteria': { skill: 'requirements-analyst', path: `${SKILLS_ROOT}/requirements-analyst/SKILL.md` },
  'scope-cut': { skill: 'requirements-analyst', path: `${SKILLS_ROOT}/requirements-analyst/SKILL.md` },
  'architecture': { skill: 'stack-selector', path: `${SKILLS_ROOT}/stack-selector/SKILL.md` },
  'stack': { skill: 'stack-selector', path: `${SKILLS_ROOT}/stack-selector/SKILL.md` },
  'adr': { skill: 'stack-selector', path: `${SKILLS_ROOT}/stack-selector/SKILL.md` },
  'conventions': { skill: 'repo-onboarding', path: `${SKILLS_ROOT}/repo-onboarding/SKILL.md` },
  'review': { skill: 'code-review', path: `${SKILLS_ROOT}/code-review/SKILL.md` },
  'quality-sweep': { skill: 'no-slop-check', path: `${SKILLS_ROOT}/no-slop-check/SKILL.md` },
  'deployment': { skill: 'deployment-pilot', path: `${SKILLS_ROOT}/deployment-pilot/SKILL.md` },
  'health-endpoint': { skill: 'deployment-pilot', path: `${SKILLS_ROOT}/deployment-pilot/SKILL.md` },
  'secrets-triage': { skill: 'deployment-pilot', path: `${SKILLS_ROOT}/deployment-pilot/SKILL.md` },
  'prerequisites-checklist': { skill: 'deployment-pilot', path: `${SKILLS_ROOT}/deployment-pilot/SKILL.md` },
  'diagnosis': { skill: 'error-recovery', path: `${SKILLS_ROOT}/error-recovery/SKILL.md` },
  'fix': { skill: 'error-recovery', path: `${SKILLS_ROOT}/error-recovery/SKILL.md` },
  'issue-record': { skill: 'error-recovery', path: `${SKILLS_ROOT}/error-recovery/SKILL.md` },
  'knowledge-update': { skill: 'knowledge-manager', path: `${SKILLS_ROOT}/knowledge-manager/SKILL.md` },
  'intent-capture': { skill: 'task-intake', path: `${SKILLS_ROOT}/task-intake/SKILL.md` },
  'task-brief': { skill: 'task-intake', path: `${SKILLS_ROOT}/task-intake/SKILL.md` },
  'outcome-review': { skill: 'business-outcome-review', path: `${SKILLS_ROOT}/business-outcome-review/SKILL.md` },
  'context-audit': { skill: 'context-economy-audit', path: `${SKILLS_ROOT}/context-economy-audit/SKILL.md` },
}

function capability(name) {
  const entry = CAPABILITY_MANIFEST[name]
  if (!entry) throw new Error(`build-mvp.js: no skill provides capability '${name}' -- update CAPABILITY_MANIFEST`)
  return entry
}

function skillPrompt(capabilityName, task) {
  const entry = capability(capabilityName)
  return `Read and follow ${entry.path} (the '${entry.skill}' skill) exactly.\n\n${task}`
}

// Cost optimization: route narrow, mechanical, high-frequency calls (fix a
// named issue, verify pass/fail, log an entry, report progress) to a cheap
// model -- reserve the inherited/default model for calls that need real
// judgment (PRD, architecture, per-feature implementation and review,
// diagnosis, pre-deploy gate, QA, deploy, the final handoff report).
const CHEAP_MODEL = 'claude-haiku-4-5-20251001'
const CHEAP = { model: CHEAP_MODEL, effort: 'low' }

const PRD_SCHEMA = {
  type: 'object',
  properties: {
    goal: { type: 'string' },
    features: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          name: { type: 'string' },
          acceptanceCriteria: { type: 'array', items: { type: 'string' } },
          cutForV1: { type: 'boolean' },
        },
        required: ['name', 'acceptanceCriteria'],
      },
    },
  },
  required: ['goal', 'features'],
}

const STACK_SCHEMA = {
  type: 'object',
  properties: {
    architecturePattern: { type: 'string' },
    summary: { type: 'string' },
    host: { type: 'string' },
  },
  required: ['architecturePattern', 'summary'],
}

const WORKSPACE_SCHEMA = {
  type: 'object',
  properties: {
    ok: { type: 'boolean' },
    path: { type: 'string' },
    error: { type: 'string' },
    editorOpened: { type: 'boolean' },
  },
  required: ['ok', 'path'],
}

const OK_ERROR_SCHEMA = {
  type: 'object',
  properties: { ok: { type: 'boolean' }, error: { type: 'string' } },
  required: ['ok'],
}

const OK_ERROR_URL_SCHEMA = {
  type: 'object',
  properties: { ok: { type: 'boolean' }, error: { type: 'string' }, url: { type: 'string' } },
  required: ['ok'],
}

const OK_ERROR_RESULTS_SCHEMA = {
  type: 'object',
  properties: { ok: { type: 'boolean' }, error: { type: 'string' }, results: {} },
  required: ['ok'],
}

const PASS_FINDINGS_SCHEMA = {
  type: 'object',
  properties: { pass: { type: 'boolean' }, findings: {} },
  required: ['pass'],
}

const DIAGNOSIS_SCHEMA = {
  type: 'object',
  properties: {
    rootCause: { type: 'string' },
    fix: { type: 'string' },
    files: { type: 'array', items: { type: 'string' } },
  },
  required: ['rootCause'],
}

// agent() returns null if a subagent dies on a terminal error (or is skipped) --
// never assume the result of an agent() call is an object without checking first.
function normalizeResult(result, context) {
  if (result && typeof result === 'object') return result
  return { ok: false, error: `agent() returned ${result === null ? 'null' : typeof result} (subagent failed or was skipped) during ${context}` }
}

// A session/rate limit or provider outage is not a code bug -- no diagnose/fix
// call will get past it, and attempting one just fails identically, burning
// tokens on calls that were never going to succeed (this happened for real:
// one run generated 31 failed recovery-loop calls hitting the same wall).
const INFRASTRUCTURE_FAILURE_PATTERN = /session limit|rate.?limit|temporarily unavailable|quota exceeded|overloaded/i

function isInfrastructureFailure(error) {
  return INFRASTRUCTURE_FAILURE_PATTERN.test(String(error || ''))
}

// Four-state phase exit: Continue (ok), Retry (internal to this loop), Blocked
// (logged, caller decides whether to route around it), Abort is the caller's
// call for a foundational phase -- this function only ever returns Continue/Blocked.
// MAX_ATTEMPTS default lowered 3 -> 2: each retry round is a full diagnose+fix+
// verify(+log) cycle -- one fewer allowed round is a real, compounding saving.
async function withRecovery(phaseName, runPhase, verifyPhase, ctx) {
  const MAX_ATTEMPTS = (ctx && ctx.maxAttempts) || 2
  const attempts = []
  let result = normalizeResult(await runPhase(), `${phaseName}:run`)

  while (!result.ok && attempts.length < MAX_ATTEMPTS) {
    if (isInfrastructureFailure(result.error)) {
      attempts.push({
        hypothesis: 'infrastructure/quota failure, not a code issue -- further agent calls would fail identically',
        outcome: 'not retried',
      })
      break
    }
    // Diagnosis is real reasoning (root-causing an unfamiliar failure) -- keep
    // it on the default/capable model and pointed at the error-recovery skill.
    const diagnosis = normalizeResult(await agent(
      skillPrompt('diagnosis', buildDiagnosePrompt(phaseName, result.error, attempts)),
      { label: `diagnose:${phaseName}`, phase: 'Implement', schema: DIAGNOSIS_SCHEMA }
    ), `${phaseName}:diagnose`)
    if (!diagnosis.rootCause || repeatsPriorHypothesis(diagnosis, attempts)) break

    // Applying an already-diagnosed, concretely-scoped fix is mechanical
    // execution, not judgment -- cheap model, and skip the skill-file read
    // (the diagnosis already contains everything needed to apply it).
    await agent(buildApplyPrompt(diagnosis), { label: `fix:${phaseName}`, phase: 'Implement', ...CHEAP })
    result = normalizeResult(await verifyPhase(), `${phaseName}:verify`)
    attempts.push({
      hypothesis: diagnosis.rootCause,
      outcome: result.ok ? 'fixed' : 'still failing',
    })
  }

  // Skip logging entirely when nothing actually failed (clean first-try
  // success, zero attempts) -- there is no incident to record, and this was
  // previously firing an agent call unconditionally after every phase.
  // Also skip it for an infrastructure-wall failure -- that call would fail
  // identically, for the same reason the retries above were skipped.
  if (attempts.length > 0 && !isInfrastructureFailure(result.error)) {
    // Inlined ISSUES.md template instead of "read the whole knowledge-manager
    // skill" -- this is a narrow, mechanical, high-frequency structured write.
    await agent(buildIssueEntryPrompt(repoPathForIssue, phaseName, result, attempts), { label: `log-issue:${phaseName}`, phase: 'Implement', ...CHEAP })
  }

  if (!result.ok) {
    return { state: 'Blocked', ok: false, phase: phaseName, attempts }
  }
  return { state: 'Continue', ok: true, ...result }
}

// Set once, before any withRecovery call, so buildIssueEntryPrompt can
// reference the repo path without threading it through every call site.
let repoPathForIssue = null

function repeatsPriorHypothesis(diagnosis, attempts) {
  const current = String((diagnosis && diagnosis.rootCause) || diagnosis || '').trim().toLowerCase()
  return attempts.some((a) => String(a.hypothesis || '').trim().toLowerCase() === current)
}

function buildDiagnosePrompt(phaseName, error, attempts) {
  const priorList = attempts.length
    ? attempts.map((a, i) => `${i + 1}. hypothesis="${a.hypothesis}" -> ${a.outcome}`).join('\n')
    : '(none yet)'
  return [
    `Phase: ${phaseName}`,
    `Failing output (trimmed):\n${String(error).slice(0, 4000)}`,
    `Prior attempts this incident:\n${priorList}`,
    `Diagnose the root cause. Do not repeat a hypothesis already listed above as falsified.`,
    `Return: rootCause (one line), fix (concrete, scoped to specific files), files (list).`,
  ].join('\n\n')
}

function buildApplyPrompt(diagnosis) {
  return [
    `Apply exactly this fix, scoped only to the files it names -- do not touch anything else:`,
    JSON.stringify(diagnosis, null, 2),
  ].join('\n\n')
}

// So HANDOFF.md is always a current, accurate snapshot -- not just after PRD/
// Architecture -- and the existing SessionStart hook (which already surfaces
// HANDOFF.md's latest content automatically) has something fresh to show without
// needing a new hook of its own. Inlined field format, cheap model, low effort --
// this is a one-line mechanical edit, not a task that needs the full
// knowledge-manager skill loaded.
const PHASE_SEQUENCE = ['Intake', 'PRD', 'Architecture', 'Scaffold', 'Implement', 'Pre-deploy Gate', 'QA', 'Deploy', 'Handoff']

async function reportProgress(repoPath, phaseName, note, extra) {
  const idx = PHASE_SEQUENCE.indexOf(phaseName)
  const position = idx >= 0 ? `Phase ${idx + 1}/${PHASE_SEQUENCE.length}` : phaseName
  const extraLine = extra ? `\n\nAlso: ${extra}` : ''
  await agent(
    `At repo ${repoPath}, overwrite HANDOFF.md's "## Current Work" section (just that section, leave the rest of the file untouched) to read exactly: "Progress: ${position} (${phaseName}) complete -- ${note}".${extraLine}`,
    { label: `progress:${phaseName}`, ...CHEAP }
  )
}

function buildIssueEntryPrompt(repoPath, phaseName, result, attempts) {
  const status = result.ok ? 'Resolved' : attempts.length ? 'Escalated' : 'Abandoned'
  const attemptLines = attempts.map((a, i) => `  - ${i + 1}. ${a.hypothesis} -> ${a.outcome}`).join('\n')
  return [
    `At repo ${repoPath}, append exactly one entry to the TOP of ISSUES.md (create it with just a "# Issues" heading first if it doesn't exist yet) in this exact format -- one entry for the whole incident, not one per attempt:`,
    '',
    '```',
    `## <today's date/time, format YYYY-MM-DD HH:MM> -- ${phaseName}`,
    `- **Phase/Context**: ${phaseName}`,
    `- **Symptom**: <one line, from the failing output>`,
    `- **Diagnosis**: <one line, or "unresolved">`,
    `- **Attempts**:`,
    attemptLines || '  - (none -- failed before any recovery attempt)',
    `- **Fix**: <what resolved it, or "none -- escalated">`,
    `- **Status**: ${status}`,
    '```',
  ].join('\n')
}

phase('Intake')
// Defensive: args can arrive as a JSON string instead of a parsed object
// depending on how the caller passed it -- don't let a silent 'undefined'
// (e.g. brief.slug) propagate into a directory name, as happened once already.
const brief = typeof args === 'string' ? JSON.parse(args) : args
if (!brief || !brief.slug) {
  throw new Error(`build-mvp.js: args did not resolve to an object with a 'slug' field (got: ${JSON.stringify(args)}) -- aborting before creating anything.`)
}
const workspace = await agent(
  `Using the Bash tool specifically (not PowerShell -- this uses POSIX mkdir -p and && chaining, which PowerShell 5.1 doesn't support): create a fresh, isolated workspace for an autonomous MVP build: mkdir -p ~/mvp-builds/${brief.slug} && cd ~/mvp-builds/${brief.slug} && git init. Then, best-effort and non-blocking (don't fail this step if it doesn't work): run 'code <path>' to open the new folder in VS Code, so this new, unrelated project visibly gets its own editor window separate from whatever repo the current session started in. Return { ok, path, error, editorOpened } with path as an absolute path (resolve '~' before returning it -- don't return the literal tilde). 'ok' reflects only the mkdir/git init outcome -- editorOpened failing never fails this step.`,
  { label: 'workspace-setup', schema: WORKSPACE_SCHEMA, ...CHEAP }
)
if (!workspace || !workspace.ok) {
  // Abort: this is the one foundational step with nothing to route around.
  throw new Error(`build-mvp.js: workspace setup failed -- aborting before any phase that depends on it. ${workspace && workspace.error}`)
}
const repoPath = workspace.path
repoPathForIssue = repoPath

phase('PRD')
const prd = await agent(
  skillPrompt('prd', `Goal/objectives/deliverables/constraints:\n${JSON.stringify(brief, null, 2)}\n\nProduce the PRD, MVP-cut feature list, and acceptance criteria.`),
  { label: 'requirements-analyst', schema: PRD_SCHEMA }
)
if (!prd || !prd.features) {
  throw new Error(`build-mvp.js: requirements-analyst failed to produce a PRD -- aborting before any phase that depends on it.`)
}
const inScopeFeatures = prd.features.filter((f) => !f.cutForV1)
await reportProgress(
  repoPath, 'PRD',
  `${prd.features.length} features specified (${prd.features.length - inScopeFeatures.length} cut for v1)`,
  `record the full feature list with acceptance criteria into TASK.md's Active entry (Output field).`
)

phase('Architecture')
let stack
if (brief.complexity === 'trivial') {
  // Workflow auto-scaling: a trivial goal skips the full architecture debate.
  stack = {
    architecturePattern: 'single static page',
    summary: 'Fixed minimal default for a trivial build (mvp-builder Intake classified this goal as trivial).',
    host: 'vercel',
  }
} else {
  // Trimmed payload: only the in-scope features (name + acceptance criteria),
  // not the full PRD with all cut-for-v1 items' descriptions -- stack-selector
  // doesn't need the cut list to pick a stack.
  const prdForStack = { goal: prd.goal, features: inScopeFeatures.map((f) => ({ name: f.name, acceptanceCriteria: f.acceptanceCriteria })) }
  stack = await agent(
    skillPrompt('architecture', `PRD (in-scope features only):\n${JSON.stringify(prdForStack, null, 2)}\n\nAt repo ${repoPath}, pick the architecture pattern and concrete free-tier stack per the Tie-Break Order, and write the ADR to decisions/.`),
    { label: 'stack-selector', schema: STACK_SCHEMA, effort: 'high' }
  )
  if (!stack || !stack.summary) {
    throw new Error(`build-mvp.js: stack-selector failed to produce a decision -- aborting before any phase that depends on it.`)
  }
}
await reportProgress(repoPath, 'Architecture', stack.summary)

phase('Scaffold')
const scaffoldResult = await withRecovery(
  'Scaffold',
  () => agent(
    skillPrompt('conventions', `At repo ${repoPath}, using stack: ${JSON.stringify(stack)}, scaffold the project files and establish (or, if any exist, detect) formatting/lint/test-framework/naming/commit conventions, writing them into CLAUDE.md's Detected stack section. Defer to stack-selector's ADR rather than re-deriving the stack. Return { ok, error }.`),
    { label: 'repo-onboarding', schema: OK_ERROR_SCHEMA, ...CHEAP }
  ),
  () => agent(`At repo ${repoPath}, verify the scaffold has a valid entry point and builds with no errors. Return { ok, error }.`, { label: 'verify-scaffold', schema: OK_ERROR_SCHEMA, ...CHEAP })
)
if (scaffoldResult.state === 'Blocked') {
  await agent(
    `At repo ${repoPath}, write HANDOFF.md stating plainly: build did not complete -- Scaffold phase failed irrecoverably. Attempts: ${JSON.stringify(scaffoldResult.attempts)}.`,
    { label: 'abort-handoff', ...CHEAP }
  )
  return { state: 'Abort', phase: 'Scaffold', repoPath }
}
await reportProgress(repoPath, 'Scaffold', 'project files + conventions in place, ready for implementation')

phase('Implement')
if (budget.total && budget.remaining() < 50000) {
  log(`Token budget nearly exhausted (${Math.round(budget.remaining() / 1000)}k remaining) before Implement -- proceeding, may hit blockers sooner than a full run would.`)
}
const features = inScopeFeatures

function implementOneFeature(feature) {
  return withRecovery(
    `Implement:${feature.name}`,
    async () => {
      await agent(
        `At repo ${repoPath}, implement feature "${feature.name}" (acceptance criteria: ${JSON.stringify(feature.acceptanceCriteria)}). Grep for an existing implementation before creating a new one. If this touches a schema, produce migration + verify + rollback/down-migration (or an explicit one-line note why none is possible) as one unit.`,
        { label: `implement:${feature.name}`, phase: 'Implement', isolation: 'worktree' }
      )
      // Merged review + quality-sweep into one call (was two full subagent
      // dispatches per feature) -- code-review's own Maintainability dimension
      // already cites no-slop-check's checklist.md, so one reviewer applying
      // both is the same standard, one context load instead of two.
      const review = normalizeResult(await agent(
        skillPrompt('review', `At repo ${repoPath}, review the diff for feature "${feature.name}" against its acceptance criteria (${JSON.stringify(feature.acceptanceCriteria)}), stack-selector's ADR (architecture-drift check), and no-slop-check's checklist.md categories (dead code/duplication/naming/comments/consistency) on the files this feature touched. Return { pass, findings }.`),
        { label: `review:${feature.name}`, phase: 'Implement', schema: PASS_FINDINGS_SCHEMA }
      ), `Implement:${feature.name}:review`)
      return { ok: Boolean(review.pass), error: review.findings }
    },
    () => agent(`At repo ${repoPath}, re-run the existing test/build command relevant to feature "${feature.name}". Return { ok, error }.`, { label: `verify:${feature.name}`, phase: 'Implement', schema: OK_ERROR_SCHEMA, ...CHEAP })
  )
}

// Chunked, small sequential batches instead of one pipeline() over every
// feature at once -- pipeline()'s own concurrency cap isn't something this
// script can lower directly, and a large burst of simultaneous calls is
// exactly what re-hits a session/rate-limit wall the instant it resets,
// before that burst can even finish. BATCH_SIZE trades wall-clock time for
// a much smaller burst footprint -- raise it if the account's limits allow.
const IMPLEMENT_BATCH_SIZE = 2
const implementResults = []
for (let i = 0; i < features.length; i += IMPLEMENT_BATCH_SIZE) {
  const batch = features.slice(i, i + IMPLEMENT_BATCH_SIZE)
  const batchResults = await parallel(batch.map((feature) => () => implementOneFeature(feature)))
  implementResults.push(...batchResults)
}
const implementedCount = implementResults.filter((r) => r && r.state === 'Continue').length
await reportProgress(repoPath, 'Implement', `${implementedCount}/${features.length} features implemented and passed review`)

phase('Pre-deploy Gate')
const gate = normalizeResult(await agent(
  skillPrompt('review', `At repo ${repoPath}, review the WHOLE assembled repo (not one feature's diff) against: the original PRD/acceptance criteria (requirements-fit), stack-selector's ADR (architecture drift -- if found, write a new decisions/ entry via knowledge-manager), a Breaking/Potentially-Breaking/Non-breaking classification, security (secrets/authz/input validation/dependency vulnerabilities), and .env.example completeness against keys actually referenced in code. Return { pass, findings }.`),
  { label: 'pre-deploy-gate', effort: 'high', schema: PASS_FINDINGS_SCHEMA }
), 'Pre-deploy Gate')
if (!gate.pass) {
  const gateFix = await withRecovery(
    'Pre-deploy Gate',
    () => agent(`Fix the following pre-deploy gate findings at ${repoPath}: ${JSON.stringify(gate.findings)}. Return { ok, error }.`, { label: 'fix-gate-findings', schema: OK_ERROR_SCHEMA, ...CHEAP }),
    () => agent(skillPrompt('review', `Re-run the pre-deploy gate at ${repoPath}. Return { ok, error }.`), { label: 'reverify-gate', schema: OK_ERROR_SCHEMA })
  )
  if (gateFix.state === 'Blocked') {
    await agent(
      `At repo ${repoPath}, log a blocker under HANDOFF.md's "### Autonomous Run Blockers": pre-deploy gate could not be satisfied. Attempts: ${JSON.stringify(gateFix.attempts)}.`,
      { label: 'blocker:gate', ...CHEAP }
    )
  }
}
await reportProgress(repoPath, 'Pre-deploy Gate', gate.pass ? 'passed on first pass' : 'passed after fix-and-reverify')

phase('QA')
// Trimmed payload here too: in-scope features only.
const qa = await withRecovery(
  'QA',
  () => agent(
    `At repo ${repoPath}, verify EVERY acceptance criterion in the PRD against the running build (not a generic smoke test): ${JSON.stringify(inScopeFeatures)}. Use the Playwright MCP if available for UI criteria, direct calls for backend criteria. Return { ok, error, results }.`,
    { label: 'qa-acceptance', phase: 'QA', schema: OK_ERROR_RESULTS_SCHEMA }
  ),
  () => agent(`At repo ${repoPath}, re-run the same acceptance-criteria verification. Return { ok, error }.`, { label: 'reverify-qa', phase: 'QA', schema: OK_ERROR_SCHEMA, ...CHEAP })
)
await reportProgress(repoPath, 'QA', qa.ok ? 'all acceptance criteria verified' : 'acceptance verification incomplete -- see Autonomous Run Blockers')

phase('Deploy')
const deploy = await withRecovery(
  'Deploy',
  () => agent(
    skillPrompt('deployment', `At repo ${repoPath}, using stack: ${JSON.stringify(stack)}, deploy to the chosen free-tier host: provision generatable secrets, treat any missing must-supply third-party key as a blocker (never invent one), provision a /health endpoint and basic logging, deploy, and verify the live URL against the PRD's acceptance criteria. Return { ok, error, url }.`),
    { label: 'deployment-pilot', phase: 'Deploy', schema: OK_ERROR_URL_SCHEMA }
  ),
  () => agent(`Check the deployed /health endpoint at the last reported URL. Return { ok, error, url }.`, { label: 'verify-deploy', phase: 'Deploy', schema: OK_ERROR_URL_SCHEMA, ...CHEAP })
)
await reportProgress(repoPath, 'Deploy', deploy.ok ? `live at ${deploy.url}` : 'deploy did not complete -- see Autonomous Run Blockers')

phase('Handoff')
const handoff = await agent(
  skillPrompt(
    'knowledge-update',
    `At repo ${repoPath}, write the final HANDOFF.md/LOG.md/MEMORY.md: what was built vs. cut (${JSON.stringify(prd.features)}), the live URL and repo URL if Deploy succeeded (${JSON.stringify(deploy)}), and every blocker logged during this run grouped under "### Autonomous Run Blockers". State explicitly whether $0 was spent, or exactly where it wasn't.`
  ),
  { label: 'knowledge-manager' }
)

return { state: 'Done', repoPath, prd, stack, implementResults, qa, deploy, handoff }
