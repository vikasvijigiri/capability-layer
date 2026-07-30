# Atlassian MCP — .claude/mcps/atlassian-mcp.md

Purpose: connect to Jira, Confluence, and Compass for teams tracking work
and docs in Atlassian tools instead of/alongside GitHub.

Source: Atlassian, `github.com/mcp/com.atlassian/atlassian-mcp-server`.

Config

- `site_url`: Atlassian site URL
- `auth_env`: environment variable holding the API token/OAuth credential

Usage

- Use for Jira issue/Confluence page operations from `product-manager`/
  `knowledge-scribe`-style workflows when the repo's tracker is Atlassian.

Security

- Scope the token to the minimum project/space access needed.
