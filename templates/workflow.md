# Dynamic Workflow — Skeleton & Request Template

Unlike a skill or subagent, you don't usually hand-author the whole script —
Claude writes it from a description of the task, you approve the plan, it
runs in the background, and if it's worth repeating you save it as `/name`.
This doc gives you both halves: the request template that produces a good
script, and the annotated shape of the script itself so you can read/edit
what Claude generates instead of treating it as a black box.

---

## Part 1 — The request template (this is what you actually type)

```text
use a workflow to <TASK>:
  - discover: <how to find the set of items to process>
  - per item: <what each agent should do to one item>
  - verify: <how findings get cross-checked before being trusted, if at all>
  - combine: <how per-item results become one final answer>
  - stop when: <the termination condition, for open-ended/looping tasks>
```

Fill in only the lines that apply — most tasks don't need all five. Five
real examples, each a different shape:

```text
# Fan-out / fan-in over a fixed file set, with adversarial verification
use a workflow to audit every route handler under src/routes/ for missing
auth checks, and adversarially verify each finding before reporting it

# Loop-until-passes
use a workflow to run npx tsc --noEmit and keep fixing the reported errors
until the type check passes or two rounds in a row make no progress

# Parallel migration with isolation
use a workflow to migrate every component under src/components/ from
styled-components to Tailwind, working on each file in its own isolated copy

# Per-item review, single merged output
use a workflow to review every file changed in this PR for correctness
issues, then merge the per-file findings into one ranked summary

# Open-ended search with a stopping condition
use a workflow to find flaky tests in this repo: run the suite repeatedly,
record intermittent failures, and stop once two rounds in a row find nothing new
```

To make Claude plan a workflow automatically for every substantial task in
the session (not just when you ask), set `/effort ultracode` instead.

---

## Part 2 — The script shape (what Claude generates / what you read & edit)

```javascript
// ═══════════════════════════════════════════════════════════════
// Saved to: .claude/workflows/<name>.js   (project — commit it, shared)
//      or:  ~/.claude/workflows/<name>.js (personal — this machine only)
// Runs as: /<name>  once saved. Plugin-distributed workflows are saved
// under <plugin>/workflows/ and run as /<plugin>:<name>.
// ═══════════════════════════════════════════════════════════════

export const meta = {
  name: 'audit-routes',                 // becomes the /name you invoke
  description: 'Audit every route handler for missing auth checks',
}

// ── Optional input, passed at invocation time ──────────────────
// e.g. "Run /audit-routes on src/routes/admin" → args = { path: "src/routes/admin" }
// Undefined if the caller passes nothing — always guard for that.
const targetPath = args?.path ?? 'src/routes/'

// ── STAGE 1: Discover ───────────────────────────────────────────
// One agent() call = one subagent spawn. Give it a `schema` so the
// result comes back as structured data you can use directly in code,
// not prose you have to re-parse.
const found = await agent(
  `List every .ts file under ${targetPath}.`,
  {
    schema: {
      type: 'object',
      required: ['files'],
      properties: { files: { type: 'array', items: { type: 'string' } } },
    },
  },
)

// ── STAGE 2: Fan out — one agent per item ───────────────────────
// pipeline(list, fn) spawns one agent per element, respecting the
// runtime's concurrency cap (16 concurrent, 1000 total per run).
// `label` is what shows up per-agent in the /workflows progress view.
const audits = await pipeline(found.files, file =>
  agent(`Audit ${file} for missing authentication checks. Report file,
         line, and the specific missing check, or "clean" if none found.`,
    { label: file },
  ),
)

// agent() resolves to null if that agent was stopped mid-run or hit an
// unrecoverable API error — pipeline() keeps the null in place, so
// always filter before using results downstream.
const findings = audits.filter(Boolean).filter(a => a.result !== 'clean')

// ── STAGE 3: Verify (adversarial cross-check) ───────────────────
// This is the pattern a workflow earns its keep on: an independent
// second agent per finding, with NO knowledge of how the first agent
// reasoned, checking it from scratch.
const verified = await pipeline(findings, finding =>
  agent(`Independently verify this claimed missing-auth-check finding by
         re-reading the file yourself: ${JSON.stringify(finding)}.
         Confirm or refute with your own reasoning.`,
    { label: `verify:${finding.file}` },
  ),
)

const confirmed = verified.filter(Boolean).filter(v => v.confirmed)

// ── STAGE 4: Combine — one synthesis agent over everything ──────
// Keep this LAST stage as a single agent so the final output Claude's
// context receives is one coherent report, not N raw findings.
const report = await agent(
  `Write one ranked report from these confirmed findings, most severe
   first: ${JSON.stringify(confirmed)}`,
)

return report
```

### The two primitives, fully

| Call | Signature | Notes |
|---|---|---|
| `agent(prompt, options?)` | spawns **one** subagent | `options.schema` (JSON Schema) makes the return value structured data instead of prose. `options.label` names it in the progress view. Resolves to `null` on stop/unrecoverable error — always guard. |
| `pipeline(items, fn)` | spawns **one agent per item**, `fn` returns an `agent()` call | Runs under the runtime's concurrency cap. Returns an array, same order as input, with `null` for any item whose agent didn't finish. |

Everything else — loops, conditionals, `for`/`while`, retry counters, early
termination — is just plain JavaScript around those two calls. That's the
whole point of a workflow: the plan lives in ordinary code you can read,
not in a sequence of turns you have to infer from a transcript.

### Loop-until-condition pattern (for the "keep fixing until X passes" shape)

```javascript
let attempt = 0
let lastFailCount = Infinity

while (attempt < 5) {
  const check = await agent('Run npx tsc --noEmit and report the error list.',
    { schema: { type: 'object', properties: { errors: { type: 'array' } } } })

  if (check.errors.length === 0) break                    // passed — done
  if (check.errors.length >= lastFailCount) break          // stalled — stop

  lastFailCount = check.errors.length
  await pipeline(check.errors, err => agent(`Fix this type error: ${JSON.stringify(err)}`))
  attempt++
}
```

---

## Part 3 — Runtime limits to design around

| Constraint | Value |
|---|---|
| Concurrent agents per run | 16 (fewer on limited-CPU machines) |
| Total agents per run | 1,000 |
| Size guideline (advisory, set via `/config`) | `small` <5, `medium` <15 (default), `large` <50, `unrestricted` |
| Mid-run human input | Not possible — split into separate saved workflows if you need a sign-off between stages |
| Resume semantics | Only agents that finished *before* the first still-running agent at stop time are cached; everything after reruns, even if it had completed |

The resume rule is why **many small `pipeline()` items beat a few long
`agent()` calls** — a workflow that fans out wide preserves far more
progress if you have to stop and resume it.

## Where to verify
`https://code.claude.com/docs/en/workflows.md` · full Workflow-tool API: `https://code.claude.com/docs/en/agent-sdk/typescript.md`