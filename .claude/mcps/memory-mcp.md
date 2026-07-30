# Memory MCP — .claude/mcps/memory-mcp.md

Purpose: knowledge-graph-based persistent memory, complementary to the
capability-local `memory/` folders used by `ai`/`backend` capabilities.

Source: `modelcontextprotocol/servers` (`src/memory`), official reference server.

Config

- `store_path`: location of the persisted graph store

Usage

- Use for cross-session entity/relationship memory (e.g. "this user prefers
  X"); use `knowledge-manager`'s MEMORY.md for repo-scoped conventions instead.

Security

- Do not store secrets, credentials, or PII in the memory graph.
