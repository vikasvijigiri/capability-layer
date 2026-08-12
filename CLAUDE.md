# CLAUDE.md

A Claude Code capability layer: skills, lifecycle hooks and slash commands
enforcing a spec → plan → build → verify workflow, plus the knowledge docs that
carry state between sessions. There is no application code here.

**This file is a bootloader.** Point at the thing that owns the work; never
restate it. History belongs in `LOG.md`, decisions in `decisions/`. It loads on
every session, so every paragraph is paid for on every session — prefer a
pointer to a paragraph.

---

## Working agreement

- **Validate, don't assume.** Never report a check as passing unless you ran it
  and can quote its output.
- **Reuse before creating.** Recover a deleted file from git rather than
  rewriting it from memory.
- **Be terse.** Cap skill and command responses at ~500 tokens.
- **Prefer deterministic mechanisms** — a hook or a test over a written rule.
- **Take the cheapest tier that answers the question.** `--scoped` mid-chain,
  `--tier all` once before delivery. The full tier is ~196s and was run 86 times
  across two sessions: 281 minutes of waiting.

---

## Skills

In `.claude/skills/<name>/SKILL.md`, triggered **only** by their own
`description:` frontmatter. Each states its own triggers, gates and handoffs —
read the skill, don't infer an order from this list.

**`.claude/workflow.md` owns the order**: stage → owner → artefact, the entry
rule, and the `[state:*]` blocks. Read it before adding a skill.

| Skill | Stage | Produces |
|---|---|---|
| `repo-recon` | — entry boundary | `docs/recon/` — the map, and up to five candidates |
| `writing-plans` | 1 frame and plan | `docs/plans/YYYY-MM-DD-<feature>.md`, six fields in its header |
| `brainstormer` | 2 design | `docs/specs/` |
| `executing-plans` | 3 execute | the thing itself; ticked plan checkboxes |
| `verifying-work` | 4 validate | coverage verdict + the unbacked set |
| `no-slop` | 5 sweep | findings; local repairs applied, structural reported |
| `code-review` | 6 review | findings + a verdict |
| `delivering` | 7 deliver | merged / pushed / PR opened |
| `releasing` | 8 release | the change serving at a target + a quoted smoke check |
| `knowledge-manager` | 9 record | `LOG.md`, `HANDOFF.md`, `ISSUES.md`, `decisions/` |
| `research` · `designer` · `systematic-debugging` | dispatched, or entered on failure | evidence · `DESIGN.md` · root cause |
| `capability-layer-maintenance` | entered to change this layer | aligned contracts and green validators |
| references | `<skill>/references/` — review lenses, worktrees, TDD, design contract, SRE | loaded per task, not per turn |

**Exactly two approval gates, each with its own tool.** Gate 1 is
`ExitPlanMode` (the finished plan); Gate 2 is `AskUserQuestion` (shipment, in
`releasing`). Neither is ever asked in prose — a prose question is answerable by
silence and scrolls away. Each declares itself with a `<!-- GATE n: ... -->`
marker, and `test_process_router.py` pins the set to two, checking each against
*its own* tool. Open questions are `[NEEDS CLARIFICATION]` markers resolved
together at Gate 1, never separate blocking asks. A rejection is durable: it
appends `## Rejected <date> (plan <hash>)` plus the user's words verbatim, and
`loop.py` refuses to re-present an unchanged body, retreating at three.

Delivery approval is separate and not counted: unapproved push, merge and deploy
are forbidden outright below.

### Subagents

Dispatched by the skill owning the stage, **only when the user has asked for
subagents**. `Explore.md` overrides the built-in to pin haiku.
`.claude/workflow.md` carries the table; `test_process_router.py` asserts each
agent has a "do NOT use" clause, a `tools:` allowlist, a pinned model, and a
dispatcher that names it — and that it names its dispatcher back.
`task-implementer` **never runs two at once**.

---

## Model and effort budget

`opus` for planning and diagnosis, `sonnet` for coding and procedure, `haiku`
for pure extraction — per-skill frontmatter is the source of truth.
`systematic-debugging` keeps `opus` though diagnosis is not planning.

Two other levers: **`/fast`** (same Opus, less extended thinking — right for doc
sweeps, wrong for debugging), and **request shape**, which is the biggest and is
the user's. One goal per request cuts deliberation directly.

Descriptions are injected **every turn** and are the only trigger surface, so
breadth is paid there. `test_process_router.py` prints the running total. Every
description carries a `Do NOT use` clause and two checkers fail without it.

---

