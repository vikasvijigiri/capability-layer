---
description: Run every repo check — seven test suites, the env check, hook registration and a skill frontmatter parse — and report real output
---

Run the full check set for this repo. Fixed procedure, no judgement about which
checks apply — all of them always run, and a check that is skipped is reported
as skipped, never as passed.

Set `PYTHONIOENCODING=utf-8` first. Several scripts print `→` and `—`, and the
Windows console default (cp1252) raises `UnicodeEncodeError` on them — that has
already turned a passing run into a fake failure once.

Run these in order and report each one's real output line, not a paraphrase:

1. **Test suites** — all five, and do not stop at the first failure:
   - `python tools/test_hooks.py`
   - `python tools/test_process_router.py`
   - `python tools/test_hook_registration.py`
   - `python tools/test_docs_gates.py`
   - `python tools/test_docs_staleness.py`
   - `python tools/test_artifact_autocommit.py`
   - `python tools/test_index_scope_guard.py`

2. **Environment check** — `01-env-check.py` is the only thing asserting that
   every skill has a `SKILL.md` and a routing entry, and it reports rather than
   blocks, so its output has to be read deliberately:
   - `echo '{"hook_event_name":"SessionStart"}' | python .claude/hooks/session-start/01-env-check.py`
   - Since 2026-08-02 it prints its findings as `additionalContext` and stays
     silent when clean, so **no output is the pass**. It also appends to
     `.claude/hooks/session-start.log`; `{"issues": []}` there is the same pass.
     Any entry is a real finding.

3. **Skill frontmatter** — parse every `.claude/skills/*/SKILL.md` and report
   the count plus any problems. A skill is a problem if it has no frontmatter,
   the frontmatter is not a YAML mapping, or `description` or `model` is missing
   or empty. Report the model split.

4. **Hook registration** — `tools/test_hook_registration.py` in step 1 now
   asserts this in all three directions (disk / `settings.json` /
   `hooks_registry.json`). It exists because this step was prose for two weeks
   and the drift accumulated anyway: `02-bootstrap-docs.py` sat on disk and in
   the registry but not in `settings.json`, so it never fired in a real session.
   Report that suite's count line; no manual cross-check is needed.

5. **Compilation** — `python -m compileall -q tools .claude/hooks`.

Then report:

- One line per check with its actual output (`All hook tests passed`, `2 skills;
  problems: none`), never a summary that replaces the evidence.
- **PASS only if every check passed.** If any failed, lead with the failure, quote
  the real error, and say what would fix it.

Rules:

- Never report a check as passing unless it actually ran and printed a pass.
- Never weaken or skip a check to get a green run — if a check is wrong, say so
  and leave it failing.
- Read-only. This command runs checks; it must not edit source, commit, or push.
- If I passed an argument, treat it as a narrowing hint (e.g. `hooks`, `skills`)
  and say clearly which checks you skipped as a result: $ARGUMENTS
