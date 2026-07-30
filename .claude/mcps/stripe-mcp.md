# Stripe MCP — .claude/mcps/stripe-mcp.md

Purpose: official Stripe integration — customers, products, payments — for
`backend` capability tasks that need real billing/payments operations.

Source: Stripe, `github.com/mcp/com.stripe/mcp`.

Config

- `api_key_env`: environment variable holding the Stripe secret key
- `mode`: `test` or `live`; default `test`

Usage

- Always develop and validate against `test` mode first; `live` mode calls
  require explicit human approval, same as any deploy-class side effect.

Security

- Never hard-code `api_key_env`'s value or log raw card/payment data.
- Treat any `live`-mode call as a side-effect requiring `backend-change-validator`.
