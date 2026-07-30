# Sequential Thinking MCP — .claude/mcps/sequential-thinking-mcp.md

Purpose: structured, revisable multi-step reasoning chains for complex
planning tasks in the `ai` capability (`agent-orchestrator`, `model-router`).

Source: `modelcontextprotocol/servers` (`src/sequentialthinking`), official reference server.

Config

- `max_steps`: bound the reasoning chain length to control token cost

Usage

- Use for genuinely multi-step, revisable plans; skip it for simple lookups
  where a direct answer is cheaper and just as correct.

Security

- No special data-exposure risk; still avoid embedding secrets in thought steps.
