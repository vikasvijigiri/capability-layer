# Figma MCP — .claude/mcps/figma-mcp.md

Purpose: bring Figma design context (frames, tokens, components) directly
into `design-engineer`'s DESIGN.md authoring and `frontend`'s component work.

Source: Figma, `github.com/mcp/com.figma.mcp/mcp`.

Config

- `figma_token_env`: environment variable holding the Figma personal access token
- `file_key`: default Figma file to read from

Usage

- Pull real token values (colour/spacing/typography) from Figma instead of
  estimating them, per the `design-system` skill's anti-estimation rule.

Security

- Read-only by default; `figma_token_env` should be scoped to the minimum
  file access needed.
