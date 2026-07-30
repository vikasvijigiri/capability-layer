# Tavily MCP — .claude/mcps/tavily-mcp.md

Purpose: advanced web search API for `research` capability's `web-search` skill.

Source: Tavily, `github.com/mcp/tavily-ai/tavily-mcp`.

Config

- `api_key_env`: environment variable holding the Tavily API key
- `max_results`: cap results per query to control token cost

Usage

- Use for research queries needing ranked, summarized web results; pair with
  `citation-check` validator before treating results as final.

Security

- Never hard-code `api_key_env`'s value; treat search queries as potentially
  sensitive (avoid leaking internal project details in query text).
