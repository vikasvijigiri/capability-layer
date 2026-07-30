# GitLab MCP — .claude/mcps/gitlab-mcp.md

Purpose: GitLab-hosted equivalent of `github-mcp` — projects, merge requests,
issues, pipelines, wikis, releases.

Source: Zereight, `github.com/mcp/zereight/gitlab-mcp` (community-maintained).

Config

- `gitlab_url`: instance URL (supports self-hosted GitLab)
- `token_env`: environment variable holding the GitLab access token

Usage

- Use for GitLab-hosted repos; do not mix with `github-mcp`/`azure-devops-mcp`
  for the same repository in one task.

Security

- Scope the token to the minimum project/group access needed; never
  hard-code it.
