# How do public Claude Code repos automate edit→commit→push→PR→review→merge, and should we extend skills or add hooks?

**Asked because:** 84 files accumulated uncommitted across five sessions while 24
registered hooks fired correctly the whole time. The decision is whether to
extend existing skills, add new hooks, or build a runner.

**Verdict:** Neither a new skill nor a new gate. **Adding a skill automates
nothing** — hooks cannot invoke skills, confirmed in the official docs, so any
new skill still waits for a human to type its name. The chain's real defect is
that our gates *ask* when they could *act*: a hook can run `git` itself, and one
public repo does exactly that. The backlog is not a missing stage; it is a
missing state transition.

## Findings

### 1. A hook cannot trigger a skill, a slash command, or a tool call. HIGH.

Official docs, confirmed by fetching the page rather than the search snippet:
hooks communicate only through exit codes, stdout, stderr and
`additionalContext`, which "Claude Code wraps … in a system reminder and inserts
into the conversation." There is no mechanism to initiate an action. Exit 2
blocks; `Stop` "blocks the stop, continues the conversation."

*Here:* every hook message in this repo that says "invoke `knowledge-manager`" is
structurally a request to the model, not a mechanism. It is honest about this,
and it is also why the same block fired four times in one session — the gate can
restate itself indefinitely and never advance the work.

### 2. But a hook can do the work itself. HIGH. This is the finding that matters.

`imehr/book-writer-plugin/.claude/hooks/version_control.py` reads
`git status --porcelain`, categorises the changed files, generates a commit
message, then runs `git add .` and `git commit` — from inside the hook, gated on
a `workflow.versionControl.autoCommit` flag in `settings.json`, default false.

*Here:* this inverts our assumption. We built gates that ask the model to act.
The same hook could commit. **What would have changed my mind was finding a hook
that commits; I found one, and it changed the recommendation** from "add a
mechanism" to "let the existing mechanism act."

Three defects in it we must not copy:
- `git add .` sweeps every unrelated change into the commit — precisely the
  failure we already have with 49 files staged across sessions.
- `run_git_command` returns `None` on any `CalledProcessError`, so a failed
  commit is indistinguishable from a successful one. Our CLAUDE.md forbids this
  exact shape ("never leave a failure silent").
- `git commit -m "{message}"` interpolated into `shell=True` with a multi-line,
  filename-derived message — breakage and injection waiting to happen.

### 3. The serious automation is a runner over a state machine, not hooks. HIGH.

`FengZhiHen1/Campfire-AI/.claude/scripts/wfctl/scheduler/processors/auto_commit.py`
is not a hook at all. It is a scheduler processor outside Claude Code. Four
properties worth stealing:

| Property | What it does | Why it matters here |
|---|---|---|
| Commit on **state transition** | fires on `newly_done_stage_instance_ids`, i.e. a stage flipping to `DONE` | a turn ending is the wrong trigger; a *unit of work finishing* is the right one |
| **Worktree per stage** (`ctx.worktree_map`) | each stage commits inside its own worktree | a commit cannot sweep unrelated files — structurally solves our 49-staged problem |
| **Git tag anchors** per stage instance | `anchor_prefix-instance-stage` | every unit is addressable and revertible without checkpoint refs |
| **Declared side effects** | returns `SideEffect(kind=…, execute=lambda)` for the orchestrator to run | decision separated from action; the processor is testable without touching git |

It also writes the commit message to a file (`.wfctl_commit_msg`) and commits
with `git commit -F`, avoiding finding 2's escaping bug, and raises `GitError`
rather than swallowing failures.

### 4. Nobody gates on backlog size, because correct design makes backlog impossible. MEDIUM.

Neither source has any notion of "too many uncommitted files." Both commit at a
boundary — a stage completing (Campfire) or a turn ending with the flag on
(book-writer) — so the condition never arises. Single-source-per-claim on the
absence, hence medium.

