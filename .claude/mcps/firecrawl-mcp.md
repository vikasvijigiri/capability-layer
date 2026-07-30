# Firecrawl MCP — .claude/mcps/firecrawl-mcp.md

Purpose: structured web scraping/extraction for `research` capability tasks
needing full-page content rather than search snippets.

Source: Firecrawl, `github.com/mcp/firecrawl/firecrawl-mcp-server`.

Config

- `api_key_env`: environment variable holding the Firecrawl API key

Usage

- Use when a single page/site needs deep extraction (e.g. `competitive-analysis`);
  use `tavily-mcp` instead for broad discovery search.

Security

- Respect target sites' robots.txt/terms; do not use to bypass paywalls or
  scrape data the source explicitly disallows.
