# Stack Selector

Picks an architecture pattern and a concrete free-tier/open-source stack for a PRD, and
records the decision as an ADR in `decisions/`. Owns the **Tie-Break Order** — a fixed,
already-made priority list (single-vendor-covers-everything, no-credit-card-required,
CLI-scriptable, then a fixed vendor preference order) so picking a stack is a mechanical
walk down a list, not a runtime debate.

Reusable standalone, not just inside `mvp-builder`: any "what stack should I use"
question fits this skill.

See [`SKILL.md`](SKILL.md) for the exact tie-break list and how its ADR is consumed
downstream by `repo-onboarding` (records it) and `code-review` (checks later diffs
against it for architecture drift).
