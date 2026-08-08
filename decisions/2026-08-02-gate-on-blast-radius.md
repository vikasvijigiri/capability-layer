# Gate on blast radius, not on phase

Date: 2026-08-02

## Decision

An action is gated by **how hard it is to undo**, not by which workflow stage it
belongs to. Three bands:

| Band | Actions | Rule |
|---|---|---|
| Reversible, local | edit, diff, stage, local commit on a feature branch, writing a prose artefact | **act** — a hook may do it without asking |
| Reversible, shared | PR opened, branch pushed | **ask once, per action** |
| Hard to reverse or externally visible | merge to `main`, publish, deploy, rollback | **ask per action and per target**; never inferred from an earlier approval |

Review sign-off is exempt from this scheme and stays human at every band: it is
the only thing that writes the receipt `pre-commit/03-review-gate.py` checks, so
an agent recording its own sign-off would make the gate theatre.

## Why

Gating by phase produces the wrong answer at both ends. `spec-kit` puts a hard
gate between every phase (`on_reject: abort`), which stops a scratch experiment
as firmly as a production deploy. `autoresearch` runs fully unattended — *"the
human is asleep"* — which is correct for a scratch directory and wrong for a
merge. Neither is a rule; both are a domain assumption.

Reversibility is the property that actually differs, and it is observable rather
than declared. This repo has the failure in both directions at once:

- **Over-gated:** 24 hooks fired correctly for five sessions while 84 files went
  uncommitted, because every gate asked the model to act instead of acting. A local
  commit on a feature branch is trivially reversible and was being treated as
  though it were a deploy.
- **Under-gated:** nothing sits between `git add` and `git commit`, so 49 files
  staged in earlier sessions sat waiting to be swept into an unrelated commit.

Supported by three independent sources, recorded in
`docs/research/2026-08-02-generic-pipeline-skillset.md` (finding 6) and
`docs/research/2026-08-02-automating-the-git-chain.md` (findings 3 and 5).

## Alternatives considered

- **Gate every phase, as `spec-kit` does.** Rejected: uniform gating trains the
  bypass. `post-run/05-docs-gate.py` blocked five turns in one session and its
  escape hatch was used three times — the gate was correct on the first turn and
  noise by the fifth. `post-run/04-docs-sync.py` already made this argument in its
  own docstring; this decision generalises it.
- **Run unattended by default, as `autoresearch` does.** Rejected: this repo's
  product *is* its `.claude/` directory, so an agent editing hooks is editing the
  thing that guards it. The irreversible band is not hypothetical here.
- **A file-count threshold — deny edits past N uncommitted files.** Rejected on
  evidence: neither public repo that solved the backlog has any notion of "too
  many uncommitted files". Both commit at a boundary, so the number never grows. A
  threshold treats the symptom of a missing commit boundary.
- **Band by directory instead of by reversibility** (e.g. `docs/` is always safe).
  Rejected as a primary rule — it is a useful *proxy* and the artefact auto-commit
  scope uses it, but `.claude/` contains both prose and executable hooks, so the
  directory does not reliably predict how bad a mistake is.
