# Designer and no-slop comparative pilot fixture

Use this same task for both runs:

> Design and implement a responsive settings screen for a trustworthy product.
> Include loading, empty, error, success, permission-denied, keyboard, and
> reduced-motion states. Use the existing design contract and leave evidence.

## Deliberate fixture defects

The fixture should contain at least these reviewable issues:

- one invented color outside the token table;
- spacing between existing scale values;
- a button without a visible focus state;
- a form error without an associated label or recovery action;
- an empty state with no next action;
- one debug log or unresolved to-do marker without an owner;
- one swallowed dependency error;
- one claim of completion without test or rendered evidence.

## Required comparison

Run once without reading the `designer` or `no-slop` skill, then reset the
fixture and run once with the relevant skill. Record findings, fixes, false
positives, turns, token estimate, tests, rendered-state evidence, and remaining
exceptions. A static validator result is not a substitute for the live run.
