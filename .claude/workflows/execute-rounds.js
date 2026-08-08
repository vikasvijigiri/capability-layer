export const meta = {
  name: 'execute-rounds',
  description: 'Execute an approved plan round by round, one task-implementer per task, concurrently within a round',
  whenToUse: 'After Gate 1, when tools/parallel_groups.py reports a schedulable plan with at least one round of concurrency. Pass its --json output as args.',
  phases: [
    { title: 'Round 1', detail: 'first dependency level — tasks with disjoint file sets' },
    { title: 'Round 2', detail: 'second level, once round 1 is verified' },
    { title: 'Round 3', detail: 'third level' },
    { title: 'Later rounds', detail: 'any level beyond the third' },
  ],
}

// Execute a plan's rounds. Dispatch is this script's job; DECIDING anything is
// not.
//
// Why this exists, and why it is shaped this way
// ----------------------------------------------
// `parallel_groups.py` computes which tasks may run together. Until now a skill
// told the model to "dispatch one task-implementer per task, all in the SAME
// message", and the first time that was tried all five agents landed in worktrees
// based on the initial commit rather than the working branch. Three returned
// BLOCKED, two wrote into stranded trees, and the round had to be salvaged by
// hand. The runtime owns concurrency here; a skill asking the model to remember
// to fan out does not.
//
// This repository deleted a previous JavaScript workflow on 2026-08-07
// (`decisions/2026-08-07-one-workflow-engine.md`) for four reasons. Three of them
// are designed out here rather than argued with:
//
//   1. "It could not be invoked" -- it exported `run({args, agent, pipeline})`
//      instead of top-level code, so it never matched the contract and never
//      appeared as a command. This file is `export const meta` plus top-level
//      code using the runtime globals, which IS the contract.
//   2. "A second budget table" -- it restated `_hooklib.FAILURE_BUDGETS` in a
//      different vocabulary, and a `deterministic` failure got the right number
//      of attempts by coincidence. This script contains NO budgets and NO ladder.
//      It reports statuses; `tools/loop.py --agent-status` decides the rung, in
//      the one place that table lives.
//   3. "Run state in memory" -- it held `transitions[]` that died with the
//      process. Nothing durable is kept here either, which is fine BECAUSE
//      nothing here is durable state: the plan's checkboxes and git are the
//      record, and `tools/resume.py` re-derives from them. Losing this run costs
//      time, not information. That is the test for whether work belongs in a
//      workflow at all.
//
// The fourth reason was that it was tested by a line count. `tools/test_workflow_contract.py`
// asserts the shape instead.
//
// No filesystem, no subprocess: a workflow script cannot read `docs/plans/` or
// shell out to Python. So the schedule is computed OUTSIDE and passed in, which
// is the hybrid the tool's own guidance recommends -- scout inline, then fan out.

const input = args || {}
const rounds = Array.isArray(input.rounds) ? input.rounds : []
const planPath = input.plan || ''

if (!planPath) {
  throw new Error(
    'args.plan is required: the repo-relative path to the approved plan. ' +
    'Agents are handed a path, never pasted text -- everything pasted into a ' +
    'dispatch stays in the dispatcher context for the rest of the session.')
}
if (rounds.length === 0) {
  throw new Error(
    'args.rounds is empty. Run `python tools/parallel_groups.py <plan> --json` ' +
    'and pass its `groups` array. An empty schedule means the plan was refused, ' +
    'and a refused plan is a plan to fix rather than one to execute.')
}

// What an implementer must return. Forced through a schema so the status is a
// known token rather than prose the caller has to interpret -- the ladder in
// `tools/loop.py` switches on exactly these.
const REPORT = {
  type: 'object',
  required: ['status', 'files', 'evidence'],
  properties: {
    status: {
      type: 'string',
      enum: ['DONE', 'DONE_WITH_CONCERNS', 'NEEDS_CONTEXT', 'BLOCKED'],
      description: 'DONE only when every verification was RUN and passed.',
    },
    files: {
      type: 'array', items: { type: 'string' },
      description: 'Paths created or modified. Empty is a finding, not a success.',
    },
    evidence: {
      type: 'string',
      description: 'The verification command and its REAL output. Not a summary.',
    },
    concerns: { type: 'string' },
    missing: {
      type: 'string',
      description: 'For NEEDS_CONTEXT: the one fact the brief lacked. Name it exactly.',
    },
  },
}

