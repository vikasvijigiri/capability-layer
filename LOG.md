# Log

<!-- Append new entries at the TOP, never rewrite old ones.
Format: ## YYYY-MM-DD HH:MM -->

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
