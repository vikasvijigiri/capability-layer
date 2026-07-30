# Chrome DevTools MCP — .claude/mcps/chrome-devtools-mcp.md

Purpose: direct Chrome DevTools protocol access (performance traces, network,
console) for `frontend`/`debugging` capability diagnosis.

Source: `github.com/mcp/ChromeDevTools/chrome-devtools-mcp`.

Config

- `remote_debugging_port`: port Chrome is listening on

Usage

- Use for perf/console/network-level diagnosis that Playwright's
  accessibility-tree view doesn't surface (e.g. `visual-regression` follow-up).

Security

- Only attach to a Chrome instance you control; remote debugging ports are
  unauthenticated by default.
