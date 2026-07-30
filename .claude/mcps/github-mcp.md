# GitHub MCP — .claude/mcps/github-mcp.md

Purpose: describe the GitHub MCP integration used by capabilities that need
to interact with GitHub (create PRs, list issues, push files via MCP server).

Config

- `owner`: default repo owner
- `repo`: default repository name
- `token_env`: environment variable name holding MCP token (optional)

Usage

- Clients should call the MCP server via the configured endpoint and use the
  `owner`/`repo` defaults when not specified.

Security

- Tokens must never be hard-coded. Use environment variables or secret
  managers. The runner that uses MCPs should validate token scope before use.
