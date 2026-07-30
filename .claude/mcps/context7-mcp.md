# Context7 MCP — .claude/mcps/context7-mcp.md

Purpose: inject up-to-date library/framework documentation into prompts,
reducing hallucinated APIs in `ai` and `backend`/`frontend` skills.

Source: Upstash, `github.com/mcp/upstash/context7`.

Config

- `default_library_hints`: optional list of libraries to bias resolution toward

Usage

- Call before generating code against an unfamiliar or fast-moving library,
  in place of relying on training-data knowledge of its API.

Security

- Read-only documentation lookup; no special data-exposure risk.
