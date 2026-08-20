#!/usr/bin/env python3
"""Validate the host-neutral capability contract and honest adapter claims.

This is deliberately a contract test, not a simulated Codex or generic-agent
run. A JSON manifest cannot prove that another host executed a bridge; it can
only stop this repository from advertising one before a host-specific
conformance command exists.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / ".claude" / "portability" / "capabilities.json"
ADAPTERS = ROOT / ".claude" / "adapters"
failures: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"OK: {label}")
    else:
        print(f"FAIL: {label}" + (f" -- {detail}" if detail else ""))
        failures.append(label)


def load(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        check(f"{path.relative_to(ROOT)} parses", False, str(exc))
        return {}
    check(f"{path.relative_to(ROOT)} is an object", isinstance(value, dict))
    return value if isinstance(value, dict) else {}


contract = load(CONTRACT)
capabilities = contract.get("capabilities", {})
expected = {
    "repository_read", "repository_write", "command_execution",
    "skill_discovery", "lifecycle_hooks", "explicit_confirmation",
    "plan_approval", "delegation", "web_research",
}
check("capability names are complete and exact", set(capabilities) == expected,
      str(sorted(capabilities)))
check("safety-critical capabilities are declared",
      set(contract.get("safety_critical", [])) == {"explicit_confirmation", "lifecycle_hooks"})
check("unsupported safety-critical work refuses",
      contract.get("unsupported_behavior", {}).get("safety_critical") == "refuse")
term_capabilities = contract.get("source_term_capabilities", {})
check("source tool terms map to declared capabilities",
      bool(term_capabilities) and set(term_capabilities.values()).issubset(expected),
      str(term_capabilities))

required = {"claude-code": "Claude Code", "codex": "Codex", "generic-agent": "generic-agent"}
known_states = {"native", "host-configured", "host-managed", "bridge-required", "unsupported-refuse"}
adapters: dict[str, dict] = {}
for filename, host in required.items():
    adapter = load(ADAPTERS / f"{filename}.json")
    adapters[filename] = adapter
    check(f"{filename} names its host", adapter.get("host") == host)
    declared = adapter.get("capabilities", {})
    check(f"{filename} declares every capability", set(declared) == expected,
          str(sorted(declared)))
    check(f"{filename} uses only known capability states",
          set(declared.values()).issubset(known_states), str(declared))
    terms = adapter.get("source_term_resolution", {})
    check(f"{filename} resolves every host-specific source term",
          set(terms) == set(term_capabilities), str(sorted(terms)))
    check(f"{filename} resolves source terms with known states",
          set(terms.values()).issubset(known_states), str(terms))
    bridge = adapter.get("bridge_contract")
    if bridge:
        check(f"{filename} bridge contract path exists",
              (ROOT / bridge).is_file(), bridge)
    conformance = adapter.get("conformance")
    if adapter.get("status") == "bridge-required-unverified":
        check(f"{filename} does not claim unverified conformance",
              conformance in (None, ""), str(conformance))
    elif conformance:
        check(f"{filename} conformance command names an existing file",
              (ROOT / conformance.split()[1]).is_file()
              if conformance.startswith("python ") and len(conformance.split()) > 1
              else True,
              conformance)

claude = adapters["claude-code"]
check("Claude adapter declares checked native configuration",
      claude.get("status") == "native-configuration-checked")
check("Claude adapter names a real conformance command",
      claude.get("conformance") == "python tools/test_hook_registration.py")
check("Claude adapter maps lifecycle hooks natively",
      claude.get("capabilities", {}).get("lifecycle_hooks") == "native")

for name in ("codex", "generic-agent"):
    adapter = adapters[name]
    check(f"{name} is not falsely claimed as runtime-verified",
          adapter.get("status") == "bridge-required-unverified")
    check(f"{name} names the canonical bridge",
          adapter.get("bridge_contract") == "docs/harness-hook-bridge.md")
    for critical in contract.get("safety_critical", []):
        check(f"{name} requires a bridge for {critical}",
              adapter.get("capabilities", {}).get(critical) == "bridge-required")

skill_text = "\n".join(path.read_text(encoding="utf-8") for path in
                       (ROOT / ".claude" / "skills").rglob("SKILL.md"))
used_terms = {term for term in term_capabilities if term in skill_text}
check("every host-specific term used by a skill has a capability mapping",
      used_terms == set(term_capabilities),
      f"used={sorted(used_terms)} mapped={sorted(term_capabilities)}")

manifest = load(ROOT / "harnesses.json")
paths = manifest.get("canonical_paths", {})
check("only Claude Code is claimed as a native host",
      set(manifest.get("native_hosts", [])) == {"Claude Code"})
check("Codex and generic-agent are integration targets, not native claims",
      set(manifest.get("integration_targets", [])) == {"Codex", "generic-agent"})
check("legacy supported-host claim is absent", "supported_hosts" not in manifest)
check("harness manifest exposes adapter manifests", paths.get("adapters") == ".claude/adapters")
check("harness manifest exposes the capability contract",
      paths.get("portability_contract") == ".claude/portability/capabilities.json")
for adapter_name, filename in (("claude-code", "claude-code"), ("codex", "codex"),
                               ("generic-agent", "generic-agent")):
    declared = manifest.get("adapters", {}).get(adapter_name, {})
    check(f"manifest points {adapter_name} to its adapter manifest",
          declared.get("adapter_manifest") == f".claude/adapters/{filename}.json")

if failures:
    raise SystemExit(f"{len(failures)} portability contract check(s) failed")
print("All portability-contract checks passed")
