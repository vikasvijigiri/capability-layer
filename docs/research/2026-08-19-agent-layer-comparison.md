# Agent Layer Comparison

**Asked because:** Compare this capability layer, including every skill and hook, with mature public agent customization repositories before continuing contract hardening.

**Verdict:** The local layer is stronger than the public references on explicit repository-local safety gates, portability refusal boundaries, and validator-backed workflow state. It is weaker on evidence of behavioral skill performance and on keeping an external comparison record that separates static parity from live-host conformance. The next improvement is a layer-wide contract validator plus an explicit comparison rule, not wholesale copying from another repository.

## Findings

### Skills and skill discovery

- **Superpowers** treats skill documents as behavior-shaping artifacts and applies a test-first pressure-scenario loop: baseline without the skill, minimal change, then rerun and close rationalization loopholes. Source: [writing-skills/SKILL.md](https://github.com/obra/superpowers/blob/main/skills/writing-skills/SKILL.md). Confidence: high. Implication here: static frontmatter and marker tests are necessary but do not prove that a skill changes agent behavior.
- **Anthropic skills** uses progressive disclosure: metadata, a bounded `SKILL.md`, then optional scripts/references, with a validation script checking the folder, frontmatter, name, and description. Sources: [skill-creator/SKILL.md](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md) and [quick_validate.py](https://github.com/anthropics/skills/blob/main/skills/skill-creator/scripts/quick_validate.py). Confidence: high. Implication here: the existing `new_skill_check.py` covers the structural layer; a separate behavioral-evaluation record must remain explicit and optional when live model calls are unavailable.
- **Superpowers portability guidance** defines support by automatic bootstrap injection, skill discovery, tool mapping, tests, and a real acceptance transcript. It explicitly distinguishes static integration from a live host run. Source: [porting-to-a-new-harness.md](https://github.com/obra/superpowers/blob/main/docs/porting-to-a-new-harness.md). Confidence: high. Implication here: adapter metadata must not be upgraded to verified support without a host-specific conformance receipt.

### Hooks

- **GitHub Awesome Copilot** defines hooks as small, deterministic, synchronous commands with explicit side effects, bounded timeouts, narrow matchers, and representative JSON payload tests. Sources: [hooks.instructions.md](https://github.com/github/awesome-copilot/blob/main/instructions/hooks.instructions.md) and [automating-with-hooks.md](https://github.com/github/awesome-copilot/blob/main/website/src/content/docs/learning-hub/automating-with-hooks.md). Confidence: high. Implication here: the local hook policy should continue enforcing one responsibility, payload loading, explicit deny behavior, and no strategic-file authoring.
- The same guidance separates hooks from skills: hooks are for deterministic guardrails and lifecycle automation; skills are for open-ended reasoning and multi-step workflows. Confidence: high. Implication here: do not move workflow judgment into hooks merely to increase automation coverage.

### Local surface inventory

- 14 skills under `.claude/skills/<name>/SKILL.md` were compared for frontmatter,
	routing, output/verification language, and success criteria.
- 24 executable event hooks under `.claude/hooks/<event>/*.py` were compared for
	module purpose, payload loading, event registration, deny behavior where
	applicable, and strategic-file write boundaries (17 at this report's original
	writing on 2026-08-19; `post-tool/02-skill-cost.py` and
	`post-run/09-telemetry.py` added 2026-08-20; `post-tool/04-read-cost.py`
	and `post-tool/05-agent-cost.py` added 2026-08-21; `post-tool/06-tool-cost.py`,
	`user-prompt/02-turn-timer.py` and `post-tool/07-human-cost.py` added
	2026-08-21, same day, `four-more-spec-metrics`).
- The inventory is structural evidence only; it does not prove that a model
	triggers every skill or that another host executes every hook.

## Disagreements

- Superpowers favors strict behavioral pressure testing for every skill edit, while Anthropic's public validator focuses on package shape and leaves quality evaluation to an iterative eval workflow. This repository should keep both layers separate: deterministic local contract tests on every run, with paid/live behavioral evals recorded as optional evidence rather than treated as structural proof.
- Public repositories optimize for their host ecosystems. Their tool names, event payloads, and installation mechanisms are not portable facts. This repository's Claude-native settings and bridge contract remain authoritative for local execution.

## Not adopted

- No public skill text was copied wholesale. The comparison extracts invariants only.
- Repository star counts were not treated as technical evidence. They establish ecosystem reach, not correctness of a specific contract.
- No Codex, generic-agent, or other non-Claude adapter was marked verified from documentation or metadata alone.
- No live model or external host run was claimed; this workspace has no approved paid trigger-evaluation receipt or non-Claude conformance receipt.

## Sources

- https://github.com/obra/superpowers
- https://github.com/obra/superpowers/blob/main/skills/writing-skills/SKILL.md
- https://github.com/obra/superpowers/blob/main/docs/porting-to-a-new-harness.md
- https://github.com/anthropics/skills
- https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md
- https://github.com/anthropics/skills/blob/main/skills/skill-creator/scripts/quick_validate.py
- https://github.com/github/awesome-copilot
- https://github.com/github/awesome-copilot/blob/main/instructions/hooks.instructions.md
- https://github.com/github/awesome-copilot/blob/main/website/src/content/docs/learning-hub/automating-with-hooks.md
