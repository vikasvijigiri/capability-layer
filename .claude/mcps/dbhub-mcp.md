# DBHub MCP — .claude/mcps/dbhub-mcp.md

Purpose: minimal, token-efficient database access (Postgres, MySQL, SQL
Server, SQLite, MariaDB) for `backend` capability's `db-migration` skill.

Source: Bytebase, `github.com/mcp/bytebase/dbhub`.

Config

- `connection_string_env`: environment variable holding the DB connection string
- `read_only`: default `true`; migrations flip this only inside `db-migration`'s
  gated flow

Usage

- Use for schema inspection and read queries by default; route actual
  migrations through `backend-change-validator` before allowing writes.

Security

- Never hard-code `connection_string_env`'s value; least-privilege DB user.
- Migration/write mode requires the validator gate and human review.
