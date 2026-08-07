#!/usr/bin/env python3
"""Validate the harness-neutral contract and explicit adapter boundaries."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
failures: list[str] = []


def require(label: str, condition: bool) -> None:
    if condition:
        print(f"OK: {label}")
    else:
        print(f"FAIL: {label}")
        failures.append(label)


agents = ROOT / "AGENTS.md"
require("root AGENTS.md exists", agents.is_file())
agent_text = agents.read_text(encoding="utf-8") if agents.is_file() else ""
for heading in ("# Universal agent operating contract", "## SDLC contract", "## Evidence contract", "## Failure and safety", "## Runtime model"):
    require(f"AGENTS.md contains {heading}", heading in agent_text)

manifest_path = ROOT / "harnesses.json"
try:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as exc:
    manifest = {}
    failures.append(f"harness manifest parses: {exc}")
    print(f"FAIL: harness manifest parses: {exc}")

require("manifest names AGENTS.md source contract", manifest.get("source_contract") == "AGENTS.md")
require("manifest declares host-managed execution", manifest.get("execution_model") == "host-managed")
require("manifest lists IDE agent hosts", set(manifest.get("supported_hosts", [])) == {"Claude Code", "Codex", "Gemini", "VS Code agent"})
require("manifest documents SDK-live as optional", "sdk-live" in manifest.get("runner_modes", {}))
adapters = manifest.get("adapters", {})
for name in ("claude-code", "codex", "generic-agent"):
    require(f"manifest declares {name} adapter", name in adapters)
require("manifest declares .claude canonical root", manifest.get("canonical_root") == ".claude")
require("manifest forbids parallel sources", manifest.get("policy", {}).get("no_parallel_sources") is True)
canonical = manifest.get("canonical_paths", {})
# `workflows` is deliberately absent. The repo shipped one dynamic workflow that
# never matched the runtime contract and was deleted 2026-08-07 -- see
# decisions/2026-08-07-one-workflow-engine.md. A manifest that promises a path
# with nothing behind it is the same dead reference this suite exists to catch.
for key in ("skills", "agents", "commands", "workflow_policy", "rules", "hooks", "settings", "output_styles", "project_checks"):
    require(f"canonical path exists in manifest: {key}", bool(canonical.get(key)))
require("Claude adapter is native-canonical", adapters.get("claude-code", {}).get("status") == "native-canonical")
require("Codex adapter uses canonical source", adapters.get("codex", {}).get("skills_path") == ".claude/skills")
require("generic adapter uses canonical source", adapters.get("generic-agent", {}).get("skills_path") == ".claude/skills")
require("Claude settings path is explicit", adapters.get("claude-code", {}).get("settings_path") == ".claude/settings.json")
require("Codex canonical hooks path is explicit", adapters.get("codex", {}).get("hooks_path") == ".claude/hooks")
require("generic canonical hooks path is explicit", adapters.get("generic-agent", {}).get("hooks_path") == ".claude/hooks")

if failures:
    raise SystemExit(1)
print("OK: harness-neutral contract and adapter boundaries validated")