*Here:* this contradicts the escalation idea floated in chat earlier ("deny
`Edit` past 80 files"). That treats the symptom. The two repos that solved it
never let the number grow. **The backlog is evidence of a missing commit
boundary, not a missing threshold.**

### 5. Prior research already fixed the autonomy question. HIGH.

`docs/research/2026-08-02-generic-pipeline-skillset.md` finding 6: **gate on
blast radius, not on phase** — three independent supports. `autoresearch` runs
unattended with `/loop 20m` as a heartbeat; spec-kit gates every phase.

*Here:* commit to a feature branch is low blast radius and is the correct thing
to automate. Push, PR, merge and deploy are not, and stay human-approved. This
was already decided and is still unrecorded in `decisions/`.

## Disagreements

- **book-writer commits on a flag; Campfire commits on a state transition.** The
  flag is one settings line and ships today; the state machine is a project. I
  lean to the transition *trigger* with the flag's *simplicity* — commit when a
  skill's terminal artefact appears, not on every turn.
- **Runner vs hooks.** Campfire proves a runner is the only way to get real
  sequencing, since hooks cannot chain. But it lives outside Claude Code and
  duplicates the orchestration the model already performs. Not worth it until a
  plan has actually been executed end to end here — a gap `HANDOFF.md` has
  carried for four sessions.

## What this implies for this repo

Ordered by value per unit of work:

1. **Fix `post-run/05-docs-gate.py` before adding anything.** It blocked four
   times in one session while both docs were ~2 hours *newer* than every file it
   compared them to. A gate that cannot be satisfied by doing what it asks
   trains its own bypass — and it got bypassed three times, by me, using its own
   escape hatch. `systematic-debugging` owns this.
2. **Let one hook commit instead of asking.** Narrowest viable version: on
   `Stop`, if the only changed files are the knowledge docs, commit them
   automatically with a generated message. Zero blast radius, no review needed
   (they are not code), and it removes the most frequent block. Use `git commit -F`
   and an explicit pathspec — never `git add .`.
3. **Record the blast-radius decision** in `decisions/`. Three sources support
   it, it governs every automation choice above, and it is still only a
   `HANDOFF.md` bullet.
4. **Do not add a skill for this.** Eleven exist, nine stages are owned, and a
   twelfth would inherit the same defect: nothing can call it.
5. **Defer the runner.** Revisit only after one plan runs end to end.

## Not adopted

- **`git add .` in any form.** Both the sweep and our 49-file mess come from it.
  Explicit pathspecs only.
- **An `Edit`-blocking backlog threshold.** Treats the symptom; finding 4 says
  the boundary is what is missing.
- **A twelfth skill ("committing" / "housekeeping").** Finding 1: it could never
  self-trigger, so it would add a name to type, not automation.
- **Campfire's worktree-per-stage, for now.** Correct and it structurally solves
  the staging problem, but it presumes a stage state machine we do not have.
  Recorded because it is the answer if we ever build the runner.
- **`autoCommit` as a global settings flag.** Too coarse — it would commit code
  as readily as docs, with no review receipt.

## Sources

- [`imehr/book-writer-plugin/.claude/hooks/version_control.py`](https://github.com/imehr/book-writer-plugin/blob/main/.claude/hooks/version_control.py) — read in full
- [`FengZhiHen1/Campfire-AI/.claude/scripts/wfctl/scheduler/processors/auto_commit.py`](https://github.com/FengZhiHen1/Campfire-AI/blob/main/.claude/scripts/wfctl/scheduler/processors/auto_commit.py) — read in full
- [Claude Code hooks reference](https://code.claude.com/docs/en/hooks) — fetched; quoted on exit codes, `additionalContext`, `Stop` blocking
- `docs/research/2026-08-02-generic-pipeline-skillset.md` finding 6 — internal, read
- `.claude/hooks/` grep for `git commit` — no auto-commit anywhere; all five matches are gate hooks parsing command strings
- GitHub code search `"auto-commit" OR "autocommit" path:.claude extension:py` — 20 hits, 2 opened
