# Azure MCP — .claude/mcps/azure-mcp.md

Purpose: connect AI agents to Azure services (provisioning, queries, resource
management) for `deployment`/`backend` capability tasks targeting Azure.

Source: Microsoft, `github.com/mcp/com.microsoft/azure`.

Config

- `subscription_id`: target Azure subscription
- `auth_env`: environment variable holding the service principal credentials

Usage

- Use for Azure-specific provisioning; prefer `terraform-mcp` when the change
  should be captured as reusable infra-as-code rather than an ad-hoc call.

Security

- Scope the service principal to the minimum roles needed (least privilege).
- Any resource-mutating call requires human approval per `deployment-pilot`.
