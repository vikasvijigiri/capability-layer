# Engineering Policy

Universal engineering standards — SOLID/DRY/KISS/YAGNI, clean architecture,
naming, context economy, and hard safety limits — that apply to every code
change in every repository.

**Principles only.** This skill deliberately contains no workflow, no
process steps, and no repo-specific detail. It's the standard other skills
and the model itself measure a change against:

- `workflow-orchestrator` cites it when deciding how much abstraction a
  task actually needs.
- `code-review` cites it as the rubric a change is judged against.
- A repo's own `CLAUDE.md` (bootstrapped by the Repository Bootstrap hook)
  can layer *repo-specific* conventions on top — it never overrides these,
  it narrows them.

See [`SKILL.md`](SKILL.md) for the actual content.
