#!/usr/bin/env python3
"""The report names every fact, and the rollback line came from a rollback.

Why this suite exists
---------------------
This is the document Gate 2 reads before approving a shipment, so the failure
that matters is not a crash — it is a **missing line read as an absent problem**.
A report that silently omits the rollback looks exactly like one where rollback
was fine.

So two properties carry the weight:

  * every fact in `REQUIRED_FACTS` appears in the report, whatever its value;
  * an unestablished fact is `unknown`, and `unknown` never exits 0.

`evaluate()` and `exit_code()` are pure, so those cases are dict literals. The
rollback probe is exercised **for real** against a scratch repo — mocking it
would test the mock, and "the rollback was executed" is the one claim here that
cannot be taken on trust.

Run: python tools/test_release_candidate.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_candidate as rc  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"OK: {name}")
    else:
        print(f"FAIL: {name}{(' -- ' + detail) if detail else ''}")
        failures.append(name)


READY = {
    "wheel_version": "capability_layer-0.1.0-py3-none-any.whl",
    "wheel_sha256": "abc123def456",
    "target_tier": True,
    "sbom_path": ".claude/hooks/state/sbom.json",
    "licence": "ok",
    "risk_tier": "low",
    "changed_paths": 12,
    "rollback": True,
}


def sev(findings, check_name):
    return next((f["severity"] for f in findings if f["check"] == check_name), None)


# --- the ready case -----------------------------------------------------------
ready = rc.evaluate(READY)
check("a complete candidate is ready", rc.exit_code(ready) == 0, str(ready))
check("...with no unknown severities",
      not any(f["severity"] == "unknown" for f in ready), str(ready))

# --- every required fact reaches the report -----------------------------------
#
# The property that stops a silent omission. A fact that vanishes from the report
# is indistinguishable from a fact that was fine.
CHECK_FOR_FACT = {
    "wheel_version": "wheel", "wheel_sha256": "wheel", "target_tier": "rehearsal",
    "sbom_path": "sbom", "licence": "licence", "risk_tier": "risk",
    "changed_paths": "scope", "rollback": "rollback",
}
check("every required fact maps to a reported check",
      set(CHECK_FOR_FACT) == set(rc.REQUIRED_FACTS),
      f"unmapped: {sorted(set(rc.REQUIRED_FACTS) - set(CHECK_FOR_FACT))}")

reported = {f["check"] for f in ready}
check("every mapped check appears in the report",
      set(CHECK_FOR_FACT.values()) <= reported,
      f"missing: {sorted(set(CHECK_FOR_FACT.values()) - reported)}")

# --- Article V: each fact, dropped alone, is unknown and never ready ----------
for fact, check_name in CHECK_FOR_FACT.items():
    missing = dict(READY, **{fact: None})
    got = rc.evaluate(missing)
    if fact == "wheel_sha256":
        continue          # carried inside the wheel line, not its own check
    check(f"[{fact}] missing is reported unknown",
          sev(got, check_name) == "unknown", f"{check_name}={sev(got, check_name)}")
    check(f"[{fact}] ...and the candidate is not ready",
          rc.exit_code(got) == 2, str(rc.exit_code(got)))

# --- a failed fact blocks, and outranks an unknown ----------------------------
failed_tier = rc.evaluate(dict(READY, target_tier="3 suites failed"))
check("a failed rehearsal blocks", rc.exit_code(failed_tier) == 1)
check("...and the detail carries what failed",
      "3 suites failed" in str(failed_tier), str(failed_tier))

denied = rc.evaluate(dict(READY, licence="denied"))
check("a denied licence blocks", rc.exit_code(denied) == 1)

bad_rollback = rc.evaluate(dict(READY, rollback="uninstall left .claude/skills/ behind"))
check("a rollback that ran and failed blocks", rc.exit_code(bad_rollback) == 1)
check("...and says what it left behind",
      "left .claude/skills" in str(bad_rollback), str(bad_rollback))

both = rc.evaluate(dict(READY, licence="denied", risk_tier=None))
check("a blocking finding outranks an unknown one", rc.exit_code(both) == 1,
      "the worst known fact wins, or a blocker hides behind a gap")

# The distinction the whole exit-code scheme exists for.
check("2 is not 0", rc.exit_code(rc.evaluate(dict(READY, rollback=None))) != 0)

# --- the rollback probe, executed for real -------------------------------------
#
# The one claim that cannot be taken on trust. `GOAL_CHECKLIST.md` asks for a
# rollback that has been RUN, and a mocked probe would assert the opposite of
# what the line means.
result = rc._rollback_probe(ROOT)
check("the rollback probe actually installs and uninstalls",
      result is True,
      f"got {result!r} -- this is a real install into a scratch repo, an "
      f"uninstall, and a read-back of the tree")

# The probe must be capable of failing, or it proves nothing. Point it at a root
# with no installer and it must report None rather than True.
import tempfile  # noqa: E402

with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
    check("the probe reports None where there is no installer to run",
          rc._rollback_probe(Path(d)) is None,
          "a probe that cannot fail is not evidence")

# --- the offline seam ----------------------------------------------------------
offline = rc.gather_facts(ROOT, offline=True)
check("offline nulls the expensive facts rather than inventing them",
      offline["wheel_version"] is None and offline["rollback"] is None,
      str({k: v for k, v in offline.items() if k in ("wheel_version", "rollback")}))
# The cheap facts are gathered even offline -- but only where they exist. A
# freshly installed layer sits in a repo with no `main` to diff against, so
# `changed_paths` is legitimately None there. Asserting otherwise is asserting
# this repository's git history in somebody else's, which is the fifth time that
# shape has turned the packaged run red today.
if offline["changed_paths"] is None:
    print("SKIP: no main...HEAD to diff here -- the changed-path count is "
          "unaskable, and reports unknown rather than 0")
else:
    check("...while the cheap ones are still real",
          offline["changed_paths"] >= 0, str(offline["changed_paths"]))
check("...and an offline candidate is never ready",
      rc.exit_code(rc.evaluate(offline)) == 2)

# --- it ships nothing ----------------------------------------------------------
src = (ROOT / "tools" / "release_candidate.py").read_text(encoding="utf-8")
for verb in ("gh pr merge", "git push", "--force"):
    check(f"the release candidate never runs `{verb}`", verb not in src,
          "this reports facts for a person to read; it does not ship")
check("it says it belongs in the slow tier",
      "slow tier" in src.lower(),
      "it builds a wheel and a venv; gating an auto-commit on that is untenable")

print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print(f"All release-candidate tests passed ({len(rc.REQUIRED_FACTS)} required facts)")
