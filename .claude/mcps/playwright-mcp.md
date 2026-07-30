# Playwright MCP — .claude/mcps/playwright-mcp.md

Purpose: browser automation via accessibility tree for `testing`
(`e2e-test-generator`) and `frontend` (`visual-regression`) capabilities.

Source: Microsoft, `github.com/mcp/microsoft/playwright-mcp`.

Config

- `headless`: default `true`
- `base_url`: default target for relative navigation

Usage

- Preferred over raw browser scripting for e2e tests and accessibility-tree
  based data extraction; pairs with `qa-engineer` agent's browser checks.

Security

- Never navigate to or submit credentials into untrusted third-party sites
  from automated runs.
