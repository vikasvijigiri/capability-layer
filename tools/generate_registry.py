#!/usr/bin/env python3
"""Regenerate every file under .claude/registry/ from what is actually on disk.

Usage:
    python tools/generate_registry.py

Generates all five registries: capabilities, skills, artefacts, agents, mcps.
An earlier version generated only capabilities.json, so `agents.json` and
`mcps.json` were maintained by hand and drifted: `mcps.json` listed 1 MCP while
`.claude/mcps/` documented 27 and `.mcp.json` wired 14. A registry that is wrong
is worse than one that is missing, because it gets read as authoritative.

The capability list comes from the `## <domain>` headings in
`.claude/routing/capabilities.md`, which is also what the router hook parses.
It came from the existence of `.claude/capabilities/<domain>/` until 2026-07-31;
that directory held nine index files plus superseded artefact copies, and was
removed once the copies were deleted and the routing consolidated. Deriving the
list from a file rather than a directory means one edit adds a capability and
the two consumers cannot disagree about which ones exist.

`session-start/01-env-check.py` only checks these files are non-empty, which is
exactly why that drift went unnoticed -- non-empty is not accurate. Regenerate
rather than editing by hand.

Paths are stored repo-relative with forward slashes so the registry is portable
and diffable across machines.
"""

from __future__ import annotations

import functools
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLAUDE = ROOT / ".claude"
REGISTRY = CLAUDE / "registry"


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def frontmatter(path: Path) -> dict:
    """Parse a leading YAML frontmatter block. Only flat `key: value` pairs are
    needed here, so this deliberately avoids a yaml dependency."""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return {}
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    out = {}
    for line in parts[1].splitlines():
        m = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if m:
            out[m.group(1).strip()] = m.group(2).strip()
    return out


def listing(directory: Path) -> list[str]:
    return sorted(p.stem for p in directory.glob("*.md")) if directory.is_dir() else []


# A skill is a capability skill only if its `<prefix>-` names a real capability.
# Deriving this beats a hardcoded list, which silently rotted the moment process
# skills were added: `impact-analysis` was filed under a non-existent "impact"
# capability, and 15 others likewise.
#
# The capability list came from the existence of `.claude/capabilities/<domain>/`
# until 2026-07-31. It now comes from the `## <domain>` headings in
# `.claude/routing/capabilities.md` -- the same file the router hook parses, so
# adding a capability is one edit in one place and cannot leave the two
# consumers disagreeing about which capabilities exist.
ROUTING = CLAUDE / "routing" / "capabilities.md"

# PROCESS_OVERRIDES is only for process skills whose prefix collides with a real
# capability name. `deployment-pilot` is the case that exists; it is a cross-cutting
# process skill, not one of the deployment capability's skills.
PROCESS_OVERRIDES = {"deployment-pilot"}


@functools.lru_cache(maxsize=1)
def capability_names() -> tuple[str, ...]:
    """Capability names, in file order, from the routing file's `## ` headings.

    Raises if the file is missing or yields nothing. A registry generator that
    quietly emits zero capabilities looks like it succeeded while reclassifying
    every capability skill as a process skill -- exactly the silent corruption
    this function exists to make impossible.
    """
    if not ROUTING.is_file():
        raise SystemExit(f"missing routing file: {rel(ROUTING)}")
    text = ROUTING.read_text(encoding="utf-8", errors="ignore")
    names = tuple(m.group(1).strip().lower()
                  for m in re.finditer(r"^## +(\S+)\s*$", text, re.M))
    if not names:
        raise SystemExit(f"no `## <domain>` headings found in {rel(ROUTING)}")
    return names


def keywords_of(domain: str) -> list[str]:
    """The `Keywords:` line for one domain's section of the routing file."""
    text = ROUTING.read_text(encoding="utf-8", errors="ignore")
    for block in re.split(r"^## +", text, flags=re.M)[1:]:
        lines = block.splitlines()
        if lines and lines[0].strip().lower() == domain:
            m = re.search(r"^Keywords:\s*(.+)$", block, re.M | re.I)
            return [k.strip() for k in m.group(1).split(",") if k.strip()] if m else []
    return []


def capability_of(skill_name: str) -> str | None:
    """Owning capability, or None for a cross-cutting process skill."""
    if skill_name in PROCESS_OVERRIDES or "-" not in skill_name:
        return None
    prefix = skill_name.split("-", 1)[0]
    return prefix if prefix in capability_names() else None


def skill_dirs() -> list[Path]:
    d = CLAUDE / "skills"
    return sorted(p for p in d.iterdir() if p.is_dir()) if d.is_dir() else []


