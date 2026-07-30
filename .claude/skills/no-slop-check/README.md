# No-Slop Check

Runs [`checklist.md`](checklist.md) — a 10-category dead-code/quality
checklist (dead code, unhandled errors, duplication, naming, comments,
consistency, fake-done, verified-vs-claimed) — against every coding/source
file in whatever repo it's invoked in, line by line, reporting findings
with `file:line` references. Report-only; it never edits anything itself.

Promoted to global from a repo-local version first built and tested in a
specific project — see that repo's `decisions/` for the original
reasoning. A repo can still have its own project-local
`.claude/skills/no-slop-check/` with a tailored version (narrower default
scope, repo-specific framing); where one exists, it takes precedence over
this global default for that repo.

See [`SKILL.md`](SKILL.md) for the exact steps.
