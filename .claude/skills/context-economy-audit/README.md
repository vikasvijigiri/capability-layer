# Context Economy Audit

Audits this repo's `.claude/` layer (skills, hooks, agents, capabilities, `CLAUDE.md`) and/or its own
knowledge docs against [`checklist.md`](checklist.md) — 7 categories, each named after
a real bug it was found from: fixed per-turn cost, duplicated skills/hooks, stale
documentation, registry accuracy, hook pattern-matching correctness, judgment-
reliability gaps (a "default" skill with no hook backstop), and per-repo doc bloat.
Report-only; it never edits anything itself.

Distilled from a real audit conducted during the `trending-news-hub` build (2026-07-25/26)
— every category is a bug class that audit actually caught, not a speculative concern.
The `.claude/` config layer isn't itself knowledge-managed, so there's no
`decisions/`/`LOG.md` entry to point at for it; this checklist's own history is that
provenance record.

See [`SKILL.md`](SKILL.md) for the exact steps.
