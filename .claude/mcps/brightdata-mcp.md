# Brightdata MCP — .claude/mcps/brightdata-mcp.md

Purpose: web search/extract/navigate at scale for `research` capability tasks
needing anti-bot-resilient access (e.g. `benchmark-comparison` across sites).

Source: Bright Data, `github.com/mcp/brightdata/brightdata-mcp`.

Config

- `api_key_env`: environment variable holding the Bright Data API key

Usage

- Use when `firecrawl-mcp`/`tavily-mcp` are blocked by anti-bot measures on
  the target site; otherwise prefer the simpler server.

Security

- Same legal/ToS constraints as `firecrawl-mcp`: no bypassing paywalls or
  scraping explicitly disallowed content.
