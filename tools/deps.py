#!/usr/bin/env python3
"""What are we shipping, and is any of it a licence we cannot take?

    python tools/deps.py                 # licence verdict for declared dependencies
    python tools/deps.py --sbom          # write the SBOM
    python tools/deps.py --json

Two checklist lines with nothing behind them
--------------------------------------------
`pip-audit` covers *vulnerabilities* in the declared tree. Nothing has ever
checked a **licence**, and no SBOM has ever been produced — so "what is in this
artefact, and may we ship it" had no answer at all.

A denylist, not an allowlist
----------------------------
Strong-copyleft licences fail; everything else passes **except** a licence that
could not be determined, which is reported as `unknown` and is not a pass.
Article V of `.claude/constitution.md`: a check that could not run is unrun.

An allowlist was rejected. It is the safer-sounding shape and the wrong one here:
the first unlisted-but-fine licence turns the gate red, somebody adds a blanket
exception to get moving, and the exception outlives the reason. A denylist names
the small set that actually blocks and treats the unknown honestly.

Reads metadata, never the network
---------------------------------
`importlib.metadata` resolves what is installed — stdlib, no new dependency, no
network call, and it reports what is *actually present* rather than what a
lockfile says should be. A dependency declared but not installed is named as
`not-installed` rather than silently dropped.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SBOM_PATH = ROOT / ".claude" / "hooks" / "state" / "sbom.json"

# Licences that block. Strong copyleft on a distributed artefact obliges source
# release under the same terms, and this layer is installed into other people's
# private repositories -- which is exactly the case those licences are designed
# to reach. AGPL is listed separately from GPL because its network clause
# catches deployments that never distribute a binary at all.
#
# LGPL is deliberately ABSENT: it permits linking without that obligation, and
# blocking it would be the over-broad rule that gets a blanket exception added.
DENIED = {
    "AGPL": "network-copyleft: obliges source release to anyone served by it",
    "GPL": "strong copyleft: obliges source release for the whole work",
    "SSPL": "server-side public licence: obliges releasing the service stack",
    "BUSL": "business source licence: not open source until its change date",
    "CC-BY-NC": "non-commercial: forbids the commercial use this is installed for",
}

# Matching a denied name is fiddlier than it looks and both traps are live:
#
#   `"GPL" in "LGPL-2.1"`   -> True, and LGPL is permitted. A substring match
#                              blocks a legitimate dependency.
#   tokenising on `-`       -> `AGPL-3.0` stays one token, so `AGPL` never
#                              matches its own entry and nothing blocks at all.
#                              (That was the first implementation, and every
#                              denied family silently passed.)
#
# So: match the denied name where it is not flanked by another LETTER. `GPL`
# inside `LGPL` is preceded by `L` and does not match; `GPL-3.0` and `AGPL-3.0`
# both match their own entries, because a digit or hyphen is a boundary and a
# letter is not.
def _denies(licence: str, key: str) -> bool:
    return re.search(rf"(?<![A-Za-z]){re.escape(key)}(?![A-Za-z])",
                     licence, re.I) is not None


def declared(root: Path | None = None) -> list[str]:
    """Distribution names from `pyproject.toml`'s runtime dependencies.

    Runtime only. Dev extras are not shipped to anybody, so their licences are
    not this repository's problem to answer for.
    """
    root = Path(root or ROOT)
    text = (root / "pyproject.toml").read_text(encoding="utf-8") \
        if (root / "pyproject.toml").is_file() else ""
    m = re.search(r"(?ms)^dependencies\s*=\s*\[(.*?)\]", text)
    if not m:
        return []
    names = []
    for raw in re.findall(r"[\"']([^\"']+)[\"']", m.group(1)):
        name = re.split(r"[<>=!~\[; ]", raw.strip(), maxsplit=1)[0].strip()
        if name:
            names.append(name)
    return sorted(set(names))


def licence_of(name: str) -> tuple[str | None, str]:
    """(licence, source) for an installed distribution. (None, reason) if unknown.

    Three places carry it and they disagree in practice, so all three are tried
    in order of specificity: the SPDX `License-Expression` field, then the
    `License ::` classifiers, then the free-text `License` field which is often
    a paragraph rather than a name.
    """
    try:
        import importlib.metadata as md
        dist = md.distribution(name)
    except Exception:
        return None, "not-installed"

    # `PackageMetadata` is an `email.Message` at runtime and carries `.get` and
    # `.get_all`, but typeshed's protocol declares neither. Cast rather than
    # restructure: the runtime behaviour is the documented one, and working
    # around the stub would mean parsing the metadata by hand.
    meta: Any = dist.metadata
    expr = meta.get("License-Expression")
    if expr and expr.strip():
        return expr.strip(), "License-Expression"

    classifiers = [c for c in (meta.get_all("Classifier") or [])
                   if c.startswith("License ::")]
    if classifiers:
        # `License :: OSI Approved :: MIT License` -> `MIT License`
        return classifiers[0].split("::")[-1].strip(), "classifier"

    free = (meta.get("License") or "").strip()
    if free and len(free) < 64 and "\n" not in free:
        return free, "License"
    if free:
        return None, "License field is prose, not a name"
    return None, "no licence metadata"


def verdict(entries: list[dict]) -> dict:
    """Pure. Entries -> {status, denied, unknown, reason}.

    `status` is `ok`, `denied` or `undetermined`. Undetermined is never `ok`:
    a licence nobody could read is not a licence anybody cleared.
    """
    denied, unknown = [], []
    for entry in entries:
        lic = entry.get("licence")
        if not lic:
            unknown.append(entry)
            continue
        hit = next((d for d in DENIED if _denies(lic, d)), None)
        if hit:
            denied.append({**entry, "why": DENIED[hit]})

    if denied:
        return {"status": "denied", "denied": denied, "unknown": unknown,
                "reason": "; ".join(f"{d['name']} is {d['licence']} -- {d['why']}"
                                    for d in denied)}
    if unknown:
        return {"status": "undetermined", "denied": [], "unknown": unknown,
                "reason": "could not determine a licence for: "
                          + ", ".join(f"{u['name']} ({u['source']})" for u in unknown)}
    return {"status": "ok", "denied": [], "unknown": [],
            "reason": f"{len(entries)} declared dependency(ies), none denied"}


def gather(root: Path | None = None) -> list[dict]:
    """The IO seam: one entry per declared runtime dependency."""
    out = []
    for name in declared(root):
        lic, source = licence_of(name)
        try:
            import importlib.metadata as md
            version = md.version(name)
        except Exception:
            version = None
        out.append({"name": name, "version": version,
                    "licence": lic, "source": source})
    return out


def sbom(entries: list[dict]) -> dict:
    """A CycloneDX-shaped document. Deliberately minimal and honest.

    Not a certified generator: it records what this repository declares and what
    is installed to satisfy it. A component whose licence is unknown carries no
    `licenses` key rather than an empty one, so a consumer cannot read absence as
    permissive.
    """
    components = []
    for e in entries:
        comp = {"type": "library", "name": e["name"],
                "version": e["version"] or "unknown",
                "purl": f"pkg:pypi/{e['name']}@{e['version'] or 'unknown'}"}
        if e["licence"]:
            comp["licenses"] = [{"license": {"name": e["licence"]}}]
        components.append(comp)
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {"component": {"type": "application",
                                   "name": "capability-layer"}},
        "components": components,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sbom", action="store_true", help="write the SBOM and exit")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--root", default=".")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    entries = gather(root)

    if args.sbom:
        doc = sbom(entries)
        SBOM_PATH.parent.mkdir(parents=True, exist_ok=True)
        SBOM_PATH.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        print(f"{SBOM_PATH.relative_to(ROOT).as_posix()}: "
              f"{len(doc['components'])} component(s)")
        return 0

    result = verdict(entries)
    if args.json:
        print(json.dumps({**result, "entries": entries}, indent=2))
    else:
        for e in entries:
            print(f"  {e['name']:20} {e['version'] or '-':10} "
                  f"{e['licence'] or 'UNKNOWN':28} ({e['source']})")
        print(f"\nlicences: {result['status']}  --  {result['reason']}")

    # 0 ok · 1 denied · 2 undetermined. Undetermined is not ok.
    return {"ok": 0, "denied": 1}.get(result["status"], 2)


if __name__ == "__main__":
    sys.exit(main())
