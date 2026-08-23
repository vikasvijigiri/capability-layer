---
paths:
  - "DESIGN.md"
  - "docs/specs/**/*.md"
---

# Design MCP grounding

When a design surface — web, iOS, or Android — has a linked Figma file,
ground its tokens, components, and layout in that file via the
`mcp__figma__*` MCP tools (`get_design_context`, `get_variable_defs`,
`get_screenshot`, `get_metadata`) rather than inventing them from the
request text alone. Figma is the only MCP server configured in this
repository that covers design work on any of these three platforms, so
there is no per-platform MCP to pick between.

The full grounding procedure and the platform-specific guidance it feeds
live in `.claude/skills/architecture/references/design-contract.md` and
`.claude/skills/architecture/references/platform-guidance.md`.
