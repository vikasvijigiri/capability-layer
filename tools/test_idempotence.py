#!/usr/bin/env python3
"""Objective 19 (idempotent and repeatable) -- second-run delta over a fixture.

"repeated execution converges without duplicating work, corrupting artifacts
or introducing inconsistency." Two independent proofs, both extending
`tools/test_install.py`'s fixture machinery per `docs/specs/2026-08-21-
qualitative-objective-metrics.md`'s Cluster B design. Report only: exits 0
unconditionally, per that spec's "report before gate" constraint -- gating is
a follow-up unit, after a baseline exists.

  (a) Install into a fixture target twice; hash every file after each install
      and report the fraction unchanged between the two. Stronger than
      `test_install.py`'s existing "a second plan rewrites nothing" check,
      which only asserts the ACTION LIST has no create/overwrite entries --
      this hashes the tree itself. Grounded in Ansible Molecule's
      `idempotence` step: "The second run should normally end with
      `changed=0`." (https://docs.ansible.com/projects/molecule/workflow/)

  (b) Fire a curated set of STATELESS decision hooks (`pre-edit`,
      `permission-security`, `pre-tool`) twice each with an identical
      payload against this repository itself, and assert the decision
      (exit code + ALLOW/DENY verdict) is identical both times. Reuses
      `tools/test_hooks.py`'s own `run_hook()` pattern and its
      runtime-assembled planted-secret construction, so this file never
      itself becomes an uncommittable credential.

Deliberately excludes the accumulative counter hooks (`01-context-cost.py`,
`02-skill-cost.py`, `04-read-cost.py`, `05-agent-cost.py`, `06-tool-cost.py`,
`07-human-cost.py`, `02-turn-timer.py`, `01-entry-classifier.py`'s
`ENTRY_SHAPE_STATE`) -- confirmed this session by grepping every
`STATE = Path(...)` assignment under `.claude/hooks/{context-budget,post-tool,
prompt-intake}/*.py`: every one of them is a counter or a history that a
second identical fire is SUPPOSED to change (a call count, a cumulative char
total, a turn timestamp). The spec's own caveat names exactly this class as
excluded ("a second fire must change them"). The three hooks fired here are
confirmed, by the same grep, to write no state file at all -- pure functions
of the payload and current repo state.

Real finding, not seeded (found by running (a), not by reading the spec):
`.claude/layer-manifest.json` itself is NOT stable across a repeat install.
`install.py:plan()` gives every SEED file (`ruff.toml`, `mypy.ini`,
`.github/workflows/checks.yml`, `CODEOWNERS`) a `"preserve"` action once it
already exists on disk -- correct, its bytes must not be touched -- but
`write_manifest()`'s owned-path filter only keeps actions in `("create",
"overwrite", "unchanged", "create-stub", "create-claude-stub", "merge")`,
which does not include `"preserve"`. So all four SEED files silently drop out
of the manifest's `paths`/`files` on the SECOND install, even though nothing
about them changed on disk. Confirmed directly (not just via the ratio) by
enumerating `inst.SEED` membership in `_layer_owned()` before and after a
second install: 4/4 present after install 1, 0/4 after install 2. This does
not corrupt `uninstall` (SEED is separately protected by name in
`uninstall_plan`, independent of manifest membership) or `upgrade` (SEED
files never receive an `"overwrite"` action, so upgrade's hash comparison
never runs against them) -- but the manifest IS a derived artifact whose
byte content depends on install-run-count, which is exactly the
"introducing inconsistency" objective 19 asks a check to catch. Recording
here, not fixing: repairing `write_manifest()` changes `install.py`'s own
behavior, a different and riskier change than building a detector, mirroring
Cluster D's Task 4 precedent for a found-not-fixed bug.

Run: python tools/test_idempotence.py
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


# `fresh_repo()` and `load()` are duplicated from `tools/test_install.py`
# rather than imported from it: that file is a top-level script whose import
# executes its entire ~930-assertion suite as a side effect, so it cannot be
# used as a library. Same accepted exception as this repo's own `_load()`
# duplication across 10 files (`docs/plans/2026-08-20-router-progress-
# consistency.md`'s Grounding).
def load(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    assert spec is not None and spec.loader is not None, f"cannot load {rel}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def fresh_repo() -> Path:
    d = Path(tempfile.mkdtemp()) / "target"
    d.mkdir()
    for args in (["init", "--quiet"],
                 ["config", "user.email", "t@example.com"],
                 ["config", "user.name", "t"]):
        subprocess.run(["git", *args], cwd=str(d), capture_output=True, text=True)
    return d


def snapshot(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        if rel.startswith(".git/"):
            continue
        out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def install_delta_ratio(before: dict[str, str],
                         after: dict[str, str]) -> tuple[float, list[str]]:
    """Fraction of `before` paths whose hash is unchanged in `after`.

    Pure function so the seeded-violation proof below needs no filesystem
    mutation to set up or revert -- only synthetic dicts.
    """
    if not before:
        return 1.0, []
    changed = sorted(p for p, h in before.items() if after.get(p) != h)
    ratio = (len(before) - len(changed)) / len(before)
    return ratio, changed


def run_hook(event: str, payload: dict) -> subprocess.CompletedProcess:
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                      encoding="utf-8") as f:
        json.dump(payload, f)
        path = f.name
    try:
        return subprocess.run(
            [PY, str(ROOT / "tools" / "run_hook.py"), event, "--file", path],
            capture_output=True, text=True, cwd=str(ROOT),
            stdin=subprocess.DEVNULL)
    finally:
        Path(path).unlink(missing_ok=True)


def decision_of(proc: subprocess.CompletedProcess) -> str:
    if '"permissionDecision": "deny"' in proc.stdout:
        return "deny"
    if '"permissionDecision": "allow"' in proc.stdout:
        return "allow"
    return f"exit={proc.returncode}"


DECISION_CASES: list[tuple[str, dict]] = [
    ("pre-edit", {"tool_name": "Write", "tool_input": {"file_path": "README.md"}}),
    ("permission-security", {"files": ["requirements.txt"]}),
    ("pre-tool", {"tool_name": "Bash", "tool_input": {"command": "echo hello"}}),
]


def main() -> int:
    findings: list[str] = []

    # --- (a) install into a fixture target twice, diff byte-for-byte -------
    inst = load(".claude/install.py", "install_mod_idempotence")
    target = fresh_repo()
    (target / "src").mkdir()
    (target / "src" / "app.py").write_text("def main():\n    return 1\n",
                                            encoding="utf-8")

    first_actions, _ = inst.plan(target)
    inst.apply(target, first_actions)
    first_snapshot = snapshot(target)

    second_actions, _ = inst.plan(target)
    inst.apply(target, second_actions)
    second_snapshot = snapshot(target)

    ratio, changed = install_delta_ratio(first_snapshot, second_snapshot)
    print(f"objective 19a (install-twice tree delta): "
          f"{len(first_snapshot) - len(changed)}/{len(first_snapshot)} "
          f"unchanged ({ratio:.4f})")
    for path in changed:
        findings.append(f"  changed on 2nd install: {path}")

    shutil.rmtree(target.parent, ignore_errors=True)

    # Proof the ratio arithmetic itself can fail before it is trusted --
    # entirely synthetic, no filesystem mutation to revert (the spec's
    # "Testing the instruments themselves" rule).
    _seed_before = {"a.txt": "hash-a", "b.txt": "hash-b", "c.txt": "hash-c"}
    _seed_after = {"a.txt": "hash-a", "b.txt": "DIFFERENT", "c.txt": "hash-c"}
    _seed_ratio, _seed_changed = install_delta_ratio(_seed_before, _seed_after)
    assert abs(_seed_ratio - (2 / 3)) < 1e-9 and _seed_changed == ["b.txt"], (
        f"install_delta_ratio() failed to flag a seeded change: "
        f"ratio={_seed_ratio}, changed={_seed_changed}")
    print("  self-check: install_delta_ratio() correctly flags a seeded "
          "byte change (b.txt, ratio=0.6667) -- proven before trusting it "
          "against the real installer above")

    # --- (b) fire stateless decision hooks twice, diff the decision --------
    case_results = []
    for event, payload in DECISION_CASES:
        p1 = run_hook(event, payload)
        p2 = run_hook(event, payload)
        same = p1.returncode == p2.returncode and decision_of(p1) == decision_of(p2)
        case_results.append((event, same, p1, p2))
        if not same:
            findings.append(
                f"  {event} decision differs across two identical firings: "
                f"run1=({p1.returncode},{decision_of(p1)}) "
                f"run2=({p2.returncode},{decision_of(p2)})")

    PLANTED_KEY = "AKIA" + "ABCDEFGHIJKLMNOP"  # runtime-assembled, see docstring
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                      encoding="utf-8", dir=str(ROOT)) as f:
        f.write(f'aws_key = "{PLANTED_KEY}"\n')
        secret_file = Path(f.name)
    try:
        rel = secret_file.relative_to(ROOT).as_posix()
        p1 = run_hook("permission-security", {"files": [rel]})
        p2 = run_hook("permission-security", {"files": [rel]})
        same = (p1.returncode == p2.returncode
                and decision_of(p1) == decision_of(p2) == "deny")
        case_results.append(("permission-security (DENY)", same, p1, p2))
        if not same:
            findings.append(
                f"  permission-security DENY decision differs across two "
                f"identical firings: run1=({p1.returncode},{decision_of(p1)}) "
                f"run2=({p2.returncode},{decision_of(p2)})")
    finally:
        secret_file.unlink(missing_ok=True)

    ok_count = sum(1 for _, same, _, _ in case_results if same)
    print(f"objective 19b (decision-hook determinism): "
          f"{ok_count}/{len(case_results)} identical across two firings")
    for event, same, _p1, _p2 in case_results:
        print(f"  {'OK' if same else 'DIFFERS'}: {event}")

    if findings:
        print("\nFindings:")
        for finding in findings:
            print(finding)

    print("\nReport only -- exits 0 regardless, per 'report before gate'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
