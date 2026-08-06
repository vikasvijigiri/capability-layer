---
description: Diagnose the capability layer's skill, agent, command, routing, reference, and description-budget health with deterministic repository checks.
---

# Skills Doctor

Mode: read-only
Arguments: optional focus hint in `$ARGUMENTS`; report skipped checks when narrowing.

Run the deterministic checks that can be reproduced from the repository:

```bash
PYTHONIOENCODING=utf-8 python tools/new_skill_check.py --all
PYTHONIOENCODING=utf-8 python tools/test_process_router.py
PYTHONIOENCODING=utf-8 python tools/test_agent_standards.py
PYTHONIOENCODING=utf-8 python tools/test_referenced_paths.py
PYTHONIOENCODING=utf-8 python tools/test_command_standards.py
```

Report required failures before advisory notes. Include the skill count, model
split, longest descriptions, missing baselines, agent count, command count, and
dead references from the real output. Do not claim to inspect the current
session's rendered system listing; that is not repository-observable.

Report only. Change nothing, stage nothing, and commit nothing.
