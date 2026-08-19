---
description: Run the fast verification tier against the current change and report exact evidence before review or delivery.
# User entry point: typed explicitly, never auto-invoked. Notion section 8 -
# commands are optional shortcuts, not workflow stages, and the router must work
# without them. Left invocable, their descriptions cost 1,506 chars of the skill
# listing on EVERY turn for a capability only the user triggers; per
# code.claude.com/docs/en/skills this flag also keeps them out of context.
disable-model-invocation: false
---

# Verify Change

Mode: read-only
Arguments: optional changed-area hint in `$ARGUMENTS`.

Run:

```bash
PYTHONIOENCODING=utf-8 python tools/run_checks.py --scoped
```

Scoped narrows the fast tier to the suites the changed paths map to, prints
`PARTIAL PASS` rather than `PASS`, and names what it skipped. It refuses a
`major` change with exit 2 — take the fast tier then:

```bash
PYTHONIOENCODING=utf-8 python tools/run_checks.py --tier fast --require-test
```

Then report the diff surface, resolved check count, test result, and any
unverified slow checks. Do not call a fast pass a release or completion proof.
Change nothing and do not commit.
