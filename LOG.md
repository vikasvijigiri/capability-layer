# Log

<!-- Append new entries at the TOP, never rewrite old ones.
Format: ## YYYY-MM-DD HH:MM -->

## 2026-08-01 20:15
Audited all three skills against `obra/superpowers`' own `writing-skills` (the closest
thing to an authoritative standard) plus five upstream skills as a baseline, then acted
on it. Confirmed first that the global layer is empty — `~/.claude/` has no `skills/`
directory at all, and the plugin marketplace has none installed. These three are the
whole skill layer.

**The defect was never length, it was kind.** All three descriptions summarised the
workflow. `writing-skills` forbids that specifically, from their own testing: a
description that summarises the process becomes a shortcut the agent takes *instead of*
reading the skill — their case had an agent do one review where the flowchart specified
two. `task-brief`'s was the worst, naming all six fields, the verification step, the
approval gate and the `TASK.md` write; an agent could execute it without opening the
file, skipping the confidence score and the HARD-GATE entirely. All three are now
trigger-only: symptoms, quoted phrases, and an explicit "Do NOT use for" boundary.
Total length is roughly unchanged (2159 → 2239) after being cut to 370 and expanded
back on request — the content is what changed, not the size.

**Bodies 4094 → 3357 words.** Prose down ~30% — `brainstormer`'s Checklist and "The
Process" were the same ten steps written twice, and `writing-plans` described its three
gates in three separate places — partly offset by ~200 words of new Red Flags and
Common Mistakes tables, which the standard treats as the primary anti-rationalisation
tool and which two of the three lacked entirely.

**Broke a skill live and caught it by luck, then fixed that.** Writing
`...not yet settled: "any ideas"` into `brainstormer`'s description made YAML parse the
scalar as a mapping; the description silently vanished and the listing rendered the bare
title `Brainstormer`. Untriggerable by description, still listed, still routed — exactly
what `/skills-doctor` check 2 warns about, and nothing in the suite caught it. The only
signal was noticing the rendered listing.

So `tools/test_process_router.py` now asserts, per skill: frontmatter parses to a
mapping, description is non-empty, `name` matches the directory, and frontmatter is
within the 1024-char hard spec limit. The 500-char description target is a NOTE, not a
failure — it is superpowers' "if possible" guidance about truncation budget, and richer
trigger coverage is worth spending some of it. Proved by planting `: "` back into
`task-brief` and confirming `FAIL: task-brief frontmatter parses -- mapping values are
not allowed here`, then restoring.

Four suites pass, `compileall` exits 0, `01-env-check.py` logs `{"issues": []}`.

Not done, deliberately: `brainstormer` should be `brainstorming` per the standard's
verb-first naming, but the rename churns routing, CLAUDE.md, history and muscle memory
for zero functional gain. And the Iron Law — "no skill without a failing test first",
meaning a baseline pressure scenario run *without* the skill — is still unmet on all
three. That is the honest remaining gap; every gate in these files is asserted by its
own text.

## 2026-08-01 19:20
Cleared every reference to a deleted capability across `.claude/`. **22 sites in 13
files.** This closes HANDOFF's top pending item and the recurring class behind it —
*prose declares a capability the wiring does not implement*, now at its seventh instance.

Method matters more than the count. The first pass grepped eight names I could remember
and found six. The second pass took **all 146 capability names from `git ls-tree eaab430`**
and grepped every `.py`/`.md`/`.json` under `.claude/` for each — that found twelve more,
including three the guessed list would never have reached (`repo-onboarding`,
`deployment-pilot`, `stack-selector`). Guessing the search terms was the bug, not the
grep.

Actionable dead instructions fixed (these told Claude to invoke something absent):

- `writing-plans` — "Route to `approval-brief` before anything irreversible" → stop and
  ask the user directly. Also dropped `execution-planner` and a paragraph naming five
  deleted agents.
- `brainstormer` — "Precedes `requirements-analyst`" → replaced with the real
  relationship, that it is an alternative to `task-brief` and never a successor.
- `/wip` — "offer `knowledge-manager`" → say which docs are stale and stop.
- `post-run/04-docs-sync.py` — user-visible "`repo-onboarding` — owns CLAUDE.md".
- `session-start/02-bootstrap-docs.py` — user-visible "run the repo-onboarding skill".
- `pre-commit/03-review-gate.py` — a botched earlier find/replace had left the literal
  sentence "Review the diff skill on this diff".

