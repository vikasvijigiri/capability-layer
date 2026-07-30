# Apify MCP — .claude/mcps/apify-mcp.md

Purpose: access thousands of pre-built scrapers/crawlers/automations on the
Apify Store for `research` capability tasks with a ready-made actor.

Source: Apify, `github.com/mcp/com.apify/apify-mcp-server`.

Config

- `api_token_env`: environment variable holding the Apify API token
- `actor_id`: default actor to invoke, if any

Usage

- Check the Apify Store for an existing actor before writing a custom
  scraper from scratch (reuse-first principle).

Security

- Third-party actors run arbitrary code on Apify's infra — vet an actor's
  publisher/reviews before use; never pass secrets as actor input.
