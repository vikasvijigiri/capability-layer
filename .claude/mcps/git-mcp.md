# Git MCP — .claude/mcps/git-mcp.md

Purpose: read, search, diff, and manipulate local git repositories without
shelling out to raw `git` commands.

Source: `modelcontextprotocol/servers` (`src/git`), official reference server.

Config

- `repository`: path to the local repo (e.g. `--repository path/to/repo`)

Usage

- Prefer for repo history/blame/diff queries; use `github-mcp` for remote
  PR/issue operations instead of this server.

Security

- Read-only by default; any write operation (commit, push) requires the same
  explicit approval as a manual `git push`/`git commit`.
