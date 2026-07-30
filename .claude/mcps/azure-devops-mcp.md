# Azure DevOps MCP — .claude/mcps/azure-devops-mcp.md

Purpose: interact with Azure DevOps repos, work items, builds, releases, and
test plans for teams using Azure DevOps instead of GitHub.

Source: Microsoft, `github.com/mcp/microsoft/azure-devops-mcp`.

Config

- `organization`: Azure DevOps org name
- `project`: default project name
- `pat_env`: environment variable holding the personal access token

Usage

- Equivalent role to `github-mcp` for Azure DevOps-hosted repos; do not use
  both for the same repo in one task to avoid duplicate state.

Security

- Scope the PAT to the minimum required (work items + code, not full admin).