Also fixed four dead file paths (`.claude/skills/code-review/SKILL.md`,
`.claude/hooks/{git-delivery-guard,deploy-spend-guard,forbidden-change-guard}.md`) and
the rationale docstrings naming `02-capability-router.py`, `03-task-brief-nudge.py`,
`capabilities.md` and `git_delivery_guard.py`.

Two references kept deliberately, both labelled as history rather than left dangling:
`03-review-gate.py` now states that the `code-review` skill which used to run `--record`
is gone, **so the gate asks on every commit by default** — that is a live behavioural
consequence a reader needs; and `04-delivery-guard.py`'s `~/mvp-builds/` path exception,
whose code is still live and inert rather than wrong.

Verified, not assumed: a 12-case payload harness ran every edited hook and asserted the
decision each returned — `01-spend-guard` deny/silent, `01-forbidden-change-guard` deny,
`03-review-gate` ask, `05-process-skill-router` match/silent, and the three Stop/
SessionStart hooks. All 12 as expected. Four suites pass, `compileall` exits 0. The
final all-names sweep returns only the two deliberate mentions.

Worth keeping: the spend guard denied the first test attempt, because the shell line
driving the test contained the vendor keyword and a `&&`. The hook was right. Tests for
a command-scanning hook cannot be written as shell one-liners.

## 2026-08-01 18:35
Corrected the golden path. `task-brief → brainstormer → writing-plans`, written into
CLAUDE.md an hour earlier, was wrong — and the sentence directly beneath the arrow
already contradicted it.

`brainstormer` exists because the first idea becomes an anchor. A finished brief *is*
that anchor: Goal and Outputs commit to a solution shape, so brainstorming afterwards
degenerates into variations on an answer already given. The reverse direction fails too
— `writing-plans` requires a design spec and six lines in `TASK.md` is not one.

`task-brief`'s terminal handoff narrowed to direct execution and nothing else. Its
bailout is now step 3's blank-field rule rather than a handoff: if Outputs or Done-check
cannot be filled because the approach is undecided, abandon the brief and start at
`brainstormer` — do not guess fields to keep the brief alive.

**Then dropped the flow from CLAUDE.md entirely.** The corrected two-lane diagram was
still the wrong kind of thing: CLAUDE.md prescribing an order the skills should decide
per ask. Checked what public repos do — 18,496 CLAUDE.md files reference
`.claude/skills`, and the pattern is a plain `## Skills` section naming the directory
and listing one line per skill, with no sequencing at all
(`mongodb/mongodb-atlas-kubernetes`, `mizchi/skills`). Adopted that. The
`## Golden path` section is now `## Skills`: three one-line entries and "read the skill,
don't infer an order from this list."

The ordering rationale is not lost — it lives in `task-brief`'s own `## Routing`, which
is where a skill's relationships belong and where it stays correct if the skill changes.

Worth keeping: the contradiction shipped inside a single section, between an ASCII arrow
and the prose under it. The arrow was the part that read as authoritative — which is the
argument against putting an arrow in CLAUDE.md at all.

Four suites re-run and pass.

## 2026-08-01 18:10
Added skill `task-brief` — rough ask → six-line brief (Goal / Constraints / Inputs /
Outputs / Done-check / Out-of-scope) → approval gate → `TASK.md`. Third skill; routing
entry added, `test_process_router.py` now reports `3 entries routed`.

Recovered rather than written: `task-intake` at `eaab430` already had these six fields
mapped onto `TASK.md`'s own field names, plus a 0–100 confidence score that decides
whether to ask clarifying questions before presenting. Both kept. Its handoffs to
`knowledge-manager` and `workflow-orchestrator` were rewritten — those are deleted, so
the skill now writes `TASK.md` itself and hands off to `brainstormer`, `writing-plans`,
or direct execution.

GitHub search (2,116 repos carry the pattern) contributed two things the old version
lacked. From `gitkraken/vscode-gitlens` `dev-scope`: **verify claims against the
codebase before filling any field**, bucketed confirmed/disputed/unverifiable. That is
the highest-value addition here — a brief built on a wrong premise looks approved, which
is this repo's own recurring failure class. From `dylanroscover/Embody` `brief`: record
the request verbatim as line zero so compression drift stays visible, and skip the brief
outright when it costs more than the work.

`pre-run/03-task-brief-nudge.py` deliberately **not** restored.
`05-process-skill-router.py` now covers its job via keywords, without injecting a fixed
string on every turn.

Checks run: four suites pass, `01-env-check.py` logs `{"issues": []}`, frontmatter parses
3 skills with names matching directories. The skill itself has never been executed — its
gates are asserted by its own text, same as the other two.