def build_capabilities() -> dict:
    caps = []
    all_skills = [p.name for p in skill_dirs()]
    for name in capability_names():
        entry = {
            "name": name,
            "path": rel(ROUTING),
            "keywords": keywords_of(name),
            # Every artefact type lives in a top-level .claude/ directory and is
            # grouped back to its capability by the `<domain>-` name prefix.
            "skills": [s for s in all_skills if capability_of(s) == name],
        }
        for kind in ARTEFACT_DIRS:
            entry[kind] = owned_artefacts(name, kind)
        caps.append(entry)
    return {"capabilities": caps}


ARTEFACT_DIRS = ("blueprints", "workflows", "validators", "playbooks", "templates")


def owned_artefacts(domain: str, kind: str) -> list[str]:
    d = CLAUDE / kind
    if not d.is_dir():
        return []
    return sorted(p.stem for p in d.iterdir()
                  if p.is_file() and p.stem.startswith(f"{domain}-")
                  and p.stem not in PROCESS_OVERRIDES)


def build_artefacts() -> dict:
    """Flat index of every non-skill artefact, with its owning capability."""
    out = []
    for kind in ARTEFACT_DIRS:
        d = CLAUDE / kind
        if not d.is_dir():
            continue
        for p in sorted(d.iterdir()):
            if not p.is_file():
                continue
            domain = p.stem.split("-", 1)[0]
            known = domain in capability_names()
            out.append({
                "name": p.stem,
                "kind": kind.rstrip("s"),
                "path": rel(p),
                "capability": domain if known else None,
            })
    return {"artefacts": out}


def build_skills() -> dict:
    skills = []
    for d in skill_dirs():
        fm = frontmatter(d / "SKILL.md")
        name = fm.get("name", d.name)
        skills.append({
            "name": name,
            "path": rel(d / "SKILL.md"),
            "kind": "capability" if capability_of(d.name) else "process",
            "capability": capability_of(d.name),
            # Claude Code only surfaces a skill whose frontmatter name matches its
            # directory. A mismatch makes it silently undiscoverable, so record it.
            "discoverable": bool(fm.get("description")) and name == d.name,
        })
    return {"skills": skills}


def build_agents() -> dict:
    agents = []
    agent_dir = CLAUDE / "agents"
    for path in sorted(agent_dir.glob("*.md")) if agent_dir.is_dir() else []:
        if path.name == "README.md":
            continue
        fm = frontmatter(path)
        agents.append({
            "name": fm.get("name", path.stem),
            "path": rel(path),
            # Discoverability is the thing worth recording: Claude Code only
            # loads an agent that has frontmatter. Without this field a reader
            # cannot tell a live agent from an inert markdown file.
            "discoverable": bool(fm.get("name") and fm.get("description")),
            "description": fm.get("description", ""),
        })
    return {"agents": agents}


def build_mcps() -> dict:
    """Documented MCP servers, cross-referenced against what is actually wired.

    `.claude/mcps/*.md` is documentation; `.mcp.json` is configuration. They are
    routinely out of step, and which is which is the useful signal -- so record
    both rather than letting one imply the other.
    """
    wired = set()
    mcp_json = ROOT / ".mcp.json"
    if mcp_json.exists():
        try:
            wired = set(json.loads(mcp_json.read_text(encoding="utf-8"))
                        .get("mcpServers", {}).keys())
        except Exception:
            pass

    entries = []
    mcp_dir = CLAUDE / "mcps"
    for path in sorted(mcp_dir.glob("*.md")) if mcp_dir.is_dir() else []:
        server = path.stem[:-4] if path.stem.endswith("-mcp") else path.stem
        entries.append({
            "name": path.stem,
            "server": server,
            "path": rel(path),
            "wired": server in wired,
        })

    documented = {e["server"] for e in entries}
    return {
        "mcps": entries,
        "wired_but_undocumented": sorted(wired - documented),
    }


def main() -> None:
    REGISTRY.mkdir(parents=True, exist_ok=True)
    written = {}
    for name, payload in (
        ("capabilities.json", build_capabilities()),
        ("skills.json", build_skills()),
        ("artefacts.json", build_artefacts()),
        ("agents.json", build_agents()),
        ("mcps.json", build_mcps()),
    ):
        (REGISTRY / name).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        key = next(iter(payload))
        written[name] = len(payload[key])
        print(f"wrote {rel(REGISTRY / name)} ({written[name]} entries)")

    try:
        runner = Path(__file__).resolve().parent / "run_hook.py"
        if runner.exists():
            subprocess.run(
                [sys.executable, str(runner), "on-artifact-create",
                 json.dumps({"event": "generate_registry", "written": written})],
                capture_output=True, timeout=60,
            )
    except Exception:
        pass


if __name__ == "__main__":
    main()
