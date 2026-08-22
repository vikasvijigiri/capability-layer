"""stop-finalization -- commits this turn's work automatically, as a small local checkpoint.

Authorised by the user on 2026-08-02, widened from prose-only to all changed
files on the same day after the trade below was stated explicitly. Do not widen
it further -- to pushing, to protected branches -- without asking again.

Why this exists
---------------
This repo accumulated 91 uncommitted files across five sessions while 28 hooks
fired correctly, because every gate asked the model to act instead of acting.
The fix is not a bigger gate; it is a commit boundary that arrives on its own.

`pre-commit/03-review-gate.py` was the opposite approach -- ask a human on every
commit -- and it deadlocked and was deleted. Its replacement is this: commits are
cheap local checkpoints that nobody reviews, and **the review moves to the push
or the PR**, which is the boundary the user actually cares about. A commit that
needs a human is not a small commit; it is an expensive one, and expensive
commits are why the backlog grew.

What gates a checkpoint
-----------------------
Artefact facts, never process compliance -- the principle five comparable repos
converge on (stripe, rstudio, crowd.dev, claudekit, superpowers: every hook in
all of them verifies an artefact; not one enforces process).

  1. Something changed.
  2. The branch is not protected.
  3. No changed file matches a credential pattern.
  4. The repo's own suites pass.
  5. The change is small enough to still be a checkpoint.

Every clause is falsifiable. A failure refuses the commit and says so; nothing
is ever committed silently on a red suite.

Deliberately bypassed gates, and how that is covered
----------------------------------------------------
A commit made from this subprocess does not pass through `PreToolUse`, so
`01-secret-scan.py`, `02-branch-guard.py` and `01-forbidden-change-guard.py`
never see it. When the scope was prose that was tolerable. It is not tolerable
for code, so the two load-bearing checks are enforced *inline* here, from the
same `_hooklib` definitions those hooks use -- one rule, two enforcement points,
no second copy to drift.

Never pushes. Never `git add .`; always an explicit pathspec, so it cannot sweep
files somebody else staged. Never raises, never blocks the turn.

Message shape
-------------
`wip:` prefixed, deliberately. These are checkpoints, not curated history: the
hook can count files but cannot know why they changed. Squash-merging the branch
at PR time collapses them into the one message a human writes, so the noise has
a defined end. A checkpoint that pretended to be a real commit message would be
worse -- it would look reviewed.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _hooklib import (  # noqa: E402
    AI_ATTRIBUTION_PATTERNS,
    KNOWLEDGE_DOCS,
    PROTECTED_BRANCHES,
    changed_paths,
    classify_failure,
    current_branch,
    declaration_sources,
    declared_paths,
    failure_budget,
    failure_signature,
    load_payload,
    migration_paths,
    minimal_diff_refusal,
    scan_for_secrets,
)
from _projectchecks import (  # noqa: E402
    CONFIG_NAME,
    changed_includes_code,
    load_config,
    run_checks,
)

REPO_ROOT = Path(__file__).resolve().parents[3]

# Above this, the turn stopped being a checkpoint and became a unit of work
# somebody should look at before it is written down as one commit. Refusing is
# the safe direction: the files stay in the working tree and `03-checkpoint.py`
# has already snapshotted them, so nothing is at risk either way.
#
# Overridable via `max_files` in .claude/project-checks.json, because a scaffold
# -- `create-next-app` and friends -- is legitimately hundreds of files on its
# first commit. Raising it is a decision someone types, not a default that drifts.
DEFAULT_MAX_FILES = 25

# Paths never committed automatically, whatever else is true. `settings.json`
# decides what fires; committing a change to it unattended means the mechanism
# that governs this hook was altered without anyone reading the diff.
NEVER_AUTO = (".claude/settings.json", ".claude/settings.local.json")

# Re-entry guard. Anything that fires the whole `post-run` event reaches this
# hook, which runs this project's checks; if one of those checks in turn fires the
# event, the recursion is unbounded and presents as a hang, not an error. A test
# suite doing exactly that found it on 2026-08-02, by timing out at two minutes.
#
# The suite is gone but the guard is not, and must not be: any check command a
# project configures can reach this hook the same way, and the failure is silent
# until it hangs.
#
# It does double duty: a check run must never produce a real commit either, and
# any invocation carrying this flag is by definition running underneath one.
REENTRY_FLAG = "UAIOS_AUTOCOMMIT_RUNNING"

# --- the diagnose loop --------------------------------------------------------
#
# When the checks are red this hook already refuses and says why. That is where
# the information stops, and the next turn starts from prose in a scrollback.
#
# So: write the failing output to a file, count consecutive failures of the SAME
# failure, and name the skill whose stated trigger this is. A hook cannot invoke
# a skill -- the official hooks reference lists command/http/mcp_tool/prompt/agent
# as the handler types and no skill among them -- so this is a signal, never a
# trigger.
#
# It deliberately does NOT block. `post-run/05-docs-gate.py` blocked a turn until
# a skill ran, deadlocked, and was deleted on 2026-08-02. Write, suggest, get out
# of the way.
#
# MAX_ATTEMPTS exists because a loop without a termination criterion does not
# terminate -- `executing-plans` states the same rule for its own loop mode.
# Three attempts at the SAME failure and it stops suggesting and escalates,
# because a fix that has not converged in three passes is not converging.
# Names, not paths. Derived from REPO_ROOT at CALL time, never baked at import:
# the suites override `REPO_ROOT` to a temp repo, and a module-level absolute
# path would keep pointing at the real one -- so a test run would quietly write
# its failure report into the developer's actual repository. Caught 2026-08-03
# by a ValueError that was the lesser symptom.
FAILURE_STATE_NAME = "check-failures.json"
FAILURE_REPORT_NAME = "check-failure-report.md"
MAX_ATTEMPTS = 3

# What to do about each class, in the report, where the next turn will read it.
# The wrong remedy is worse than none: editing product code to chase a locked
# file changes working code for a fault that is not in it.
REMEDY_NOTE = {
    "transient": "This looks like infrastructure, not the change. Rerun the exact "
                 "command. Do NOT edit product code. If the output is not "
                 "byte-identical on the retry, it was never transient.",
    "deterministic": "This is a real defect. Reproduce it, find the root cause, "
                     "make the smallest change that addresses it, rerun the "
                     "focused check, then the tier.",
    "merge": "Fetch the current target and rebase onto it. Resolve only "
             "mechanical conflicts; anything touching public API, migrations, "
             "auth or business logic goes back to plan approval.",
    "security": "Not auto-repairable and not retryable. Stop, remove the "
                "credential or address the finding, and rerun the security check.",
    "unknown": "No rule matched this output. Treat it as a real defect, and once "
               "the cause is known add a row to `_hooklib.FAILURE_CLASSES` so the "
               "next occurrence is classified.",
}


def _state_dir() -> Path:
    return REPO_ROOT / ".claude" / "hooks" / "state"


def git(*args):
    """Run git and return (rc, stdout, stderr). Never raises."""
    try:
        proc = subprocess.run(
            ["git", *args], cwd=str(REPO_ROOT),
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=60,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except Exception as exc:  # noqa: BLE001 -- reported below, never swallowed
        return 1, "", str(exc)


def speak(text: str) -> None:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "Stop",
        "additionalContext": text,
    }}))


def run_suites():
    """(ok, detail, ran_test) for whatever this project's checks are.

    Delegates to `_projectchecks`, which detects `npm test`, `tsc --noEmit`,
    `pytest`, `cargo test` and so on from marker files, and lets
    `.claude/project-checks.json` override any of them. Until 2026-08-02 this
    function hardcoded one repo's own Python suites, which would have found
    nothing at all in a web app and reported "nothing to verify" on every commit.

    In this capability repo it resolves to the configured lint, typecheck, and
    standalone contract-test commands. A project without test markers or an
    explicit test command still returns `ran_test=False`, which keeps the
    unverified-code gate honest rather than pretending that no test was a pass.
    """
    return run_checks(REPO_ROOT, extra_env={REENTRY_FLAG: "1"})


# Kept as a name here because the suites call it, but there is one definition and
# it is in `_hooklib` -- `tools/loop.py` needs the identical key, and two copies
# would diverge on the copy that decides when to give up.
_failure_signature = failure_signature


def _load_failures() -> dict:
    try:
        return json.loads(
            (_state_dir() / FAILURE_STATE_NAME).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _record_failure(detail: str, paths) -> int:
    """Write the report, bump the counter, return the attempt number.

    The class is recorded alongside the count so the next turn knows what kind
    of failure it is looking at without re-deriving it, and so the report says
    which remedy applies -- retrying a real defect and repairing a network blip
    are both wasted turns, and they look identical in the raw output.
    """
    signature = _failure_signature(detail)
    kind, action = classify_failure(detail)
    budget = failure_budget(kind)
    state = _load_failures()
    # Only the current signature is kept: a different failure means the previous
    # one was resolved or replaced, and its count is no longer meaningful.
    attempt = (state.get(signature, 0) if state.get("signature") == signature
               else 0) + 1
    try:
        _state_dir().mkdir(parents=True, exist_ok=True)
        (_state_dir() / FAILURE_STATE_NAME).write_text(
            json.dumps({"signature": signature, signature: attempt,
                        "failure_class": kind, "action": action,
                        "max_attempts": budget}),
            encoding="utf-8")
        (_state_dir() / FAILURE_REPORT_NAME).write_text(
            f"# Check failure — attempt {attempt} of {budget}\n\n"
            f"Class `{kind}`, remedy `{action}`.\n"
            f"Signature `{signature}` (digits normalised, so a partial fix does\n"
            f"not reset the attempt budget).\n\n"
            + (f"{REMEDY_NOTE[kind]}\n\n" if kind in REMEDY_NOTE else "")
            + f"## What failed\n\n```\n{detail}\n```\n\n"
            + "## Uncommitted at the time\n\n"
            + "".join(f"- {p}\n" for p in paths[:40])
            + "\n## Next\n\n"
            "This file is scratch, overwritten each failure, and is not a\n"
            "knowledge doc. Root-cause the failure before changing anything.\n",
            encoding="utf-8")
    except OSError:
        pass
    return attempt


GREEN_REF_PREFIX = "refs/uaios/green/"


def _slug() -> str:
    """The unit of work, taken from the branch. `feat/x` -> `x`."""
    branch = current_branch(REPO_ROOT) or ""
    prefix = "feat/"
    return branch[len(prefix):] if branch.startswith(prefix) else branch


def _mark_green() -> None:
    """Point this unit's green ref at HEAD. Best effort, never fatal.

    Called only after the fast tier passed, so the ref always names a tree that
    was actually verified -- not merely one that was committed.
    """
    slug = _slug()
    if not slug or slug == "HEAD":
        return
    git("update-ref", f"{GREEN_REF_PREFIX}{slug}", "HEAD")


def _clear_failures() -> None:
    for name in (FAILURE_STATE_NAME, FAILURE_REPORT_NAME):
        try:
            (_state_dir() / name).unlink(missing_ok=True)
        except OSError:
            pass


def build_message(paths, suite_detail):
    """A checkpoint subject the hook can actually justify, plus the evidence."""
    groups: dict[str, int] = {}
    for p in paths:
        head = p.split("/")[0] if "/" in p else "(root)"
        groups[head] = groups.get(head, 0) + 1
    summary = ", ".join(f"{k} ({v})" for k, v in sorted(groups.items()))
    subject = f"wip: checkpoint {len(paths)} file(s) -- {summary}"
    if len(subject) > 72:
        subject = f"wip: checkpoint {len(paths)} file(s) across {len(groups)} area(s)"

    listing = "\n".join(f"- {p}" for p in paths)
    return (
        f"{subject}\n\n"
        f"Automatic checkpoint from stop-finalization/06-artifact-autocommit.py. Not a\n"
        f"reviewed commit: squashed at PR time, when a human reads the branch.\n\n"
        f"Verified before committing: {suite_detail}; no credential pattern in\n"
        f"the changed files; branch is not protected.\n\n"
        f"{listing}\n"
    )


def main():
    # Running underneath our own suite run: never recurse, never commit.
    if os.environ.get(REENTRY_FLAG):
        return

    payload = load_payload()
    if payload.get("stop_hook_active"):
        return

    paths = changed_paths(REPO_ROOT)
    if not paths:
        return

    paths = sorted(p for p in paths if p not in NEVER_AUTO)
    if not paths:
        return

    # --- gate 1: the branch
    branch = current_branch(REPO_ROOT)
    if branch is None:
        speak("Auto-commit skipped: could not read the current branch, so it "
              "cannot rule out a protected one. Commit by hand.")
        return
    if branch in PROTECTED_BRANCHES:
        speak(f"Auto-commit skipped: `{branch}` is a protected branch. Branch "
              f"first, then the checkpoint resumes on its own.")
        return

    # --- gate 2: size
    max_files = load_config(REPO_ROOT).get("max_files", DEFAULT_MAX_FILES)
    if len(paths) > max_files:
        speak(f"Auto-commit skipped: {len(paths)} changed files is past "
              f"max_files={max_files} and is a unit of work, not a checkpoint. "
              f"Review it and commit deliberately, or raise `max_files` in "
              f"{CONFIG_NAME} if this project scaffolds in bulk.")
        return

    # --- gate 2b: schema migrations
    #
    # The least reversible thing a product contains, and the one no test proves.
    # Refusing is not a judgement about the migration -- it is a refusal to let
    # one land while nobody is looking.
    migrations = migration_paths(paths)
    if migrations:
        speak(f"Auto-commit REFUSED: this turn touches {len(migrations)} schema "
              f"migration(s) -- {', '.join(migrations[:3])}"
              f"{' …' if len(migrations) > 3 else ''}. A migration is the least "
              f"reversible thing here and no suite proves it is right. Review it "
              f"and commit deliberately. {len(paths)} file(s) left uncommitted.")
        return

    # --- gate 2c: minimal diff
    #
    # The target workflow calls minimal-diff commits mandatory, and until
    # 2026-08-10 nothing enforced it. "Minimal" here means *no unrelated file* --
    # not few lines: a formatting sweep across forty files is not minimal, and a
    # hundred-line change in one file is.
    #
    # Resolved at Gate 1 as refuse-and-name rather than warn. Every other clause
    # in this gate refuses, and a lone warning among seven refusals is the one
    # nobody reads. The accepted cost is real: a turn touching a file no plan
    # names gets NO checkpoint. That is why the refusal prints the paths -- the
    # fix is to name them in the plan or to stop touching them, never to wonder
    # why nothing committed. Silence would be the worst of the three outcomes.
    # The gate applies only where something could declare a path. A repository
    # with no `TASK.md` and no `docs/plans/*.md` has nothing to be minimal
    # *against*, and refusing there would disable the auto-commit outright in
    # every repo this layer installs into that has never written a plan. The
    # other seven clauses still run, so this is a gate that does not apply
    # rather than a check reporting green on no evidence.
    # Two conditions, and both are fail-safe. A source must exist, AND it must
    # actually declare something: only declaration-shaped lines count now, so a
    # repo with a `TASK.md` full of prose and no plan yet has a source and zero
    # declarations -- and refusing there would block every turn for work that
    # has not reached a plan.
    _declared = declared_paths(REPO_ROOT) if declaration_sources(REPO_ROOT) else set()
    if _declared - set(KNOWLEDGE_DOCS):
        unrelated = minimal_diff_refusal(paths, _declared)
        if unrelated:
            speak(unrelated)
            return

    # --- gate 3: secrets. This hook's commits never reach 01-secret-scan.py,
    # so the identical rule is enforced here from the same _hooklib patterns.
    findings = scan_for_secrets(paths, REPO_ROOT)
    if findings:
        speak("Auto-commit REFUSED: a credential pattern matched in "
              f"{', '.join(findings)}. Nothing was committed. Remove the secret "
              f"-- do not override; a committed key is unrecoverable once pushed.")
        return

    # --- gate 4: the project's own checks
    ok, suite_detail, ran_test = run_suites()
    if not ok:
        attempt = _record_failure(suite_detail, paths)
        kind, action = classify_failure(suite_detail)
        budget = failure_budget(kind)
        report = f".claude/hooks/state/{FAILURE_REPORT_NAME}"
        if attempt >= budget:
            speak(f"Checks red {attempt} times running on the SAME {kind} failure "
                  f"({suite_detail}). Not suggesting another pass: a fix that "
                  f"has not converged in {budget} attempts is not "
                  f"converging, and looping further just burns turns. This needs "
                  f"a human decision. Full report: {report}. "
                  f"{len(paths)} file(s) uncommitted.")
        else:
            speak(f"Auto-commit skipped: checks are red ({suite_detail}). "
                  f"Class {kind}, remedy {action} -- attempt {attempt} of {budget}. "
                  f"{REMEDY_NOTE.get(kind, '')} "
                  f"Written to {report}. {len(paths)} file(s) left uncommitted; "
                  f"`03-checkpoint.py` has already snapshotted them.")
        return

    # --- gate 4b: code with nothing that could have failed
    #
    # "All checks passed" and "no check ran" are the same boolean and completely
    # different facts. Committing code unattended on the second one is the whole
    # safety story evaporating quietly, which is the failure mode this repo keeps
    # rediscovering. Prose-only turns are unaffected: a README has nothing a
    # suite could have caught.
    # A false `test` value is the explicit opt-out for a project with no suite.
    # This repo configures real standalone tests, so its code edits are gated by
    # those commands instead of relying on the opt-out.
    test_disabled = load_config(REPO_ROOT).get("test") is False
    if not ran_test and not test_disabled and changed_includes_code(paths):
        speak(f"Auto-commit REFUSED: this turn changed code but no test check "
              f"ran ({suite_detail}). An unattended commit is only as good as "
              f"what could have failed, and nothing could have. Add a test "
               f"command to {CONFIG_NAME}, or set `\"test\": false` only when "
               f"this project deliberately has no suite. {len(paths)} file(s) "
              f"left uncommitted.")
        return

    message = build_message(paths, suite_detail)

    # --- gate 5: the message itself. CLAUDE.md forbids AI attribution in git
    # history, and no human reads this message before it lands.
    if any(p.search(message) for p in AI_ATTRIBUTION_PATTERNS):
        speak("Auto-commit skipped: the generated message matched an "
              "AI-attribution pattern, which CLAUDE.md forbids in git history. "
              "This is a bug in build_message() -- report it.")
        return

    msg_file = REPO_ROOT / ".claude" / "hooks" / "state" / "autocommit-msg.txt"
    try:
        msg_file.parent.mkdir(parents=True, exist_ok=True)
        msg_file.write_text(message, encoding="utf-8")
    except OSError as exc:
        speak(f"Auto-commit could not write its message file ({exc}); "
              f"{len(paths)} file(s) left uncommitted.")
        return

    # A pathspec commit alone cannot commit an untracked file, and a new file is
    # exactly what a turn most often produces. So stage first, still by explicit
    # pathspec: the pathspec can only ever be the set computed above, so the
    # sweep this hook exists to avoid remains impossible.
    #
    # DELETIONS are the case this got wrong, and the first turn that deleted a
    # file aborted the whole commit: `git add -- <path>` fails with "pathspec did
    # not match any files" when the path is in neither the worktree nor the index,
    # which is exactly the state `git rm` leaves. Five deletions in one turn left
    # a whole session uncommitted.
    #
    # `-A` alone does not fix it either -- it still cannot match a pathspec that
    # resolves to nothing. The distinction that matters is WHY the path is absent:
    #
    #   `D ` staged deletion   -- already in the index; adding it is an error
    #   ` D` worktree deletion -- must be staged, and needs `-A` to do it
    #   anything else          -- exists on disk, a plain add works
    #
    # The pathspec is still the computed set either way, so the whole-tree sweep
    # this hook exists to avoid remains impossible.
    rc_st, st_out, _ = git("status", "--porcelain", "--", *paths)
    staged_gone = set()
    if rc_st == 0:
        for line in st_out.splitlines():
            if len(line) > 3 and line[0] == "D" and line[1] == " ":
                staged_gone.add(line[3:].strip().strip('"'))
    to_add = [p for p in paths if p not in staged_gone]
    if to_add:
        rc, _, stderr = git("add", "-A", "--", *to_add)
    else:
        # Every path is already staged (a pure-deletion turn). Nothing to add.
        rc, stderr = 0, ""
    if rc != 0:
        msg_file.unlink(missing_ok=True)
        speak(f"Auto-commit could not stage its own paths ({stderr[:200]}); "
              f"nothing was committed and the index is unchanged.")
        return

    rc, _, stderr = git("commit", "-F", str(msg_file), "--", *paths)
    msg_file.unlink(missing_ok=True)

    if rc != 0:
        # Leave the index as it was found, or a failed commit strands the paths
        # staged and the next session inherits them as somebody else's work.
        rc_undo, _, undo_err = git("restore", "--staged", "--", *paths)
        index_state = ("the index was left as it was found" if rc_undo == 0
                       else f"WARNING: still staged, could not unstage ({undo_err[:120]})")
        speak(f"Auto-commit FAILED and nothing was committed: {stderr[:300]} -- "
              f"{len(paths)} file(s) still uncommitted and {index_state}.")
        return

    # Green closes the loop FORWARD, not merely quiet. If a diagnose loop was
    # running, say it ended and name the stage the workflow goes to next --
    # otherwise "no longer failing" gets mistaken for "finished", which is the
    # gap between stage 5 and stage 6 that `verifying-work` exists to hold.
    was_looping = bool(_load_failures())
    _clear_failures()

    # --- the restore point.
    #
    # This commit's tree just passed the whole fast tier, which makes it the
    # newest verified-good state of this unit of work. Recording it is what lets
    # the escalation ladder undo itself: three failed repair attempts do not
    # leave the tree where they found it, they leave it worse, and the fourth
    # attempt is then debugging damage the loop did rather than the original
    # defect. `tools/loop.py` resets here rather than digging further.
    #
    # A ref rather than a file: durable, survives a cleared context and a fresh
    # clone of the same repository, and there is no state to desync.
    _mark_green()

    rc_sha, sha, _ = git("rev-parse", "--short", "HEAD")
    resolved = (
        "The diagnose loop is closed -- checks went from red to green. "
        if was_looping else ""
    )
    speak(f"Checkpoint {sha if rc_sha == 0 else 'HEAD'}: {len(paths)} file(s), "
          f"{suite_detail}. {resolved}Local only -- nothing pushed. "
          f"Green is the mechanical half only -- it does not say the goal was met.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