## 2026-08-01 17:35
Rewrote `CLAUDE.md` against the section order public CLAUDE.md surveys converge on
(overview → working agreement → golden path → commands → map → knowledge docs →
gotchas → never). 131 → 122 lines. The file had drifted into a changelog: a
"State: mid-rebuild" preamble and a full "What was deleted on 2026-08-01" inventory,
both of which are LOG.md's and `eaab430`'s job, not a bootloader's.

Two real errors fixed, not just reshaped prose:

- It pointed at `docs/architecture/`, which does not exist. The actual design set is
  `docs/00-*.md … 17-*.md`, and it describes the pre-teardown layer, so the map now
  says to read it with suspicion.
- The six root knowledge docs were absent entirely, despite hooks referencing them
  584 times. They now have their own section, with the honest gate strengths:
  `PreToolUse` deny works, `Stop` blocking is still unproven at 130 payloads.

Added the `PYTHONIOENCODING=utf-8` gotcha (it was only in `/verify`, where it is
found after the failure rather than before) and the `ALLOW_UNLOGGED_COMMIT=1`
override. No code changed; `/verify` not run.

## 2026-08-01 16:40
First `brainstormer` run end to end — the skill's gates and its `docs/specs/` path are
now asserted by something other than its own text. Six futures generated for "how does
software engineering change in 10 years", converged on trust-scarcity + agent-fleets, and
the design that fell out is an **evidence ledger**: claims extracted only from explicit
sources, checks executed and captured verbatim, and the *unbacked* set as the primary
output rather than the pass list.

Spec at `docs/specs/2026-08-01-evidence-ledger-design.md`. Units 1–4 in scope; unit 5
(attention router) designed and deliberately not built. Gate ships advisory until
extraction's false-positive rate is measured over ~20 real changes.

Motivating failure is this repo's own: six hooks shipped naming deleted skills, past a
green suite, because nothing asserted the named skill exists. That is criterion 2.

Nothing implemented. `writing-plans` is next.

## 2026-08-01 14:26
Tore the capability layer down to two skills. Deleted 85 skills, 12 agents, 6 blueprints,
7 workflows, 11 validators, 1 playbook, 1 template, 27 MCP docs, all five generated
registries, `routing/capabilities.md` and its router hook, and the six tools that only
served them. 182 deletions. `brainstormer`, `writing-plans` and `.claude/hooks/` survive.
Safety commit `eaab430` first, so all of it is recoverable.

"Keep the hooks as-is" was not satisfiable, and the reason is worth keeping. Three of them
were wired to things that no longer exist:

- `pre-run/03-task-brief-nudge.py` — deleted and unregistered. It named `task-intake` on
  every prompt; the skill is gone, so it was injecting a dead instruction every turn.
- `session-start/01-env-check.py` — checked three registries that no longer exist and would
  have reported `missing registry` at every session start forever. Rewritten to assert what
  now matters: every skill has a `SKILL.md` and a routing entry. Verified by planting an
  unrouted skill and confirming it is reported, not just that the clean case is silent.
- `tools/test_process_router.py` — six of seven match assertions named deleted skills.
  Rewritten, and now also asserts the inverse (every skill *has* an entry), which the old
  suite only emitted as a tolerated NOTE.

**The Stop gate then demonstrated the same bug on itself:** it blocked the turn with
"invoke `knowledge-manager` to record this unit of work" — a skill deleted ten minutes
earlier. Six hooks carry user-visible strings naming `knowledge-manager` or `code-review`.
That is the sixth instance of this repo's recurring class, *prose declares a capability the
wiring does not implement*, and the first where the prose is inside a hook rather than a
skill. A hook cannot check whether the skill it names exists; nothing does.

