# Baselines — does this skill earn its place?

One file per skill, named `<skill>.md`. Each records a **baseline run**: the same
class of work attempted *without* the skill, then with it, and the difference
between the two outputs.

## Why a baseline and not a test

Every other check in this repo asserts a skill is *wired* — its frontmatter
parses, its name matches its directory, the chain names it, every path in it
resolves. All of that can be green for a skill that changes nothing about the
work. Wiring is necessary and proves nothing about value.

The Iron Law is the missing half: **a skill is only justified by a task it
measurably improves.** Without the comparison, a skill is a plausible-sounding
document that costs ~380 characters of description budget on every single turn.

## The procedure

1. **Pick a real task**, not a demo. Something the skill claims to own, which
   someone actually needed done.
2. **Do it without reading the skill.** This is the part that is hard to do
   honestly, and the whole exercise is worthless if it is faked — the baseline
   has to be a genuine attempt, not a strawman written to lose.
3. **Record what the baseline produced**, including what it got right. A skill
   that improves nothing has failed the law and should be deleted, and that is a
   legitimate result.
4. **Then run the skill** on the same task.
5. **Write the delta**: what the skill caught that the baseline missed, and what
   it cost. Cost is real — turns, tokens, gates, and the description budget.

## What makes a record trustworthy

- **The baseline is dated and specific.** "It would probably have missed X" is not
  a baseline; it is a guess dressed as evidence.
- **Findings are quoted, not summarised.** A defect the skill caught is named with
  `file:line`, so a reader can check the claim rather than accept it.
- **The cost is stated.** A skill that catches one real bug per hundred turns and
  costs a gate on every one of them is not obviously worth keeping.
- **A negative result is kept.** Deleting the record of a skill that failed is how
  the same skill gets re-proposed next quarter.

## Status

`tools/new_skill_check.py` reports a missing baseline as an advisory note rather
than a failure, because a gate nobody can satisfy gets switched off. The note is
the pressure; closing it is the work.

| Skill | Baseline |
|---|---|
| `code-review` | [code-review.md](code-review.md) — passed, 2 live defects the green suites missed |
| `designer` | [designer.md](designer.md) — initial record; live comparative run still required |
| `test-driven-development` | [test-driven-development.md](test-driven-development.md) — comparative pilot pending |
| `supply-chain-audit` | [supply-chain-audit.md](supply-chain-audit.md) — comparative pilot pending |
| `performance-engineering` | [performance-engineering.md](performance-engineering.md) — comparative pilot pending |
| `observability-sre` | [observability-sre.md](observability-sre.md) — comparative pilot pending |
| `accessibility-audit` | [accessibility-audit.md](accessibility-audit.md) — comparative pilot pending |
| `artifact-review` through `writing-plans` | [capability-layer-audit.md](capability-layer-audit.md) — dated comparative campaign; individual records link to the shared evidence |
