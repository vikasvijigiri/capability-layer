# Terraform MCP — .claude/mcps/terraform-mcp.md

Purpose: generate and automate Terraform workflows for HCP Terraform/Terraform
Enterprise, backing the `deployment` capability's `infra-provision` skill.

Source: HashiCorp, `github.com/mcp/hashicorp/terraform-mcp-server`.

Config

- `hcp_token_env`: environment variable holding the HCP Terraform API token
- `workspace`: default Terraform workspace name

Usage

- Route `infra-provision` plan/apply steps through this server instead of
  hand-written HCL where a supported pattern exists.

Security

- Never hard-code `hcp_token_env`'s value; store in a secret manager.
- `apply`-class calls must pass `smoke-test` validator gating first (see
  `deployment/validators/smoke-test.md`) and require human approval.