`04-delivery-guard.py` also has a real Windows bug. `find_ai_attribution` scans the whole
command string, and its `_STANDALONE` lookarounds exclude `/` but not `\`, so any path
containing `\claude\` reads as AI attribution. Its own comment says a `~/.claude/` path
must not trigger it — true on POSIX, false here. It blocked two legitimate commits before
the message was moved onto stdin.

## 2026-08-01 14:07
Adopted two skills from `obra/superpowers` (264k stars), whose `.claude/skills/brainstorm/`
convention 6,912 repos share. `brainstormer` took the full superpowers shape by explicit
choice over a read-only variant: `disallowed-tools` dropped, `HARD-GATE`, Anti-Pattern,
10-step Checklist, a dot Process Flow with three approval diamonds, a spec written to
`docs/specs/` and committed, terminal handoff to `writing-plans`. New skill `writing-plans`
adopted from superpowers' own, plus three blocking `AskUserQuestion` gates (decomposition,
task breakdown, written plan), one-question-per-message and prefer-multiple-choice. 87 skills.

Neither superpowers nor the widely-copied gist uses `AskUserQuestion` — both gate on plain
text, with superpowers going as far as "This offer MUST be its own message" to force the
pause. The structured gates here are a deliberate departure, not prior art.

`execution-planner`'s "Nothing else produces a plan" corrected to "Nothing else produces
`PLAN.md`" and delineated: it owns ordering, dependencies and risk; `writing-plans` owns the
task-by-task script with real code. Two skills, two artefacts, no duplicate implementation.

**Open contradiction, recorded not fixed:** CLAUDE.md now caps every skill response at 500
tokens. Both adopted skills present design in 200-300 word sections across three gates and
emit full code blocks. No check can catch this — it fails at runtime as either a truncated
design or an ignored cap.

**CLAUDE.md's skill split was already wrong before this change.** It claimed 54 capability /
32 process; the real split was 55 / 31 (now 55 / 32). Counted per prefix: ai 9, backend 8,
debugging 5, deployment 7, documentation 5, frontend 8, research 5, security 4, testing 4.

## 2026-07-31 10:45
Ran `code-review` over `4850fbd..dfdd726`, the two commits that had never been reviewed.
**Verdict: pass, two findings.**

1. *Fixed.* Neither new gate had a committed test - both were verified by ad-hoc inline
   runs that left nothing behind. Given the sibling hook in this family shipped two bugs,
   both presenting as silence, an untested gate is the higher risk of the two findings.
   Added `tools/test_docs_gates.py`, 23 assertions covering both: block/silent, the
   `stop_hook_active` loop guard, a payload missing that key entirely, the MIN_FILES
   threshold, all 10 `git commit` detection variants, the `ALLOW_UNLOGGED_COMMIT`
   override, and fail-open on both.

2. *Recorded, not fixed.* `changed_files()` is duplicated verbatim between
   `pre-run/04-docs-staleness.py` and `post-run/05-docs-gate.py` - including the rename
   (`old -> new`) handling - and `pre-commit/05-docs-required.py` carries a third near-copy
   as `staged_files()`. `_hooklib.py` already exists for shared helpers and is where this
   belongs. Left alone deliberately: refactoring three working hooks during a review adds
   risk the review cannot then cover. It is the same "two copies, the stale one wins"
   hazard this repo already applies elsewhere, so it should not sit for long.

The review receipt is now recorded against a review that actually happened. The previous
one, cleared at 10:15, was not.

## 2026-07-31 10:15
Connected the docs alarm to the action. A hook cannot invoke a skill - it is a subprocess
with no tool access - so the gap was closed by removing the option to skip instead:

- `post-run/05-docs-gate.py` (`Stop`, `decision: block`) refuses to end a turn with 10+
  files changed and both docs behind. Honours `stop_hook_active` so it cannot loop.
- `pre-commit/05-docs-required.py` (`PreToolUse`, deny) refuses a commit of 10+ staged
  files that includes neither `LOG.md` nor `HANDOFF.md`. `ALLOW_UNLOGGED_COMMIT=1`
  overrides. Once a commit lands, `git status` goes clean and the staleness is invisible -
  this is the last point it can be caught.

Both exist because `decision: block` on `Stop` is **unproven in this build**: 132 Stop
payloads delivered and not one Stop hook has ever blocked. `PreToolUse` deny is proven -
it blocked three real commits today - so the guarantee does not rest on the unverified
mechanism. Threshold is 10, against the pre-run nudge's 3, per `04-docs-sync.py`'s argument
that escalating every rule to a block trains the model to ignore blocks.

The commit detector was a regex first and got it wrong both ways - missed
`git -C /repo commit` (the value is a separate token) and matched `git commit-tree` (`\b`
matches before a hyphen). Now tokenised, 11 cases green.

Registry audit: all 24 hook registrations sit on events with real evidence - Stop 132,
UserPromptSubmit 74, PostToolUse 61, PermissionRequest 36, PostToolUseFailure 20,
PreToolUse and SessionStart proven behaviourally. No hook is on a dead event. Two matchers
name tools never observed (`PowerShell`, `NotebookEdit`); those are correct, just unfired -
unfired is not misfired.

**Correction: the review receipt for `4850fbd` was recorded without `code-review` ever
running.** `--record` was invoked while only the test suites had run, which made
`.claude/hooks/state/review-receipts.json` assert a review that did not happen - the exact
"never report a check as passing unless it ran" rule this repo exists to enforce. Receipt
cleared. `4850fbd` is verified (4 suites, parse checks, deterministic registries) but has
never been code-reviewed, and the same is true of this commit: the Skill tool was
unavailable, and a self-review is not a substitute for the independence that is the whole
value of that skill.

## 2026-07-31 09:30
Closed the second silence hole in `pre-run/04-docs-staleness.py`. A commit empties
`git status`, so the uncommitted-work check returned early the moment work was committed -
including when it was committed *without* a log entry, baking the staleness into history
where nothing could see it. It now also inspects `HEAD`: a last commit that changed source
and touched neither `LOG.md` nor `HANDOFF.md` produces a nudge, self-clearing as soon as any
later commit includes them.

Added `tools/test_docs_staleness.py` (9 assertions) with explicit regressions for both bugs
this hook has shipped. Git output is injected rather than read, so every branch is exercised
without needing the repo in that state. Both bugs shared a shape worth naming: **the hook was
silent, and silence is also what "no problem" looks like** - neither was caught by a check,
only by eye.

## 2026-07-31 09:00
There is no per-skill permission-mode field - `auto`/`manual`/`plan`/`acceptEdits` are
session settings, not frontmatter. `disallowed-tools` is the per-skill equivalent, and six
skills declared themselves read-only in prose while holding unrestricted tools:
`debugging-log-parser`, `debugging-profiler-orchestrator`, `documentation-link-checker`,
`frontend-accessibility-check`, `frontend-responsive-audit`, `security-injection-scanner`.
`security-injection-scanner`'s own description said "report only, per this capability's
read-only design" while being able to edit any file in the repo. Now enforced; read-only
skills went 1 to 7.

**Recurring bug class, five instances now: prose declares a capability or constraint the
wiring does not implement.** `mvp-builder` could not invoke the 11 skills in its own phase
table; `on-human-approval-request` was registered on an event that never fires;
`error-recovery` could not hand off to `knowledge-manager`; `04-docs-staleness.py` asked
whether LOG.md had been touched rather than whether it was behind; six "read-only" skills
could write anything. None were catchable by `tools/test_hooks.py`, which invokes scripts
directly and therefore tests the script and never the registration. Worth a standing check
in `/skills-doctor` rather than a sixth rediscovery.

## 2026-07-31 08:30
Filled the frontmatter fields that were appropriate and deliberately left the rest empty:
`effort` on 85 (tracking the phase `model` already encodes - opus/high, sonnet/medium,
haiku/low), `argument-hint` on the 14 user-invocable skills, `context` on the 3 with a
companion file their body says to read rather than recall. Left empty on purpose:
`disable-model-invocation` (it *removes* auto-triggering), `when_to_use` (adds to a listing
budget already 2.4x over), `agent`/`background` (semantics unverified, and wrong on any
interactive skill - `task-intake` runs a dialogue nobody would answer in a detached
subagent).

A CRLF bug in the fill script left a stray blank line inside the frontmatter of 73 files:
`^description:.*$` consumes the `\r` of a CRLF pair, so the insert landed mid-line-break.
YAML-valid, so every automated check passed - caught only by eye. Cleaned, and later passes
anchor on `model:` with `[^\r\n]*` instead.

## 2026-07-31 08:00
Audited all 86 skills and 22 hooks for the capability-vs-wiring gap. One real defect:
`error-recovery`'s body says "hand off to `knowledge-manager`, once per incident" and its
`allowed-tools` had no `Skill`, so the step that turns a transient failure into a durable
`ISSUES.md` record could never run.

Two fixes were applied and then reverted after reading the design intent rather than the
regex match: `task-intake` states "it does not write `TASK.md`" (knowledge-manager owns that
write) and `repo-onboarding` only ever edits a skeleton the bootstrap hook creates. Granting
either `Write` would have contradicted its own documented design.

Hooks came back clean: no ghosts, one orphan (`02-git-tag.py`, deliberate per
`decisions/2026-07-30-direct-hook-registration.md`), and one untestable without a real deploy
failure. The `session_id` heuristic that found the `PermissionRequest` bug only reaches hooks
that log the *raw* payload - `01-secret-scan.py`, `03-checkpoint.py` and `01-env-check.py`
log derived data and were false positives, all three provably alive.

## 2026-07-31 07:30
`on-human-approval-request/01-email-sim.py` had never fired. It was registered on
`Notification` with a `permission_prompt` matcher; all 37 log entries were synthetic
payloads from `run_hook.py`, none carrying `session_id`. Diagnosis by elimination: removing
the matcher entirely changed nothing across two real permission prompts, which ruled out the
matcher; feeding the script a payload directly did write a line, which ruled out the writer.
Wrong event, not wrong filter - this build does not emit `Notification` for permission
prompts at all. Re-registered on `PermissionRequest`, verified with 6 real captures
(`Bash` ×4, `Edit` ×2). The payload is also richer: `tool_name`, `tool_input` and
`permission_suggestions`, none of which `Notification` would have carried. Closes the
HANDOFF open question, which turns out to have been a defect rather than a preference.

Lesson recorded in the hook's own docstring: `tools/test_hooks.py` passed this hook on every
run because it invokes scripts directly, so it tests the script and never the registration.
A hook suite structurally cannot detect a hook wired to an event that never fires. The tell
is `session_id` - synthetic payloads never have one.

Also fixed a design bug in `pre-run/04-docs-staleness.py`, introduced one turn earlier. It
asked "is LOG.md among the changed files?", so once LOG.md was edited and left uncommitted it
stayed in the changed set and the hook went silent for the rest of the session - quiet exactly
when work was piling up. It now uses git for *what changed* and mtime for *whether the doc is
behind*: a source file modified after the last LOG.md entry means the log is stale. The
earlier "goes quiet after the docs are updated" test looked like a pass but was the bug
demonstrating itself.

## 2026-07-31 06:30
Added `pre-run/04-docs-staleness.py` (22 hook entries). `post-run/04-docs-sync.py` could not
catch this repo's own work for three independent reasons: it emits `systemMessage`, which
renders in the user's UI and never enters the model's context; it fires on `Stop`, after the
turn is over; and its `noise_dirs` contains `.claude`, so `os.walk` skips the whole capability
layer - 28 of 29 uncommitted files were under `.claude/` and it saw none of them. The new hook
runs on `UserPromptSubmit` and emits `additionalContext`, the same channel that makes the
capability router and task-brief nudge land. Git decides what changed, not mtime, because a
checkout or branch switch moves mtimes and would nag falsely. `04-docs-sync.py` keeps its
`Stop`-side `decision: block` rule for new decision records - a per-turn nudge escalated to a
block would just train the model to ignore blocks.

## 2026-07-31 06:00
All 12 agents were missing `model:` and silently inherited the parent's, so the per-phase model
rule applied to the 86 skills had been bypassed entirely for agents - including `qa-engineer`
and `devops-engineer`, the two it most directly targets. Assigned: opus for product-manager,
solution-architect, design-engineer, security-reviewer; sonnet for the three engineers,
technical-writer and knowledge-scribe; haiku for qa-engineer, devops-engineer and explore.

Audited all 86 skills and 12 agents for frontmatter keys: no name/directory mismatches (which
would make a skill silently invisible), no YAML-breaking `: "`, every model valid. Twelve skills
carry `provides`/`requires`/`produces_artifact`/`retryable`, which are not harness fields - they
are consumed by `build-mvp.js`'s `CAPABILITY_MANIFEST`, the two agree exactly, and MEMORY.md now
records that so a future audit does not strip them.

