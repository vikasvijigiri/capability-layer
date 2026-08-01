---
description: Run every repo check — four test suites, registry drift, and an 86-skill frontmatter parse — and report real output
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
   - `python tools/test_resolver.py`
   - `python tools/test_router.py`
   - `python tools/test_process_router.py`

2. **Registry drift** — the registries are generated, so any diff is real drift:
   - copy `.claude/registry/capabilities.json` aside
   - `python tools/generate_registry.py`
   - diff against the copy, and report the entry counts for all five registries

3. **Skill frontmatter** — parse all 86 `.claude/skills/*/SKILL.md` and report
   the count plus any problems. A skill is a problem if it has no frontmatter,
   the frontmatter is not a YAML mapping, or `description` or `model` is missing
   or empty. Also report the model split (opus / sonnet / haiku).

4. **Compilation** — `python -m compileall -q tools .claude/hooks`.

5. **Determinism** — run `generate_registry.py` a second time and confirm the
   output is byte-identical. A generator that is not deterministic makes every
   future drift check meaningless.

Then report:

- One line per check with its actual output (`All hook tests passed`, `86 skills;
  problems: none`), never a summary that replaces the evidence.
- **PASS only if every check passed.** If any failed, lead with the failure, quote
  the real error, and say what would fix it.

Rules:

- Never report a check as passing unless it actually ran and printed a pass.
- Never weaken or skip a check to get a green run — if a check is wrong, say so
  and leave it failing.
- Read-only. This command runs checks and regenerates the registries; it must not
  edit source, commit, or push.
- If I passed an argument, treat it as a narrowing hint (e.g. `router`, `skills`)
  and say clearly which checks you skipped as a result: $ARGUMENTS
