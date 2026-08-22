#!/usr/bin/env python3
"""Objective 20 (backward-compatible where practical) -- contract-surface
diff against a frozen golden.

"preserve contracts, interfaces and behavior unless a deliberate, justified
breaking change is required." The only objective of the fifteen the
2026-08-20 audit graded Unmeasured rather than Amber. Diffs the layer's own
public contract surface against a checked-in golden
(`.claude/contracts/layer-contract.golden.json`): a removal or rename is
reported as breaking (or warn-only for `telemetry.unstable`); an addition is
always silent-safe. A deliberate break is landed by updating the golden in
the SAME commit, per `cargo-semver-checks`'s model (confirmed and cited in
`docs/specs/2026-08-21-qualitative-objective-metrics.md`'s Cluster B
section). Report only: exits 0 unconditionally, per that spec's "report
before gate" constraint.

Six categories, five plain (removal is always breaking) and one two-tier:

  skills.names             .claude/skills/*/  directory names
  skills.frontmatter_keys  union of SKILL.md frontmatter property names
  hook_events              keys of .claude/settings.json's "hooks" object
  capabilities             keys of .claude/portability/capabilities.json's
                            "capabilities" object
  project_checks_keys      non-underscore-prefixed top-level keys of
                            .claude/project-checks.json
  telemetry                the top-level keys `build_snapshot()` in
                            .claude/hooks/telemetry/09-telemetry.py returns,
                            read live via `ast` rather than executed (a hook
                            module has side effects on import). Split
                            `stable`/`unstable` per the spec's 2026-08-22
                            resolution: `unstable` fields (`run_id`,
                            `execution_level`, `retries`) only warn on
                            removal; the other 13, present unchanged since
                            the 2026-08-20 schema consolidation, are
                            `stable` and fail on removal.

Why the golden does not join `install.py`'s `TREES` (so it does not ship to
an installed target): it is a self-referential fixture about THIS
repository's own contract surface, the same category as `tools/test_*.py`
itself (`install.py`'s own `SHIPPED_SUITES` already excludes ~40 of those
from being adopted as a target's own test set, for the identical reason -- a
target's contract surface is its own, not this one's). This script still
ships (`tools/` is in `TREES`), and degrades to a named SKIP rather than a
crash when the golden is absent, so a fresh install is never broken by this.

Run: python tools/test_contract_surface.py
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / ".claude" / "contracts" / "layer-contract.golden.json"
TELEMETRY_HOOK = ROOT / ".claude" / "hooks" / "telemetry" / "09-telemetry.py"
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.S)
KEY_RE = re.compile(r"^([A-Za-z_-]+):")


def telemetry_field_names(path: Path) -> set[str]:
    """The string keys of `build_snapshot()`'s own `return {...}` literal.

    Read via `ast`, never executed -- `09-telemetry.py` has import-time
    behavior appropriate to a hook, not to a fixture this check loads.
    """
    if not path.is_file():
        return set()
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "build_snapshot":
            for sub in ast.walk(node):
                if isinstance(sub, ast.Return) and isinstance(sub.value, ast.Dict):
                    return {
                        k.value for k in sub.value.keys
                        if isinstance(k, ast.Constant) and isinstance(k.value, str)
                    }
    return set()


def current_surface(root: Path) -> dict:
    skills_dir = root / ".claude" / "skills"
    names = sorted(
        p.name for p in skills_dir.iterdir()
        if p.is_dir() and (p / "SKILL.md").is_file()
    ) if skills_dir.is_dir() else []

    frontmatter_keys: set[str] = set()
    for name in names:
        text = (skills_dir / name / "SKILL.md").read_text(encoding="utf-8")
        m = FRONTMATTER_RE.match(text)
        if not m:
            continue
        for line in m.group(1).splitlines():
            mm = KEY_RE.match(line)
            if mm:
                frontmatter_keys.add(mm.group(1))

    settings_path = root / ".claude" / "settings.json"
    hook_events = sorted(
        json.loads(settings_path.read_text(encoding="utf-8")).get("hooks", {})
    ) if settings_path.is_file() else []

    caps_path = root / ".claude" / "portability" / "capabilities.json"
    capabilities = sorted(
        json.loads(caps_path.read_text(encoding="utf-8")).get("capabilities", {})
    ) if caps_path.is_file() else []

    pc_path = root / ".claude" / "project-checks.json"
    project_checks_keys = sorted(
        k for k in json.loads(pc_path.read_text(encoding="utf-8"))
        if not k.startswith("_")
    ) if pc_path.is_file() else []

    return {
        "skills": {"names": names, "frontmatter_keys": sorted(frontmatter_keys)},
        "hook_events": hook_events,
        "capabilities": capabilities,
        "project_checks_keys": project_checks_keys,
        "telemetry_fields": sorted(telemetry_field_names(TELEMETRY_HOOK)),
    }


def diff_surface(current: dict, golden: dict) -> dict[str, list[str]]:
    """{'breaking': [...], 'warn': [...], 'added': [...]} -- pure function.

    Synthetic-dict-testable without any filesystem mutation, per the spec's
    "Testing the instruments themselves" rule.
    """
    breaking: list[str] = []
    warn: list[str] = []
    added: list[str] = []

    def plain(label: str, cur_list, gold_list) -> None:
        cur, gold = set(cur_list), set(gold_list)
        for name in sorted(gold - cur):
            breaking.append(f"{label}: {name}")
        for name in sorted(cur - gold):
            added.append(f"{label}: {name}")

    plain("skills.names", current["skills"]["names"], golden["skills"]["names"])
    plain("skills.frontmatter_keys", current["skills"]["frontmatter_keys"],
          golden["skills"]["frontmatter_keys"])
    plain("hook_events", current["hook_events"], golden["hook_events"])
    plain("capabilities", current["capabilities"], golden["capabilities"])
    plain("project_checks_keys", current["project_checks_keys"],
          golden["project_checks_keys"])

    cur_tel = set(current["telemetry_fields"])
    stable = set(golden["telemetry"]["stable"])
    unstable = set(golden["telemetry"]["unstable"])
    for name in sorted(stable - cur_tel):
        breaking.append(f"telemetry.stable: {name}")
    for name in sorted(unstable - cur_tel):
        warn.append(f"telemetry.unstable: {name}")
    for name in sorted(cur_tel - stable - unstable):
        added.append(f"telemetry (unclassified, needs a golden entry): {name}")

    return {"breaking": breaking, "warn": warn, "added": added}


def _self_check() -> None:
    """Proves diff_surface() can fail before it is trusted -- synthetic
    dicts only, nothing on disk is touched or needs reverting."""
    syn_current = {
        "skills": {"names": ["a", "b"], "frontmatter_keys": ["name", "description"]},
        "hook_events": ["PreToolUse"],
        "capabilities": ["repository_read"],
        "project_checks_keys": ["test"],
        "telemetry_fields": ["ts", "chain"],
    }
    syn_golden_removal = {
        "skills": {"names": ["a", "b"], "frontmatter_keys": ["name", "description"]},
        "hook_events": ["PreToolUse"],
        "capabilities": ["repository_read", "EXTRA_CAP"],
        "project_checks_keys": ["test"],
        "telemetry": {"stable": ["ts", "chain"], "unstable": ["EXTRA_UNSTABLE"]},
    }
    result = diff_surface(syn_current, syn_golden_removal)
    assert result["breaking"] == ["capabilities: EXTRA_CAP"], result
    assert result["warn"] == ["telemetry.unstable: EXTRA_UNSTABLE"], result

    syn_golden_subset = {
        "skills": {"names": ["a"], "frontmatter_keys": ["name"]},
        "hook_events": [],
        "capabilities": [],
        "project_checks_keys": [],
        "telemetry": {"stable": [], "unstable": []},
    }
    result2 = diff_surface(syn_current, syn_golden_subset)
    assert result2["breaking"] == [] and result2["warn"] == [], result2

    print("  self-check: diff_surface() correctly flags a seeded removal in "
          "both a stable (breaking) and an unstable (warn-only) category, "
          "and reports zero removals when the golden is a strict subset of "
          "current -- proven before trusting it against the real golden below")


def main() -> int:
    _self_check()

    if not GOLDEN.is_file():
        print(f"SKIP: no {GOLDEN.relative_to(ROOT).as_posix() if GOLDEN.is_relative_to(ROOT) else GOLDEN} "
              f"-- this golden is a self-referential fixture about the SOURCE "
              f"layer's own contract surface and deliberately does not travel "
              f"to an installed target (see module docstring). Nothing to "
              f"diff here.")
        print("\nReport only -- exits 0 regardless.")
        return 0

    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    current = current_surface(ROOT)
    result = diff_surface(current, golden)

    print(f"objective 20 (contract-surface diff): "
          f"{len(result['breaking'])} breaking, {len(result['warn'])} warn-only, "
          f"{len(result['added'])} addition(s)")
    for line in result["breaking"]:
        print(f"  REMOVED (breaking): {line}")
    for line in result["warn"]:
        print(f"  REMOVED (warn-only): {line}")
    for line in result["added"]:
        print(f"  added: {line}")

    print("\nReport only -- exits 0 regardless, per 'report before gate'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
