# Filesystem MCP — .claude/mcps/filesystem-mcp.md

Purpose: secure, scoped file read/write/search operations for capabilities
that need file access beyond the editor's own tools (e.g. batch scaffolding).

Source: `modelcontextprotocol/servers` (`src/filesystem`), official reference server.

Config

- `allowed_dirs`: explicit allow-list of directories the server may touch
- `read_only`: default `true` unless a skill's workflow requires writes

Usage

- Clients should pass only the minimal `allowed_dirs` needed for the task.
- Never point `allowed_dirs` at the whole drive or user profile root.

Security

- Enforce the allow-list at the server config level, not just by convention.
- Treat this server as having the same blast radius as direct disk access.