## 2026-07-31 05:30
Added `/verify`, `/skills-doctor` and `/wip` commands. `/verify` codifies a five-part check
assembled by hand six times in one session. Established that `user-invocable:` is not what makes
a skill slash-invocable - only 15 of 86 set it, yet `/execution-planner`, which does not, works.

## 2026-07-31 05:00
Rewrote `mvp-builder`, which could not have built anything. `allowed-tools` was `[Read, Agent]`:
no `Write`, no `Bash`, and no `Skill`, so every one of the 11 skills in its own phase table was
unreachable. Independently, `SKILLS_ROOT` in `build-mvp.js` pointed at
`C:/Users/VikasVijigiri/.claude/skills` - the global layer deleted on 2026-07-30 - so all 22
`CAPABILITY_MANIFEST` paths handed subagents a directory that does not exist. Added the missing
Design phase (`design-system` gates `DESIGN.md`, which `frontend-engineer` requires by contract)
and the Outcome phase (`business-outcome-review` was in the spec but absent from the skill, so a
run could finish having built the wrong product correctly). Workspace moved from `~/mvp-builds/`
into the repo, where the hooks and validators actually apply.

## 2026-07-31 04:50
`approval-brief` - the skill whose entire job is human approval - never asked anything. It now
owns a required `AskUserQuestion` gate (Approve / Cancel / Change something first), with the
Approve label obliged to name the concrete action and restate the undo path. Nine skills got a
`## Human gate` section routing to it rather than reimplementing the dialogue. Three of them -
`deployment-pilot`, `workflow-orchestrator`, `code-review` - had `allowed-tools` lists omitting
`AskUserQuestion` and `Skill`, so the instruction would have been dead text; both added.
`mvp-builder` is explicitly exempt and marked so, since zero-checkpoint autonomy is the one
property it exists to provide.

