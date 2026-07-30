# Time MCP — .claude/mcps/time-mcp.md

Purpose: timezone-aware time conversion for backend skills that schedule
jobs (`background-job`) or need accurate cross-timezone timestamps.

Source: `modelcontextprotocol/servers` (`src/time`), official reference server.

Config

- `default_timezone`: fallback timezone when none is specified

Usage

- Use instead of hand-rolled timezone math for cron/schedule skills.

Security

- No secrets or side effects; safe to call freely.
