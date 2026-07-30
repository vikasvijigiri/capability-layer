# MongoDB MCP — .claude/mcps/mongodb-mcp.md

Purpose: official MongoDB server access (collections, queries, aggregation)
for `backend` capability tasks on a Mongo-backed stack.

Source: MongoDB, `github.com/mcp/mongodb-js/mongodb-mcp-server`.

Config

- `connection_string_env`: environment variable holding the Mongo URI
- `read_only`: default `true`

Usage

- Same gating as `dbhub-mcp`: schema/document changes route through
  `backend-change-validator` before being committed.

Security

- Use a least-privilege database user; never embed the connection string in
  a skill file or committed config.
