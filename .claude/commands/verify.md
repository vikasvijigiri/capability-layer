---
description: Run every repo check — four test suites, the env check, hook registration and a skill frontmatter parse — and report real output
---

Run the full check set for this repo. Fixed procedure, no judgement about which
checks apply — all of them always run, and a check that is skipped is reported
as skipped, never as passed.

Set `PYTHONIOENCODING=utf-8` first. Several scripts print `→` and `—`, and the
Windows console default (cp1252) raises `UnicodeEncodeError` on them — that has
already turned a passing run into a fake failure once.

Run these in order and report each one's real output line, not a paraphrase:

1. **Test suites** — all four, and do not stop at the first failure:
   - `python tools/test_hooks.py`
   - `python tools/test_process_router.py`
   - `python tools/test_docs_gates.py`
   - `python tools/test_docs_staleness.py`

2. **Environment check** — `01-env-check.py` is the only thing asserting that
   every skill has a `SKILL.md` and a routing entry, and it reports rather than
   blocks, so its output has to be read deliberately:
   - `echo '{"hook_event_name":"SessionStart"}' | python .claude/hooks/session-start/01-env-check.py`
   - then read the last line of `.claude/hooks/session-start.log`
   - `{"issues": []}` is the pass. Any entry is a real finding.

3. **Skill frontmatter** — parse every `.claude/skills/*/SKILL.md` and report
   the count plus any problems. A skill is a problem if it has no frontmatter,
   the frontmatter is not a YAML mapping, or `description` or `model` is missing
   or empty. Report the model split.

4. **Hook registration** — every script under `.claude/hooks/*/` should appear
   in `.claude/settings.json`, and every path named in `settings.json` and in
   `.claude/hooks/hooks_registry.json` should exist on disk. A hook registered
   but deleted, or present but unregistered, is invisible either way — and the
   test suites cannot catch it, because they invoke scripts directly and so test
   the script and never the registration. Report both directions.

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