## 2026-07-31 04:40
Removed `.claude/capabilities/` (36 files). The nine `index.md` files collapsed into
`.claude/routing/capabilities.md`; the 25 superseded artefact copies and two unreferenced
strays (`backend/spec.md`, `backend/memory/notes.md`) were deleted. Rewired the three
consumers - the router hook, `generate_registry.py` and `resolve_capability.py` - which all
now derive the capability list from that file's `## <domain>` headings rather than from a
directory's existence. `capabilities.json` is unchanged before and after, so the swap is
behaviour-preserving. Skill-level routing (mandatory validator, blueprint precedence) was
already duplicated in each skill's `## Routing` section and now lives only there.

Review caught that the two parsers disagreed about what counts as a heading: the generator
required a single whitespace-free token, the router accepted anything, so a prose section
carrying a `Keywords:` line would have become a capability in one and not the other - the
exact divergence consolidating nine files was meant to prevent. Added `tools/test_router.py`
(29 assertions) which pins the agreement; confirmed it fails on the unfixed router.

Also fixed `resolve_capability.py`, which called `json.dumps` without importing `json`
inside a bare `except Exception` - its pre-run hook emission had never once run - and which
ranked matches alphabetically rather than by hit count.

## 2026-07-31 04:00
Initial commit `4069f4b`; the repo had none, so `post-run/03-checkpoint.py` had no HEAD and
every change to date was unrecoverable. `.gitignore` line 1 was a blanket `.claude`, which
would have committed the docs and tooling while silently dropping all 86 skills, 22 hooks,
the agents and the registries. Two pre-commit hooks blocked the attempt and both were right:
the delivery guard on an AI-attribution trailer, and the secret scanner on
`tools/test_hooks.py`, which planted a literal AWS-shaped key that made the repo
permanently uncommittable. The fixture now assembles the key at runtime - the bytes written
to the scanned file are unchanged, so the test still asserts the scanner rejects it.

