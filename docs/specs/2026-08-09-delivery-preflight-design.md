# Delivery preflight — design

Date: 2026-08-09
Status: proposed

## The problem, stated from evidence rather than principle

Two failures happened today, in one session, both invisible until something
outside the layer noticed:

1. **PR #6 was opened with `--base merge-framing-into-planning` from a branch cut
   off `feat/uninstall-verb`.** It showed **10 files instead of 3**. Nothing
   caught it; a human reading the PR list caught it.
2. **`feat/uninstall-verb` was declared ready while CI was red.** Local said
   `PASS: 36 check(s) green`; CI said `ModuleNotFoundError: No module named
   'capability_layer'`. The suite checked whether a file *existed* when the
   thing that mattered was whether the package was *importable*.

Both are the same shape: **a delivery fact nobody computed.** Neither is a
judgement call, a taste question, or a thing prose can fix — each is one command
away from being decided mechanically.

## The constraint that drives the design

    gh api repos/<owner>/<repo>/branches/main/protection
    → 403 Upgrade to GitHub Pro or make this repository public

Required status checks, branch protection and merge queues are **not available**
on a free private repository. So:

> **Nothing this layer builds can *prevent* a bad merge here. It can only make
> the facts undeniable before a human clicks.**

Designing as though enforcement were possible would produce a gate that quietly
does nothing — which is this repository's stated worst failure mode. The design
target is therefore an *advisory that cannot be misread*, not a gate.

[NEEDS CLARIFICATION: is making this repository public, or upgrading to Pro, on
the table? Required checks + merge queue would turn every check below from
advisory into enforced, and that changes what is worth building. Public exposes
the layer's source; Pro is a paid plan.]

## Approaches considered

### A. `tools/delivery_check.py` — a validator that computes facts (chosen)

One script, the same shape as `resume.py`, `parallel_groups.py`, `analyze.py`
and `git_identity.py`: it derives facts and **refuses to decide**. `delivering`
runs it and quotes it; CI can run it on a pull request.

**Why it wins.** It matches the layer's dominant and proven pattern — seven
tools already work this way, and the one thing they all share is that a
statement in prose became a number somebody could check. It catches both of
today's failures directly. It costs no dependency. And it degrades honestly:
where the API says 403, the script says "unenforceable here" rather than
pretending.

**What it gives up.** It is advisory. A human who does not run it, or ignores
it, merges anyway. That is inherent to the plan tier, not to this design.

### B. Prose in `delivering`

Cheapest, and **already disproved today**. `delivering` said *"Do not bypass
protected-branch rules, required checks, or merge queue"* and *"Confirm the
worktree/branch is isolated and the base is known"* — and the wrong base was
declared anyway, by an agent that had read the file that morning. Prose that has
already failed in the exact scenario is not a candidate; it is the null option
with evidence against it.

Rejected as a *primary* mechanism. Retained as the explanation beside the check,
because a check with no stated reason gets deleted in the next tidy-up.

### C. Repo-settings-as-code

Commit the intended repository settings, assert actual matches intended. This is
genuinely valuable and it is **the only thing here that could ever be
preventive** — `allow_squash_merge`, `allow_merge_commit`, `allow_rebase_merge`
are all `true` right now, which is precisely how today's squash-vs-stack
mismatch became possible. Turning two off makes the wrong button unclickable.

**Not rejected — deferred to its own unit**, because it is a different kind of
change (it mutates repository configuration, needs its own approval, and is
`/publish`'s territory). One check *from* it lands here: compare enabled merge
methods against what the current PR shape needs.

### D. Adopt Graphite / `ghstack` / `spr`

External tooling that owns stacked PRs properly.

**Rejected, and the reason is the interesting one.** The layer's own guidance —
added today — is *"prefer no stack; independent branches off `main` merge in any
order."* Adopting tooling to make deep stacks comfortable optimises the practice
we just decided to avoid. It would also be the first runtime dependency outside
Python and `git`, in a layer whose install story is "Python 3.11+ and git alone".

Revisit if stacks turn out to be unavoidable rather than self-inflicted. Today's
five-deep stack was self-inflicted.

## The design

`tools/delivery_check.py --base <ref> --head <ref>`, defaulting to the current
branch and its tracking base.

Seven checks, each a fact with a command behind it:

| # | Check | Catches |
|---|---|---|
| 1 | `merge-base(base, head) == tip(base)` | **PR #6** — declared base ≠ branch point |
| 2 | latest CI run for **this exact SHA** concluded `success` | **the red-CI merge** — and staleness, since a run against an older SHA proves nothing about this tree |
| 3 | stack depth: open PRs chaining to the default branch | a 5-deep stack, before it is built |
| 4 | enabled merge methods vs what this PR shape needs | squash enabled while a stack is open |
| 5 | local vs origin divergence | a push that would need `--force`, and whether `--force-with-lease` was used |
| 6 | working tree clean | delivering a tree that does not match the branch |
| 7 | enforcement ceiling: probe branch protection | reports `403` as **advisory-only**, so nobody reads a green result as a guarantee |

**Exit codes:** `0` ready · `1` a check failed · `2` could not determine, and it
names which and why. `2` is not `0`. A check that could not run is reported as
unrun — the layer's Article V.

**It never merges, pushes, or rebases.** Like `git_identity`, it reports; the
human acts. `test_process_router.py` already fails any skill or command that
acquires `gh pr merge`, and this script is covered by that scan.

[NEEDS CLARIFICATION: should check 2 fail (exit 1) or warn (exit 0 with a note)
when CI has not run yet, as opposed to having run and failed? Failing is safer
and makes the check unusable on a branch pushed seconds earlier; warning risks
the exact "declared ready while red" failure this exists to stop.]

[NEEDS CLARIFICATION: which merge method should this repository standardise on —
squash (matches `CLAUDE.md`'s `wip:` checkpoint rationale, breaks stacks) or
merge commits (preserves stacks, keeps `wip:` noise in history)? Check 4 needs a
declared intent to compare against.]

## Where it plugs in

- `delivering` gains one step: run it, quote it, and do not report `clean`
  without it. Prose stays as the *reason*, never as the mechanism.
- **Not** in the fast tier: it needs network and a remote, and the fast tier
  gates every auto-commit in seconds. On-demand, like `resume.py` and
  `recon.py`.
- Optionally a CI job on `pull_request`, which is the one place it becomes
  visible to a reviewer who did not run it.

## Testing

`tools/test_delivery_check.py`, driven by injected facts rather than a live
repository — the pattern `analyze.py` uses, where `exists()` is injected so every
branch is reachable without building a repo per case. The GitHub API is a seam:
pass a callable returning the check-run payload, so 403, no-runs, stale-SHA and
failure are all ordinary test cases.

Each check must be proved red before it is believed. Today's mutation sweep
reported `hollow: none` over eight mutations on code carrying a path traversal,
so a green sweep is evidence the checks bite — never that coverage is complete.

## What this does not do

- It does not merge, and nothing in the layer does.
- It does not prevent anything on this plan tier.
- It does not manage stacks; it counts them and says when one is too deep.
- It does not configure the repository — that is unit (2), and `/publish`'s rule
  that an agent never sets its own merge gates still holds.
