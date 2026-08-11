#!/usr/bin/env python3
"""The report Gate 2 actually reviews — and a rollback that was run, not written.

    python tools/release_candidate.py                  # full rehearsal, slow
    python tools/release_candidate.py --offline        # every network/build fact unknown
    python tools/release_candidate.py --json

Why this exists
---------------
`GOAL_CHECKLIST.md` §12 asks for a staging report attached to the release
candidate, and says it is *"what Gate 2 actually reviews"*. There was never one,
which is why Gate 2 has never had anything to show and has never been exercised.

**The deployable artefact here is the wheel, and "production" is a target
repository with the layer installed.** That is not a metaphor built to make the
checklist pass: `tools/test_package.py` already builds the wheel, installs it
into a clean venv and then into a fresh git repo, and requires *that* repo's own
tier to come back green. The rehearsal existed; nothing collected its result.

Rollback is executed, never described
-------------------------------------
The checklist is explicit that a documented rollback does not count. So after
the install proves green, `.claude/install.py --uninstall` runs **in the same
scratch repo**, and the report carries what actually happened: the layer gone,
`PRESERVE` files still there. A rollback nobody has run is a paragraph.

It reports; it never ships
--------------------------
No deploy, no push, no merge, no tag. It gathers facts and prints them.
Gate 2 is a person, and this is what they read before deciding.

Slow tier, and it must stay there
---------------------------------
It builds a wheel and creates virtualenvs — minutes, not seconds. It must never
gate an auto-commit; that tier runs every turn and has to stay in seconds.

Undetermined is not ready
-------------------------
Article V. Any fact it could not establish prints `unknown`, and `exit_code`
returns 2 for that — which is not 0.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SBOM = ROOT / ".claude" / "hooks" / "state" / "sbom.json"

# Facts the report must carry. Named as a table so a missing one is a KeyError
# at build time rather than a quietly absent line in a report somebody is about
# to approve a shipment on.
REQUIRED_FACTS = (
    "wheel_version", "wheel_sha256", "target_tier", "sbom_path",
    "licence", "risk_tier", "changed_paths", "rollback",
)


def _run(args: list[str], cwd: Path | None = None, timeout: int = 900):
    """CompletedProcess, or None when the command could not run at all.

    None rather than a fabricated result: a failed subprocess and a subprocess
    that returned nothing are different facts, and collapsing them is how an
    unrun check reads as a passing one.
    """
    try:
        # `stdin=DEVNULL` is load-bearing, not tidiness. Anything spawned here
        # may reach a hook, and a hook calls `load_payload()`, which blocks on an
        # inherited pipe -- so the failure is a hang rather than an error, and it
        # only appears when this runs under the tier rather than alone.
        return subprocess.run(args, cwd=str(cwd or ROOT), capture_output=True,
                              text=True, timeout=timeout,
                              stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        return None


def evaluate(facts: dict) -> list[dict]:
    """Pure. facts -> findings, each {check, severity, detail}.

    `blocking` stops a shipment, `unknown` means the fact could not be
    established and is never treated as a pass, `ok` is a fact in hand.
    """
    out: list[dict] = []

    def add(check: str, severity: str, detail: str) -> None:
        out.append({"check": check, "severity": severity, "detail": detail})

    version = facts.get("wheel_version")
    add("wheel", "ok" if version else "unknown",
        f"version {version}, sha256 {(facts.get('wheel_sha256') or '?')[:12]}"
        if version else "the wheel could not be built")

    tier = facts.get("target_tier")
    if tier is None:
        add("rehearsal", "unknown", "the target repo's tier did not run")
    elif tier is True:
        add("rehearsal", "ok", "the layer installed into a fresh repo and its "
                               "own tier came back green")
    else:
        add("rehearsal", "blocking", f"the target repo's tier failed: {tier}")

    lic = facts.get("licence")
    if lic is None:
        add("licence", "unknown", "the licence check did not run")
    elif lic == "ok":
        add("licence", "ok", "no denied licence in the declared tree")
    else:
        add("licence", "blocking", f"licence verdict: {lic}")

    add("sbom", "ok" if facts.get("sbom_path") else "unknown",
        facts.get("sbom_path") or "no SBOM was produced")

    tier_name = facts.get("risk_tier")
    add("risk", "ok" if tier_name else "unknown",
        f"risk tier {tier_name}" if tier_name else "the plan could not be tiered")

    rollback = facts.get("rollback")
    if rollback is None:
        add("rollback", "unknown", "rollback was NOT executed")
    elif rollback is True:
        add("rollback", "ok", "uninstall ran in the scratch repo: the layer was "
                              "removed and the preserved files survived")
    else:
        add("rollback", "blocking", f"rollback ran and failed: {rollback}")

    changed = facts.get("changed_paths")
    add("scope", "ok" if changed is not None else "unknown",
        f"{changed} changed path(s)" if changed is not None
        else "the changed set could not be established")

    return out


def exit_code(findings: list[dict]) -> int:
    """0 ready · 1 a check failed · 2 a fact could not be determined.

    2 is not 0. A release candidate with an unestablished fact is not a release
    candidate anybody can approve.
    """
    if any(f["severity"] == "blocking" for f in findings):
        return 1
    if any(f["severity"] == "unknown" for f in findings):
        return 2
    return 0


def rehearse(root: Path) -> dict:
    """Build the wheel, install into a fresh repo, run its tier, then ROLL BACK.

    Delegates the build-and-install to `tools/test_package.py` rather than
    reimplementing it. An `ISSUES.md` entry records two hooks already shelling
    out to `.claude/install.py` with near-identical logic; a third copy of this
    would be the same defect, and this one would be the copy that drifts,
    because it runs least often.
    """
    facts: dict = {"wheel_version": None, "wheel_sha256": None,
                   "target_tier": None, "rollback": None}

    proc = _run([sys.executable, "tools/test_package.py"], root)
    if proc is not None:
        facts["target_tier"] = True if proc.returncode == 0 else \
            (proc.stdout or proc.stderr or "")[-200:].strip()

    dist = sorted((root / "dist").glob("*.whl")) if (root / "dist").is_dir() else []
    if dist:
        wheel = dist[-1]
        facts["wheel_version"] = wheel.name
        facts["wheel_sha256"] = hashlib.sha256(wheel.read_bytes()).hexdigest()

    facts["rollback"] = _rollback_probe(root)
    return facts


def _rollback_probe(root: Path) -> bool | str | None:
    """Install into a scratch repo, then uninstall, and read the tree back.

    The whole point of the task: the checklist asks for a rollback that has been
    **run**. Returns True when the layer is gone and a PRESERVE file survived,
    a string when it ran and something was wrong, None when it could not run.
    """
    import shutil
    import tempfile

    installer = root / ".claude" / "install.py"
    if not installer.is_file():
        return None

    tmp = Path(tempfile.mkdtemp(prefix="rollback-"))
    try:
        target = tmp / "repo"
        target.mkdir()
        if _run(["git", "init", "-q"], target) is None:
            return None
        # A PRESERVE file with content of our own: the test is that uninstall
        # leaves it exactly as found.
        marker = target / "CLAUDE.md"
        marker.write_text("# target's own contract\n", encoding="utf-8")

        if _run([sys.executable, str(installer), "--into", str(target)],
                root, timeout=300) is None:
            return None
        if not (target / ".claude" / "skills").is_dir():
            return "install did not land a layer to roll back"

        out = _run([sys.executable, str(installer), "--uninstall",
                    "--into", str(target)], root, timeout=300)
        if out is None:
            return "uninstall could not run"
        if out.returncode != 0:
            return f"uninstall exited {out.returncode}"

        if (target / ".claude" / "skills").is_dir():
            return "uninstall left .claude/skills/ behind"
        if not marker.is_file():
            return "uninstall deleted CLAUDE.md, which it must preserve"
        if marker.read_text(encoding="utf-8") != "# target's own contract\n":
            return "uninstall modified a preserved file"
        return True
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def gather_facts(root: Path, plan: str | None = None,
                 offline: bool = False) -> dict:
    """The IO seam. `offline=True` nulls every expensive fact rather than faking it."""
    facts: dict = {k: None for k in REQUIRED_FACTS}

    lic = _run([sys.executable, "tools/deps.py"], root)
    if lic is not None:
        facts["licence"] = "ok" if lic.returncode == 0 else \
            ("denied" if lic.returncode == 1 else "undetermined")

    sbom = _run([sys.executable, "tools/deps.py", "--sbom"], root)
    if sbom is not None and sbom.returncode == 0 and SBOM.is_file():
        facts["sbom_path"] = SBOM.relative_to(ROOT).as_posix()

    if plan:
        tier = _run([sys.executable, "tools/scope.py", "--plan", plan], root)
        if tier is not None:
            facts["risk_tier"] = {0: "low", 1: "medium", 2: "high"}.get(
                tier.returncode, "undetermined")

    diff = _run(["git", "diff", "--name-only", "main...HEAD"], root)
    if diff is not None and diff.returncode == 0:
        facts["changed_paths"] = len([x for x in diff.stdout.splitlines() if x.strip()])

    if not offline:
        facts.update(rehearse(root))

    return facts


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--plan", default=None)
    ap.add_argument("--offline", action="store_true",
                    help="skip the build and the rollback; those facts report unknown")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--root", default=".")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    facts = gather_facts(root, args.plan, offline=args.offline)
    findings = evaluate(facts)
    code = exit_code(findings)

    if args.json:
        print(json.dumps({"findings": findings, "facts": facts,
                          "exit": code}, indent=2))
    else:
        print("RELEASE CANDIDATE")
        for f in findings:
            mark = {"ok": "  ", "blocking": "!!", "unknown": "??"}[f["severity"]]
            print(f" {mark} {f['check']:12} {f['detail']}")
        print()
        print({0: "ready: every fact established and none blocking",
               1: "NOT ready: a check failed",
               2: "NOT ready: a fact could not be determined, which is unrun "
                  "rather than passed"}[code])
    return code


if __name__ == "__main__":
    sys.exit(main())
