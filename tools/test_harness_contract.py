#!/usr/bin/env python3
"""Validate the harness-neutral contract, its Claude Code binding, and the
explicit adapter and hook-bridge boundaries."""

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
# The deterministic guard against re-claiming an unbuilt runner lives on the
# manifest below ("manifest does not claim an unbuilt runner"), not here --
# AGENTS.md's prose is allowed to name the removed flags when explaining why,
# the same way CLAUDE.md narrates other deleted mechanisms by name.

# CLAUDE.md is deliberately not part of what an install ships -- the packaged
# wheel installs into a target repo with no root CLAUDE.md, and each target
# writes its own from guide/how_to_create_CLAUDE.md (see tools/test_package.py:
# "the wheel ships no root CLAUDE.md"). So its presence is optional here; its
# content is not, when it exists -- this repository always has one.
claude_md = ROOT / "CLAUDE.md"
if claude_md.is_file():
    claude_text = claude_md.read_text(encoding="utf-8")
    require("CLAUDE.md references AGENTS.md", "AGENTS.md" in claude_text)
    require("CLAUDE.md references harnesses.json", "harnesses.json" in claude_text)
    require("CLAUDE.md references the hook bridge doc", "docs/harness-hook-bridge.md" in claude_text)

hook_bridge = ROOT / "docs" / "harness-hook-bridge.md"
require("docs/harness-hook-bridge.md exists", hook_bridge.is_file())
require("AGENTS.md references the hook bridge doc", "docs/harness-hook-bridge.md" in agent_text)

manifest_path = ROOT / "harnesses.json"
try:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as exc:
    manifest = {}
    failures.append(f"harness manifest parses: {exc}")
    print(f"FAIL: harness manifest parses: {exc}")

require("manifest names AGENTS.md source contract", manifest.get("source_contract") == "AGENTS.md")
require("manifest declares host-managed execution", manifest.get("execution_model") == "host-managed")
# Three hosts, matching the three structural `adapters` buckets below --
# "Gemini" and "VS Code agent" were never their own adapter, only names
# folded into `generic-agent`, so listing them separately in
# `supported_hosts` was a naming split the structure never had. Fixed
# 2026-08-1x on feat/security-gate; kept over the 4-name list this test
# asserted first.
require("manifest lists declared IDE agent hosts", set(manifest.get("supported_hosts", [])) == {"Claude Code", "Codex", "generic-agent"})
require("manifest names the hook bridge doc", manifest.get("hook_bridge_doc") == "docs/harness-hook-bridge.md")
# `runner_modes` is deliberately absent, the same pattern as `workflows` below:
# it named --host-managed/--dry-run/--sdk-live flags on a repository runner
# that was never built. A manifest that promises a path with nothing behind it
# is the same dead reference this suite exists to catch -- see AGENTS.md's
# Runtime model section.
require("manifest does not claim an unbuilt runner", "runner_modes" not in manifest)
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
require("Claude bootloader imports AGENTS.md", "@AGENTS.md" in (ROOT / "CLAUDE.md").read_text(encoding="utf-8"))

if failures:
    raise SystemExit(1)
print("OK: harness-neutral contract and adapter boundaries validated")
