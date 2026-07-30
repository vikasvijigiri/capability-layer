# Design System

Owns a project's `DESIGN.md` — forks [`DESIGN.template.md`](DESIGN.template.md)
into a repo's root the first time real UI/UX/frontend work comes up and
no project design doc exists yet, wires a one-line reference into that
project's `CLAUDE.md`, and (once a `DESIGN.md` exists) checks generated
output against its token table, layout scale, and anti-pattern list
rather than relying on ad-hoc judgment per request.

Deliberately narrow: it owns the design artifact and its single `CLAUDE.md`
reference line, nothing more — `repo-onboarding` owns the rest of the
project handbook.

First built and tested in a specific project (a `DESIGN.docx` the user
provided, forked into that repo's `DESIGN.md`) before being promoted here
as the reusable, project-agnostic version.

See [`SKILL.md`](SKILL.md) for the fork/reference/check steps.
