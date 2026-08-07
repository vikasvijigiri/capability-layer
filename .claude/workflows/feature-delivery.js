// Bounded, resumable feature-delivery state machine. The host owns side effects;
// this workflow owns order, evidence, recovery budgets, and the two gates.

export const meta = {
  name: 'feature-delivery',
  description: 'Plan, implement, diagnose, verify, integrate, and release one bounded change',
}

const BUDGETS = Object.freeze({ transient: 2, repair: 3, reentry: 2, conflict: 2, rollback: 1 })

export async function run({ args: workflowArgs = {}, agent, pipeline }) {
  const input = workflowArgs ?? {}
  const task = input.task ?? input.request
  const scope = input.scope ?? 'the repository'
  const acceptance = input.acceptance ?? 'All stated acceptance criteria pass.'
  const planApproved = input.planApproved === true
  const releaseApproved = input.releaseApproved === true
  const shipmentApproved = input.shipmentApproved === true || releaseApproved
  const incidents = []
  const transitions = []
  const json = value => JSON.stringify(value ?? null)
  const complete = value => value !== null && value !== undefined
  const completed = complete
  const move = (from, to, reason) => transitions.push({ from, to, reason })
  const incident = (stage, category, symptom, evidence, attempt, maxAttempts) => ({ id: `${stage}-${incidents.length + 1}`, stage, category, symptom, evidence, attempt, maxAttempts, rootCause: null, repair: null, verification: null, status: 'open' })

  async function recover(stage, failure, context) {
    const max = BUDGETS[failure.category] ?? BUDGETS.repair
    let current = failure
    for (let attempt = 1; attempt <= max; attempt += 1) {
      current.attempt = attempt
      incidents.push({ ...current })
      const diagnosis = await agent(`Use .claude/skills/systematic-debugging/SKILL.md. Diagnose this failure from evidence, name one falsifiable root cause, and classify it. Do not guess or silently broaden scope. Return JSON only. Failure: ${json(current)} Context: ${json(context)}`, { label: 'diagnose', schema: { type: 'object', required: ['category', 'rootCause', 'evidence', 'action'], properties: { category: { type: 'string' }, rootCause: { type: 'string' }, evidence: { type: 'array', items: { type: 'string' } }, action: { type: 'string' } } } })
      if (!complete(diagnosis)) return { status: 'blocked', reason: 'Diagnosis did not complete.' }
      current = { ...current, category: diagnosis.category, rootCause: diagnosis.rootCause, evidence: diagnosis.evidence }
      if (['security', 'specification-mismatch', 'scope-escape'].includes(diagnosis.category)) {
        current.status = diagnosis.category === 'security' ? 'blocked' : 'needs-plan-approval'
        incidents[incidents.length - 1] = { ...current }
        return { status: current.status, incident: current }
      }
      const repair = await agent(`Use .claude/skills/executing-plans/SKILL.md. Apply only the diagnosed, bounded repair for the current failure. Return changed files, command evidence, and whether complete. Diagnosis: ${json(diagnosis)} Context: ${json(context)}`, { label: 'repair', schema: { type: 'object', required: ['complete', 'changedFiles', 'evidence'], properties: { complete: { type: 'boolean' }, changedFiles: { type: 'array', items: { type: 'string' } }, evidence: { type: 'array', items: { type: 'string' } } } } })
      current = { ...current, repair, status: repair?.complete ? 'repair-applied' : 'open' }
      incidents[incidents.length - 1] = { ...current }
      if (!repair?.complete) continue
      const verification = await agent(`Use .claude/skills/verifying-work/SKILL.md. Re-run only the failed stage's proof against the actual tree. Return pass/fail and evidence. Failure: ${json(current)} Context: ${json(context)}`, { label: 'reverify', schema: { type: 'object', required: ['passed', 'evidence'], properties: { passed: { type: 'boolean' }, evidence: { type: 'array', items: { type: 'string' } }, findings: { type: 'array', items: { type: 'string' } } } } })
      current = { ...current, verification, status: verification?.passed ? 'resolved' : 'open' }
      incidents[incidents.length - 1] = { ...current }
      if (verification?.passed) return { status: 'resolved', incident: current }
    }
    current.status = 'blocked'
    incidents[incidents.length - 1] = { ...current }
    return { status: 'blocked', incident: current }
  }
  const fail = (stage, category, symptom, evidence) => recover(stage, incident(stage, category, symptom, evidence, 0, BUDGETS[category] ?? BUDGETS.repair), { task, scope, acceptance })

  if (!task) return { status: 'invalid-input', message: 'Provide args.task (or args.request), scope, and acceptance.' }
  move('START', 'DISCOVERING', 'bounded task received')
  const brief = await agent(`Read .claude/skills/task-brief/SKILL.md. Frame exactly one bounded task. Do not edit files. Task: ${task} Scope: ${scope} Acceptance: ${acceptance}`, { label: 'frame', schema: { type: 'object', required: ['goal', 'constraints', 'doneCheck', 'outOfScope'], properties: { goal: { type: 'string' }, constraints: { type: 'array', items: { type: 'string' } }, doneCheck: { type: 'array', items: { type: 'string' } }, outOfScope: { type: 'array', items: { type: 'string' } } } } })
  if (!complete(brief)) return { status: 'blocked', stage: 'frame', reason: 'Task framing did not complete.', transitions }
  move('DISCOVERING', 'PLANNING', 'brief complete')
  const plan = await agent(`Read .claude/skills/writing-plans/SKILL.md. Produce an implementation plan only; do not edit. Include ordered steps, affected paths, validation, risks, rollback, and file ownership. Brief: ${json(brief)} Task: ${task}`, { label: 'plan', schema: { type: 'object', required: ['steps', 'validation', 'risks', 'rollback'], properties: { steps: { type: 'array', items: { type: 'string' } }, validation: { type: 'array', items: { type: 'string' } }, risks: { type: 'array', items: { type: 'string' } }, rollback: { type: 'string' }, ownership: { type: 'array', items: { type: 'string' } } } } })
  if (!complete(plan)) return { status: 'blocked', stage: 'plan', reason: 'Planning did not complete.', brief, transitions }
  if (!planApproved) return { status: 'awaiting-plan-approval', gate: 'plan', brief, plan, incidents, transitions, next: 'Review the plan, then rerun with --plan-approved.' }

  move('WAITING_PLAN_APPROVAL', 'IMPLEMENTING', 'Gate 1 approved')
  const implementation = await agent(`Read .claude/agents/task-implementer.md and .claude/skills/executing-plans/SKILL.md. Implement only the approved plan in the declared scope. Do not push, merge, deploy, or commit. Return changed files, tests, risks, incomplete work. Plan: ${json(plan)}`, { label: 'implement', schema: { type: 'object', required: ['changedFiles', 'testsRun', 'incomplete'], properties: { changedFiles: { type: 'array', items: { type: 'string' } }, testsRun: { type: 'array', items: { type: 'string' } }, risks: { type: 'array', items: { type: 'string' } }, incomplete: { type: 'array', items: { type: 'string' } } } } })
  if (!complete(implementation)) return { status: 'blocked', stage: 'implement', reason: 'Implementation did not complete.', plan, transitions }
  move('IMPLEMENTING', 'VERIFYING', 'implementation report received')
  // at most two concurrent review agents. This workflow must never push, merge, deploy, or commit.
  const reviewers = [['verification', '.claude/skills/verifying-work/SKILL.md'], ['security', '.claude/skills/code-review/references/security-review.md']]
  let reviews = await pipeline(reviewers, ([label, reference]) => agent(`Perform an independent ${label} review. Read ${reference}. Inspect the actual changed tree and acceptance criteria. Do not edit. Return pass/fail, findings with paths and lines, and evidence. Acceptance: ${acceptance} Implementation: ${json(implementation)}`, { label, schema: { type: 'object', required: ['passed', 'findings', 'missingEvidence'], properties: { passed: { type: 'boolean' }, findings: { type: 'array', items: { type: 'string' } }, missingEvidence: { type: 'array', items: { type: 'string' } } } } }))
  const usableReviews = reviews.filter(completed)
  if (usableReviews.length !== reviewers.length) return { status: 'blocked', stage: 'verify', reason: 'Required review did not complete.', reviews, incidents, transitions }
  if (reviews.some(review => review.passed === false)) {
    const recovery = await fail('verify', 'repair', 'verification or security review failed', reviews)
    if (recovery.status !== 'resolved') return { ...recovery, reviews, incidents, transitions }
    reviews = await pipeline(reviewers, ([label, reference]) => agent(`Re-run the ${label} review after bounded repair. Read ${reference}. Inspect the actual tree. Return pass/fail, findings, missingEvidence.`, { label, schema: { type: 'object', required: ['passed', 'findings', 'missingEvidence'], properties: { passed: { type: 'boolean' }, findings: { type: 'array', items: { type: 'string' } }, missingEvidence: { type: 'array', items: { type: 'string' } } } } }))
  }
  if (reviews.some(review => review.passed === false)) return { status: 'blocked', stage: 'verify', reason: 'Review remains red after bounded recovery.', reviews, incidents, transitions }
  move('VERIFYING', 'REVIEWING', 'verification and security passed')
  const review = await agent(`Read the actual branch diff and .claude/skills/code-review/SKILL.md. Produce a machine-verifiable review only; do not edit. Return passed, findings with file:line, scope verdict, and evidence.`, { label: 'review', schema: { type: 'object', required: ['passed', 'findings', 'evidence'], properties: { passed: { type: 'boolean' }, findings: { type: 'array', items: { type: 'string' } }, evidence: { type: 'array', items: { type: 'string' } }, scopeVerdict: { type: 'string' } } } })
  if (!review?.passed) {
    const recovery = await fail('review', 'repair', 'automated code review found blocking findings', review)
    if (recovery.status !== 'resolved') return { ...recovery, review, incidents, transitions }
  }
  move('REVIEWING', 'PR_READY', 'review passed')
  const integration = await agent(`Read .claude/skills/delivering/SKILL.md. Prepare a PR/merge-queue handoff without pushing or merging. Detect conflicts and return clean, conflict, or blocked with files and evidence.`, { label: 'integration', schema: { type: 'object', required: ['status', 'evidence'], properties: { status: { type: 'string' }, conflictFiles: { type: 'array', items: { type: 'string' } }, evidence: { type: 'array', items: { type: 'string' } } } } })
  if (integration?.status === 'conflict') {
    const recovery = await fail('integration', 'conflict', 'merge conflict detected', integration)
    if (recovery.status !== 'resolved') return { ...recovery, integration, incidents, transitions }
  }
  if (integration?.status === 'blocked') return { status: 'blocked', stage: 'integration', integration, incidents, transitions }
  const release = await agent(`Read .claude/agents/release-verifier.md and .claude/skills/releasing/SKILL.md. Assess release readiness from implementation, reviews, and integration. Do not release. Require passing checks, no unresolved security findings, rollback, smoke evidence, and observability.`, { label: 'release-readiness', schema: { type: 'object', required: ['ready', 'blockingFindings', 'rollback'], properties: { ready: { type: 'boolean' }, blockingFindings: { type: 'array', items: { type: 'string' } }, rollback: { type: 'string' }, smoke: { type: 'array', items: { type: 'string' } } } } })
  if (!release?.ready) return { status: 'blocked', stage: 'release-readiness', release, implementation, reviews, review, integration, incidents, transitions }
  if (!shipmentApproved) return { status: 'awaiting-ship-approval', gate: 'shipment', implementation, reviews, review, integration, release, incidents, transitions, next: 'Review the release candidate, then rerun with --release-approved.' }
  move('WAITING_SHIP_APPROVAL', 'RELEASING', 'Gate 2 approved')
  const outcome = await agent(`Read .claude/skills/releasing/SKILL.md. Execute the approved release through the host, observe the target, and verify the smoke check. If it fails, rollback once, diagnose, and report. Return deployed, rolledBack, stable, evidence, and rollback.`, { label: 'release', schema: { type: 'object', required: ['deployed', 'stable', 'evidence'], properties: { deployed: { type: 'boolean' }, rolledBack: { type: 'boolean' }, stable: { type: 'boolean' }, evidence: { type: 'array', items: { type: 'string' } }, rollback: { type: 'string' } } } })
  if (!outcome?.stable) return { status: 'blocked', stage: 'observe', outcome, incidents, transitions, note: 'Release is not successful until observation or rollback is stable.' }
  move('RELEASING', 'RECORDING', 'release observed stable')
  return { status: 'ready', implementation, reviews, review, integration, release, outcome, incidents, transitions, budgets: BUDGETS, note: 'Only plan approval and shipment approval are human gates; all recovery loops are bounded and evidenced.' }
}