function brief(planPath, taskNumber, title, roundTasks, constraints) {
  const peers = roundTasks.filter((n) => n !== taskNumber)
  return [
    `Implement **Task ${taskNumber}** (${title}) from the approved plan at`,
    `\`${planPath}\`. Read that file and follow ONLY Task ${taskNumber}.`,
    '',
    'Your files are the ones Task ' + taskNumber + ' declares under `Files:`, and',
    'nothing else. That set was checked to be disjoint from every other task in',
    'this round, which is the only reason you may run concurrently with them.',
    peers.length
      ? `Task(s) ${peers.join(', ')} are running RIGHT NOW in their own worktrees.`
      : 'You are the only task in this round.',
    'A file you touch outside your declared set is a collision with an agent you',
    'cannot see. If your task genuinely needs an undeclared path, return',
    'NEEDS_CONTEXT and name it -- do not write it.',
    '',
    constraints,
    '',
    'Run your task\'s own Verification command and return its REAL output as',
    '`evidence`. Exit 0 is not proof the effect occurred: read the result back.',
    'Never return DONE on a verification you did not run.',
  ].join('\n')
}

const CONSTRAINTS = [
  'Global constraints:',
  '- Never commit, push, merge or deploy. The dispatcher owns integration.',
  '- Never weaken, skip or delete a test to get a green run. If a test is wrong,',
  '  say so and leave it failing.',
  '- Never change the plan. If it is wrong, return BLOCKED with the reason.',
  '- `PYTHONIOENCODING=utf-8` before any Python tool script in this repo, or the',
  '  Windows console default raises UnicodeEncodeError and a passing run reports',
  '  as a failure.',
  '- After editing any hook, fire it with `python tools/run_hook.py <event>` --',
  '  a hook bug\'s symptom is silence, identical to "no problem".',
].join('\n')

function phaseFor(index) {
  return index < 3 ? `Round ${index + 1}` : 'Later rounds'
}

const results = []

for (let i = 0; i < rounds.length; i++) {
  const round = rounds[i]
  const tasks = Array.isArray(round.tasks) ? round.tasks : []
  const titles = Array.isArray(round.titles) ? round.titles : []
  const label = phaseFor(i)
  phase(label)

  log(`round ${i + 1}/${rounds.length}: ${tasks.length} task(s)` +
      (round.serialized ? ` — SERIAL (${round.reason})` : '') +
      ` — ${tasks.join(', ')}`)

  // A barrier between rounds, and this is the case where one is correct: every
  // task in round N+1 declared a dependency on something in round N, so starting
  // it early would execute against an interface that does not exist yet. Inside a
  // round there is no ordering at all, which is what `parallel` expresses.
  const round_results = await parallel(tasks.map((number, position) => () =>
    agent(
      brief(planPath, number, titles[position] || `task ${number}`, tasks, CONSTRAINTS),
      {
        label: `task-${number}`,
        phase: label,
        agentType: 'task-implementer',
        isolation: 'worktree',
        schema: REPORT,
      },
    ).then((report) => ({ task: number, title: titles[position] || '', report }))
  ))

  const finished = round_results.filter(Boolean)
  const died = tasks.length - finished.length

  for (const entry of finished) {
    results.push({ round: i + 1, ...entry })
  }
  // A dispatch that returns null died before reporting -- a terminal API error or
  // a killed process. That is a distinct outcome from BLOCKED and the ladder has
  // a separate rung for it, so it is recorded rather than folded into a count.
  for (let k = 0; k < died; k++) {
    results.push({ round: i + 1, task: null, title: '', report: { status: 'DIED' } })
  }

  const bad = finished.filter((e) =>
    e.report && e.report.status !== 'DONE' && e.report.status !== 'DONE_WITH_CONCERNS')

  if (bad.length || died) {
    log(`round ${i + 1} did not fully land: ` +
        bad.map((e) => `task ${e.task}=${e.report.status}`).join(', ') +
        (died ? ` (${died} died)` : '') +
        ' — stopping. Later rounds depend on this one, and dispatching them now ' +
        'would build against work that is not there.')
    break
  }

  log(`round ${i + 1} reported complete — the DIFF is the evidence, not the report`)
}

// Returned, not acted on. The caller applies `python tools/loop.py --agent-status
// <STATUS> --attempt <n>` per unfinished task, because that is where the budgets
// live and duplicating them here is the mistake that got the last workflow deleted.
return {
  plan: planPath,
  rounds_scheduled: rounds.length,
  rounds_attempted: results.length ? results[results.length - 1].round : 0,
  results,
  next: 'For each non-DONE status run `python tools/loop.py --agent-status <STATUS>` ' +
        'for its rung. Read the diff before ticking any plan checkbox: an agent ' +
        'reporting DONE is a claim, and the diff is the evidence.',
}
