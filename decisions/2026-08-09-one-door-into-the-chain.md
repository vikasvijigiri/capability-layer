# One door into the chain

Date: 2026-08-09

## Decision

`task-brief` is merged into `writing-plans`. One skill owns framing a request
into six fields, fetching whatever it could not fill, and decomposing the result
into tasks. The chain has one entry.

What it could not fill, it **dispatches** for — `brainstormer` when the approach
is open, `research` for outside evidence, `designer` for a surface with no
contract, `repo-recon` for an unread repository, `systematic-debugging` for a
blocking failure of unknown cause. Every dispatch returns to stage 1.

Ten stages became nine, and the numbers shifted by one from `executing-plans`
onward.

## Why

The boundary between the two skills was the most restated rule in the layer. It
had a `FORBIDDEN_SUCCESSOR` entry in `test_process_router.py` whose entire job
was stopping a brief from reaching a plan, on the argument that six lines is not
a spec. The entry rule was found in seven places on 2026-08-08 and cut back to
one; `no-slop` was the eighth and had to be corrected separately.

That is a lot of machinery around one edge, and the edge was not where the
failures were. `task-brief` said so in its own file: *"Stopping here is the
chain's most common break: nothing watches for a finished brief, so an
un-handed-off one is simply forgotten."* The split created a seam, then every
check defended the wrong side of it — that a brief must not become a plan too
directly, when the observed failure was a brief becoming nothing at all.

The argument for the split was real and it survives, in a better place. "Six
lines is not a spec" is true, and framing an open approach into six fields does
bake in the first idea under a heading that looks agreed. That is now a rule
about *ordering inside one skill* — dispatch `brainstormer` before `TASK.md` is
written — rather than a rule about which of two skills the user's request lands
in. A skill can enforce its own ordering. A boundary between skills needs a
router, and this layer deleted its router on 2026-08-04.

## What this cost, accepted

- **A merged skill is longer**, and `no-slop` calls one skill doing two
  separable jobs a "god skill". The mitigation is that the two jobs are not
  separately rejectable: nobody approves a brief and rejects the plan built from
  it. Gate 1 was always on the plan.
- **The suite lost a check it cannot get back.** `FORBIDDEN_SUCCESSOR` guarded a
  real edge, and merging the endpoints means the edge cannot exist to be
  guarded. Two new forbidden edges replace it — `brainstormer` →
  `executing-plans` and `repo-recon` → `brainstormer` — but they guard skips,
  not this.
- **`docs/baselines/task-brief.md` measures a skill that no longer exists.**
  Renamed to `framing.md` and marked superseded rather than deleted; it is a
  dated measurement, and the framing contract it measured is unchanged.

## What is enforced rather than asserted

`tools/test_process_router.py`, all new on this date:

- `writing-plans` can dispatch each of the five, by name;
- it says `brainstormer` runs *before* the brief is written;
- the six field names and the `(inferred)` marking survived the merge — a merge
  that silently dropped framing would still plan correctly, which is exactly the
  failure that would not show up in a review;
- `DISPATCHED_STAGES` are numbered in the workflow table and absent from the
  handoff walk, so a dispatch cannot quietly become a handoff;
- each dispatched stage's successor is `writing-plans`, so it comes back;
- the Entry section names one door plus its two boundaries, and calls
  `brainstormer` a dispatch.

`tools/test_entry_classifier.py` gained the case the merge broke: one skill now
owns two entry shapes, so `docs/evals/trigger-queries.json` carries an `entry`
field per positive query. `eval_triggers.py` validates `query` and
`should_trigger` only, so the field costs nothing there.

## The option it beat

Keeping both skills and adding a hook that watched for a finished `TASK.md` with
no successor invoked. Rejected: a hook cannot invoke a skill, so the best it
could do is print a reminder, and `decisions/2026-08-04-hooks-never-name-a-skill.md`
already settled that a hook whose only output is the name of a skill is a second
copy of a routing decision. The seam would still exist; only its symptom would
be louder.