## Commands

    /verify          canonical full lint, test, typecheck and capability checks
    /verify-change   scoped checks for the current change
    /save            explicitly confirmed local commit; never pushes
    /wip             branch, uncommitted work, documentation staleness
    /git-state       exact Git counts and branch accounting
    /plan-review     independent spec/plan review before execution
    /security-review independent trust-boundary review
    /release-check   non-destructive release-readiness evidence
    /handoff         durable read-only session-state report
    /pr-review       high-confidence pull-request review; local by default
    /publish         create the repo, push, open the PR — one explicit yes

Safety rails, each a tool with a suite behind it — `.claude/workflow.md` owns
the table:

    python tools/security_gate.py --base main  five artefact facts; a receipt is not one
    python tools/halt.py --halt "<reason>"     halt every mutating tool; --resume lifts it
    python tools/deps.py [--sbom]              licence verdict; undetermined is not ok
    python tools/release_candidate.py          the report Gate 2 reads, rollback executed
    python tools/budget.py                     turns and elapsed against a ceiling
    python tools/chain.py --ledger             the append-only audit trail

Raw equivalents, from the repo root:

    python tools/run_checks.py --scoped                    # mid-chain
    python tools/run_checks.py --tier all --require-test   # before delivery
    python tools/resume.py            # which state this unit of work is in
    python tools/analyze.py           # is the plan internally consistent (pre-Gate 1)
    python tools/loop.py              # what the escalation ladder says to do next
    python tools/loop.py --restore    # reset to the last verified-green tree
    python tools/new_skill_check.py <name>|--all   # is one skill actually reachable
    python tools/smoke.py --url <url> --expect-status 200   # is it actually serving
    python tools/run_hook.py <event> '<json-payload>'       # fire one hook manually

Individual suites live in `.claude/project-checks.json`, the only place they are
listed. Run `/verify` before declaring work done — it resolves every kind and
names any it skipped.

---

## Repository map

| Path | What it is |
|---|---|
| `.claude/skills/` | one directory each; `<skill>/references/` holds depth loaded on demand |
| `.claude/agents/` | the fan-out set, plus `Explore` overriding the built-in |
| `.claude/workflow.md` | stage → owning skill → artefact; the chain and its invariants |
| `.claude/hooks/<event>/` | hooks that act, deny or measure |
| `.claude/settings.json` | what actually fires; `hooks_registry.json` documents the contract |
| `.claude/commands/` | the slash commands above |
| `tools/` | `run_checks.py`, `resume.py`, `loop.py`, `smoke.py`, `run_hook.py`, the suites |
| `docs/specs/`, `docs/plans/`, `docs/research/` | skill outputs, one dated file each |
| `docs/archive/` | superseded; see `docs/archive/ARCHIVE.md` |
| `decisions/` | dated ADRs |
| `.github/workflows/checks.yml` | CI; calls the same resolver, so it cannot drift from local |
| `.mcp.json`, `.vscode/mcp.json` | MCP servers, kept in sync by hand |

`~/.claude/` holds no skills or agents. **`../physrun/` is a sibling repo, not
part of this one** — the first product built with this layer; copying this file
there would be wrong, since it asserts there is no application code here.

## Knowledge docs

Six files at the repo root carry state between sessions. Hooks read and gate on
them, so they are code, not commentary:

`TASK.md` (status line + completed trail) · `HANDOFF.md` (current work, pending,
next) · `LOG.md` (history) · `ISSUES.md` · `MEMORY.md` · `README.md`

**Keep every entry minimal.** They are read by someone with no context, and
length is paid on every session that loads them. Record only what a future reader
could not reconstruct from the diff — a decision and the option it beat, a
failure whose symptom misled, what was verified and what was not. Never restate
the diff.

`session-start/03-state-report.py` measures staleness from git alone and renders
the matching `[state:<key>]` block from `.claude/workflow.md`. It names no skill;
`test_hook_registration.py` fails any hook that does.

## The commit loop

Commits are automatic and local. `post-run/06-artifact-autocommit.py` fires at
the end of every turn and commits what changed as a `wip:` checkpoint, if and
only if all of these hold. What "the checks pass" means is
`.claude/project-checks.json` resolved by `.claude/hooks/_projectchecks.py` — the
same code `/verify` calls, so the two cannot disagree:

| Gate | Refuses when |
|---|---|
| branch | on `main`/`master`/`develop`/`release` |
| size | more than `MAX_FILES = 25` changed — a unit of work, not a checkpoint |
| secrets | any changed file matches `_hooklib.SECRET_PATTERNS` |
| checks | any **fast-tier** command exits non-zero |
| unverified code | the change contains code and **no test check ran** |
| migration | the change touches `_hooklib.MIGRATION_PATH_PATTERNS` |
| minimal diff | a changed path is named by neither `TASK.md` nor any `docs/plans/*.md` — **and the refusal prints those paths** |
| message | the generated subject matches `_hooklib.AI_ATTRIBUTION_PATTERNS` |

