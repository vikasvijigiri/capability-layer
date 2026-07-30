# Supabase MCP — .claude/mcps/supabase-mcp.md

Purpose: interact with the Supabase platform (tables, auth, storage, edge
functions) for projects using Supabase as their backend.

Source: Supabase, `github.com/mcp/com.supabase/mcp`.

Config

- `project_ref`: Supabase project reference id
- `service_role_key_env`: environment variable holding the service role key

Usage

- Prefer the anon/public key for read-only queries; only use the service
  role key for skills that explicitly need elevated access.

Security

- `service_role_key_env` bypasses row-level security — treat as a top-tier
  secret, never logged or echoed back in output.
