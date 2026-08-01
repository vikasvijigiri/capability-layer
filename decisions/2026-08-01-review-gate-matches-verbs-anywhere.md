# Review gate matches delivery verbs anywhere in the command

## Decision

`03-review-gate.py` matches `git commit`, `git push` and `gh pr create|merge|ready`
anywhere in the command string, not anchored to its start. `echo git commit` and
`grep -r "git push" .` therefore both return `ask`.

This is asserted by `tools/test_hooks.py` as `SUBSTRING_ASKS`, so it cannot be
quietly "fixed" into silence.

## Why

The gate's worst outcome on a false positive is one extra prompt. Its worst outcome
on a false negative is an unreviewed change reaching a shared branch. Those are not
symmetric, so the regex errs toward asking.

Anchoring would also break real usage: `cd sub && git commit -m x` is a single Bash
call and the verb is not at position zero.

Discovered while writing the PR trigger — a test asserted `echo gh pr create` should
stay silent, and it did not. Checking `echo git commit` showed the two pre-existing
verbs behave identically, so the new regex was consistent with shipped behaviour
rather than a regression. The assertion was wrong, not the code.

## Alternatives considered

- **Anchor to the start of the command, or to each `&&`/`;` segment.** Removes the
  `echo`/`grep` false positives. Rejected: segment-splitting has to model quoting to
  be correct, and getting that subtly wrong produces a false negative — the failure
  direction this gate exists to prevent.
- **Shell-tokenise and inspect argv[0].** Correct in principle. Rejected for now: it
  is real parsing work inside a hook whose stated contract is fast, deterministic and
  fail-open, and it buys only the removal of a rare, harmless extra prompt.

## Note on the sibling guard

`04-delivery-guard.py` is the opposite case and must not adopt this reasoning. It can
`deny`, so a false positive blocks legitimate work — its `\claude\` Windows path bug
did exactly that twice. Erring toward firing is correct for `ask`, wrong for `deny`.