**Minimal means "no unrelated file", not "few lines".** It refuses rather than
warns, because a lone warning among seven refusals is the clause nobody reads.
The accepted cost is real — a turn touching an unplanned file gets no checkpoint
— which is why the refusal names the paths. The gate applies only where a
declaration source exists.

Every clause is a fact about the artefact, never about process. A refusal is
always spoken. It **never pushes**, never `git add .`.

Two dependencies, both easy to break:

- `UAIOS_AUTOCOMMIT_RUNNING` guards re-entry. Without it the hook runs the suites
  which run the hook, unbounded — presenting as a hang, not an error.
- Its commits **bypass `PreToolUse`**, so the secret and attribution checks run
  *inline* from `_hooklib`.

**`pre-commit/02-branch-guard.py` resolves the command's target repo, not the
session's** — `git -C ../other commit` commits somewhere else. Both hooks use
`_hooklib.is_git_commit`, a tokeniser rather than a regex, because `-C` takes a
value and no regex repetition can consume it.

Checks come in **two tiers**, because cost differs by an order of magnitude and a
gate nobody can afford to run gets switched off:

| Tier | Kinds | Runs | Gates |
|---|---|---|---|
| fast | lint · typecheck · test | every turn, seconds | the auto-commit |
| slow | build · audit · e2e · smoke | before delivery, minutes | push / PR, and CI |

`--scoped` narrows the fast tier on a `small` change and refuses a `major` one.
**"Fast" means *ran fewer checks and said which*, never *green on less
evidence*** — the three rules keeping that true are in `.claude/workflow.md`,
which owns the scope table.

**Review moves to the push/PR**, over the whole branch — a commit needing a human
is not a checkpoint.

## When the checks go red

`06-artifact-autocommit.py` writes the failing output to
`.claude/hooks/state/check-failure-report.md`, counts consecutive failures of the
*same* failure (digits normalised), and names `systematic-debugging`. It
**suggests**, never triggers — a hook cannot invoke a skill — and never blocks.

**The budget depends on the kind**, decided by `_hooklib.FAILURE_CLASSES` before
anything is spent: `security` 0, `transient` 2, `merge` 2,
`deterministic`/`unknown` 3. Unmatched output is a defect, never noise.
`tools/loop.py` turns class + attempt into one of six rungs (retry, repair,
restore, rebase, retreat, block); `test_loop.py` proves by exhaustion that every
path terminates. **`restore` is load-bearing** — three failed repairs leave the
tree worse than they found it. Green updates `refs/uaios/green/<slug>`; restore
goes there.

Green closes the loop **forward**: `verifying-work` → `code-review` →
`delivering`, so "no longer failing" is not mistaken for "finished".

**The slow tier is the only thing that verifies the running system.** Everything
else reads the source. `tools/smoke.py` starts the app, waits, probes and tears
the process tree down.

Detection is a data table (`MARKER_CHECKS`) covering Node, Deno, Python, Rust,
Go, Java, Kotlin, Ruby, PHP, Elixir, .NET and `make`; a new ecosystem is a row.
`.claude/project-checks.json` overrides any of it, `false` disables a kind as a
stated decision, and a configured tool that is not installed is **skipped and
named**, never failed.

---

## Gotchas

- **Set `PYTHONIOENCODING=utf-8` before running any tool script.** Several print
  `→` and `—`; the Windows console default raises `UnicodeEncodeError` and turns
  a passing run into a fake failure.
- **A hook bug's symptom is silence** — identical to "no problem". After editing
  any hook, fire it with `tools/run_hook.py` against a realistic payload.
- Hook scripts read input via `_hooklib.load_payload()`, so both stdin and
  `HOOK_PAYLOAD` work.
- **A skill is silently invisible** if it is a flat `.md` rather than
  `<name>/SKILL.md`, or if its frontmatter `name:` differs from its directory.
  Nothing errors — it just never appears.
- **Never use a per-process `hash()` where a value must be stable across runs.**
  It is SipHash-seeded per process; `chain.py` fingerprinted the tree that way
  and its stall detector's third limb was dead for its whole life.
- The `github` MCP server needs `GITHUB_TOKEN`. `gh` itself is already
  authenticated on this machine.

---

## Never

- Ignore a failing test, or weaken/delete one to make a build pass.
- Report a check as passing that was not actually run.
- Commit secrets or credentials.
- Push, merge, publish or deploy without explicit user approval.
- Create a duplicate implementation of something that already exists.
- Put AI attribution in git history. Two layers: `attribution.commit`/`pr` are
  `""` in `~/.claude/settings.json`, and `pre-commit/03-attribution-guard.py`
  DENIES a hand-written `-m` carrying a trailer, plus a `user.name`/`user.email`
  resolving to an AI.
