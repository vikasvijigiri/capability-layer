# Netdata MCP — .claude/mcps/netdata-mcp.md

Purpose: real-time infrastructure monitoring (metrics, logs, alerts, ML-based
anomaly detection) backing `debugging` (`profiler-orchestrator`,
`memory-leak-detector`) and `deployment` health checks.

Source: Netdata, `github.com/mcp/netdata/mcp-server`.

Config

- `netdata_endpoint`: URL of the Netdata agent/cloud instance
- `api_key_env`: environment variable holding the API key, if cloud-hosted

Usage

- Query before/after a deploy or hotfix to correlate metric anomalies with
  the change; feed findings into `hotfix-validator`/`smoke-test`.

Security

- Read-only monitoring queries only; this server should never be used to
  change infra state.