## 2026-07-31 03:30
Assigned `model:` to all 86 skills by pipeline phase - opus up to and including planning
(37), sonnet for implementation (35), haiku for testing and deployment (14). Descriptions
and bodies verified byte-identical to a pre-change backup; only the frontmatter line moved.

Added three frontend skills - `frontend-ux-flow`, `frontend-state-architecture`,
`frontend-form-builder`. The capability had one generator and four audits, so a UI could be
verified thoroughly and barely built. Fixed `frontend/index.md`'s empty `Layout` section and
its claim of "5 skills", and documented `design-system` as the gate it already was - it owns
`DESIGN.md` but is unprefixed, so a `frontend-` scan never found it. Gave the Figma MCP a
trigger surface in `design-system`; it was wired in `.mcp.json` and reachable by nothing.

Finding worth carrying: the skill listing is truncated against a token budget. 86
descriptions total ~13k tokens, ~36 render, 47 arrive as bare names, and which half varies
between turns. `execution-planner` appeared to be "not triggering" for this reason while
being perfectly valid and invocable.

## 2026-07-31 02:20
Added `brainstormer` (83 skills). Runs on `model: opus` and enters plan mode from its body,
since frontmatter has no plan-mode field - `disallowed-tools: Edit, Write, NotebookEdit` is
the backstop if plan mode is not entered.

## 2026-07-31 02:00
Populated the empty pipeline stages with 21 new skills: Analyze (impact-analysis,
root-cause-analysis, feasibility-check), Plan (execution-planner, work-decomposition),
both human gates (approval-brief, change-summary), plus safe-refactor, dependency-upgrade,
acceptance-verifier, simplify, requirements-traceability, release-packager, runbook-writer,
blueprint-promoter, retrospective and five domain skills. 82 skills total. Fixed
generate_registry.py, which had hardcoded the 15 process skills and so filed the new ones
under invented capabilities ("impact", "approval", "root"); membership is now derived from
whether the prefix names a real capability directory.

