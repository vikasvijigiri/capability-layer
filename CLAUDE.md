# CLAUDE.md

@AGENTS.md

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

**`.claude/workflow.md` owns the order** — stage → owner → entry condition →
artefact, for all nine, plus the `[state:*]` blocks. Read it before adding a
skill. A table here would be a lossier second copy of the one at its top, and a
rule stated twice is a rule that drifts.

Three things that table does not tell you:

- `repo-recon` sits *before* stage 1, at the entry boundary, and `research`,
  `designer` and `systematic-debugging` are dispatched or entered on failure
  rather than held in the sequence.
- `capability-layer-maintenance` is the way in when **this layer** is what
  changes — not a stage, an owner.
- `<skill>/references/` holds depth loaded per task, never per turn.

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

`ls .claude/` answers most of this. Only the parts a listing gets wrong:

- **`.claude/workflow.md`** owns the chain and its invariants;
  **`.claude/operating.md`** the commit loop, tiers, failure budgets and
  gotchas. Those two carry what used to be here.
- **`.claude/settings.json` is what actually fires.** `hooks_registry.json`
  documents the contract and cannot enforce it — when they disagree, the
  registry is the one that is wrong.
- **`.github/workflows/checks.yml` calls the same resolver as local**, so CI
  cannot drift from your machine. `.mcp.json` and `.vscode/mcp.json` are kept
  in sync **by hand** and can.
- `docs/archive/` is superseded material; see its `ARCHIVE.md` before reviving
  anything.

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
