---
description: Run the repository's canonical lint, test, typecheck, hook, skill, agent, command, and reference checks and report real evidence before completion claims.
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