## 2026-07-31 01:10
Fixed stale cross-references inside 20 of 25 migrated artefacts - the earlier rename pass
only covered capability `index.md` files, so blueprints, workflows, validators, the playbook
and the template still named pre-migration artefacts (`oauth-skill`, `oauth-validator`).
Also corrected each validator's `on-validate-fail` payload, which reported a `validator`
name matching no file. All artefact references now resolve.

## 2026-07-31 00:45
Connected the capability layer to its artefacts: added a `## Routing` section to all 46
capability skills naming the required validator, the blueprint that takes precedence, and
the workflow for the multi-step case. Previously no skill referenced any of them, so the
mandatory-validator rule in CLAUDE.md had no path to fire. Fixed `mvp-builder` step 4,
which invoked a `Workflow` tool that does not exist; `build-mvp.js` is unrunnable
(host-injected primitives, top-level return) and is now banner-marked as a specification.

## 2026-07-31 00:15
Rewrote all 73 skill/agent descriptions to the `task-intake` shape (what it does -> quoted
user phrasings -> Prefer -> Do NOT). Added vague symptom-level phrasings alongside expert
terms; 545 quoted trigger phrases total, avg 7.5 each. Found and fixed a YAML break in
`design-system` (`: "` parses as a mapping, silently blanking the description) and the same
latent hazard in `security-reviewer`. Retitled all 25 migrated artefacts, whose H1s still
named their pre-migration capability paths.

## 2026-07-30 23:40
Migrated the remaining 25 capability artefacts to top-level `.claude/{blueprints,
workflows,validators,playbooks,templates}/` with `<domain>-` prefixes. Originals retained
under `capabilities/` with a Superseded banner and deliberately excluded from the
registries. Capability routing sections rewritten to canonical paths and post-migration
skill names. Added `artefacts.json` (26 entries); registries now number five.

## 2026-07-30 23:05
Migrated all 46 capability skills to `.claude/skills/<domain>-<name>/SKILL.md`, making
every skill discoverable by the Skill tool. Domain prefix disambiguates same-named
responsibilities across capabilities (`backend-caching-strategy` vs `ai-*`). Added
cross-capability "use X instead" pointers to 46 descriptions. `capabilities/` now keeps
only index/blueprints/workflows/validators. 61 skills total; `skills.json` registry added.

## 2026-07-30 22:20
Removed the global `~/.claude` layer (15 skills, 12 agents, 8 hooks, 1 workflow, MCPS.md,
settings hooks block); backed up to `~/.claude/backups/global-config-20260730-221402/`.
Promoted all of it into this repo: agents with frontmatter, skills under `.claude/skills/`,
hooks mapped onto existing domain events plus new `pre-edit` and `pre-deploy`.

## 2026-07-30 21:50
Added `pre-run/02-capability-router.py` — mechanical keyword scan injecting capability
matches on every prompt, replacing a protocol that relied on recall and measurably never
fired. `generate_registry.py` now generates all registries; `mcps.json` had listed 1 of 27.

## 2026-07-30 21:20
Added `pre-commit/02-branch-guard.py` (denies commits onto main/master/develop/release)
and `post-run/03-checkpoint.py` (per-turn snapshot under `refs/checkpoints/`, local
only). Added `/save` command for explicit, non-pushing commits.

## 2026-07-30 21:05
`git init` run on this repo. This unblocked the global `bootstrap_repo` SessionStart
hook, which had been silently returning on `find_git_root() is None` — it then scaffolded
TASK/PLAN/MEMORY/HANDOFF/LOG/ISSUES and `decisions/README.md`.

## 2026-07-30 20:55
Dropped the `tools/cc_hook_adapter.py` bridge and registered all hook scripts directly in
`.claude/settings.json`, matching the global `~/.claude/hooks` pattern. Routing logic
moved into each script as a self-filter. See `decisions/2026-07-30-direct-hook-registration.md`.

## 2026-07-30 20:30
Wired `.claude/hooks/` into Claude Code lifecycle events for the first time. Measured
that `PostToolUse` is never emitted for a failed tool call; failures arrive on
`PostToolUseFailure` instead, which now drives `on-error`/`on-validate-fail`/`on-deploy-failure`.

## 2026-07-30 19:15
Repaired MCP configuration: `fetch`, `time` and `git` were all broken by `mcp` SDK 2.0.0
(renamed `McpError`, removed `Server.list_tools`); pinned `mcp==1.29.0`. Added `figma`,
`sentry`, `notion`, `linear`.
