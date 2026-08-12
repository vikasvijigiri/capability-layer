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
  `--tier all` once before delivery. Cost is why: the fast tier gates every turn
  and the full tier gates delivery, so the gap between them is paid over and
  over. Both got ~4x cheaper on 2026-08-12 when the checks began running
  concurrently — the rule did not change, only how much it saves.

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

Two approval gates, each with its own tool: **Gate 1 `ExitPlanMode`** (the
plan), **Gate 2 `AskUserQuestion`** (shipment). Never asked in prose. Delivery
approval is separate and not counted. `.claude/operating.md` owns the rules and
the subagent dispatch table; `test_process_router.py` pins both.

---

## Model and effort budget

`opus` plans and diagnoses, `sonnet` codes, `haiku` extracts — per-skill
frontmatter is the source of truth. Descriptions are injected **every turn** and
are the only trigger surface, so breadth is paid there; `test_process_router.py`
prints the running total and fails a description with no `Do NOT use` clause.
The largest lever is request shape, and it is the user's: one goal per request.

---

## Commands

`.claude/commands/` holds them and each states its own contract. `/verify` and
`/verify-change` (checks), `/save` (confirmed local commit, never pushes),
`/wip` `/git-state` `/handoff` (state), `/plan-review` `/security-review`
`/pr-review` (independent review), `/release-check` `/publish` (delivery).

Safety rails, one tool each with a suite behind it — `.claude/workflow.md` owns
the table: `security_gate.py` (artefact facts, not a receipt) · `halt.py` ·
`deps.py` (licences) · `release_candidate.py` · `budget.py` · `chain.py --ledger`.

    python tools/run_checks.py --scoped                    # mid-chain
    python tools/run_checks.py --tier all --require-test   # before delivery
    python tools/resume.py       # which state this unit of work is in
    python tools/loop.py         # what the escalation ladder says next; --restore resets
    python tools/bench.py        # what this layer costs per session and per turn
    python tools/run_hook.py <event> '<json>'   # fire one hook manually

`.claude/project-checks.json` is the only place suites are listed. Run `/verify`
before declaring work done — it resolves every kind and names any it skipped.

---

## Repository map

| Path | What it is |
|---|---|
| `.claude/skills/` | one directory each; `<skill>/references/` holds depth loaded on demand |
| `.claude/agents/` | the fan-out set, plus `Explore` overriding the built-in |
| `.claude/workflow.md` | stage → owning skill → artefact; the chain and its invariants |
| `.claude/operating.md` | the commit loop, the tiers, failure budgets, gate policy, gotchas |
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

`TASK.md` · `HANDOFF.md` · `LOG.md` · `ISSUES.md` · `MEMORY.md` · `README.md`
carry state between sessions. Hooks read and gate on them, so they are code, not
commentary, and `knowledge-manager` owns their formats.

**Keep every entry minimal** — length is paid on every session that loads them.
Record only what a future reader could not reconstruct from the diff: a decision
and the option it beat, a failure whose symptom misled, what was verified and
what was not.

## The commit loop, the tiers, and the gotchas

`.claude/operating.md` owns all three: the eight auto-commit gates and what each
refuses on, the fast/slow tier split, the failure-class budgets and the
escalation ladder, and the traps that cost a session each (`PYTHONIOENCODING`, a
hook whose failure symptom is silence, a skill invisible for its filename, a
per-process `hash()`).

Two that are cheaper to know than to look up: **set `PYTHONIOENCODING=utf-8`
before any tool script**, and **fire a hook with `tools/run_hook.py` after
editing it** -- a broken hook is silent, which reads exactly like a working one.

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
