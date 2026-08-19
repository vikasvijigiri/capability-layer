---
description: Run the repository's canonical lint, test, typecheck, hook, skill, agent, command, and reference checks and report real evidence before completion claims.
# User entry point: typed explicitly, never auto-invoked. Notion section 8 -
# commands are optional shortcuts, not workflow stages, and the router must work
# without them. Left invocable, their descriptions cost 1,506 chars of the skill
# listing on EVERY turn for a capability only the user triggers; per
# code.claude.com/docs/en/skills this flag also keeps them out of context.
disable-model-invocation: false
---

# Verify

Mode: read-only
Arguments: optional focus hint in `$ARGUMENTS`; full verification remains the default.

Set UTF-8 output, then run the single canonical check contract:

```bash
PYTHONIOENCODING=utf-8 python tools/run_checks.py --tier all --require-test
```

Report the actual resolved check count and final PASS/FAIL line. Do not replace
the result with a paraphrase. A skipped check is not a pass; a code change with
no test run is a failure.

If the command fails, quote the first failure and then run the relevant targeted
suite to expose its evidence. Never edit, stage, commit, push, or weaken checks.

If `$ARGUMENTS` narrows the request, state which canonical checks were skipped.
