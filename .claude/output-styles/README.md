# output-styles

Declared by `harnesses.json` as `paths.output_styles`, so the directory is part
of the harness contract and exists whether or not a style has been added.

Empty is the correct state until this repo defines one. Claude Code reads output
styles from here; an absent directory and an empty one behave identically to the
harness, but only one of them tells a reader the slot is deliberate.

A `.gitkeep` stood here until 2026-08-07 — see `.claude/agent-memory/README.md`
for why it was replaced rather than kept.
