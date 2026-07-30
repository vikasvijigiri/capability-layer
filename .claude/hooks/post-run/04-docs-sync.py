"""
Stop-hook doc-sync checker — global, runs in every repo.

Passive rules are pure filesystem-mtime comparisons, no git involved. Note:
immediately after a fresh `git clone`, a `git checkout` onto a different
branch, or a `git stash` pop, mtimes may not reflect real edit recency, so a
passive reminder may be spurious or missing. That self-corrects the moment a
reference file (HANDOFF.md, CLAUDE.md, etc.) is genuinely saved again — not
worth adding heuristic clone/checkout detection for a low-stakes, self-healing
failure mode.

That "low-stakes, self-healing" argument holds only for passive notices, and
does not extend to the one rule that blocks. A spurious block is neither: it
cannot be dismissed, and the only edit that clears it is the false HANDOFF.md
entry it is demanding. So that rule confirms against git before firing — see
`_changed_since`. (Found the hard way: a bulk checkout ordered a
months-old decision record 61ms "after" a HANDOFF.md updated days earlier, and
the resulting block could only be satisfied by fabricating project history.)

Every rule is gated on its reference file existing, so this no-ops silently
in any repo that doesn't have the doc structure it looks for.

One rule escalates past a passive notice: a `decisions/*.md` file (other than
the index) newer than `HANDOFF.md` returns `decision: block` instead of a
`systemMessage`, so the turn can't end without HANDOFF.md reflecting the
decision. Added after a real gap where four decisions landed while
HANDOFF.md sat stale for days and the passive notice alone didn't stop that
-- every other rule here stays passive. Escalating every rule to a block
would just retrain the model to ignore blocks; this one is scoped to
"a genuine decision was just recorded," the case a passive notice
demonstrably wasn't enough for. mtime only nominates a candidate for that
rule; git decides whether the decision is real, and when git cannot answer
the rule degrades to a passive notice rather than blocking on unverified
evidence.
"""

import json
import os
import re
import subprocess


def _git(repo_root, *args):
    """Run a read-only git command; return stdout, or None if git can't answer
    (not a repo, git missing, command failed)."""
    try:
        result = subprocess.run(
            ["git", "-C", repo_root, *args],
            capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout if result.returncode == 0 else None


def _is_dirty(repo_root, rel_path):
    """True if rel_path is untracked or differs from HEAD; None if git can't say."""
    out = _git(repo_root, "status", "--porcelain", "--untracked-files=all", "--", rel_path)
    return None if out is None else bool(out.strip())


def _changed_since(repo_root, ref_rel):
    """
    The set of repo-relative paths genuinely changed since `ref_rel` was last
    updated: everything touched by a commit after ref_rel's last commit, plus
    everything currently uncommitted. Returns None if git can't answer, in which
    case the caller falls back to mtime.

    mtime alone cannot distinguish a genuine edit from a clone, checkout or
    stash pop, each of which rewrites every mtime to ~now in arbitrary
    sub-second order — enough to order a months-old file "after" a reference doc
    that was really updated days later. This costs a fixed three git calls per
    reference doc regardless of repo size, rather than one per candidate file.
    """
    ref_dirty = _is_dirty(repo_root, ref_rel)
    if ref_dirty is None:
        return None
    if ref_dirty:
        # "Dirty" normally means the reference doc was just edited, so nothing
        # outranks it. But in a repo with no commits yet, every file is untracked
        # and therefore permanently dirty — which silences this hook completely,
        # for exactly the greenfield projects whose docs drift fastest. Fall back
        # to mtime there instead of reporting "nothing changed".
        if _git(repo_root, "rev-parse", "--verify", "HEAD") is None:
            return None
        return set()

    ref_commit = _git(repo_root, "log", "-1", "--format=%H", "--", ref_rel)
    if ref_commit is None or not ref_commit.strip():
        return None
    listing = _git(
        repo_root, "log", "--format=", "--name-only", f"{ref_commit.strip()}..HEAD"
    )
    status = _git(repo_root, "status", "--porcelain", "--untracked-files=all")
    if listing is None or status is None:
        return None

    # --untracked-files=all above is load-bearing: the default collapses a wholly
    # untracked directory to a single "decisions/" entry, which would miss the
    # brand-new decision record this rule exists to catch.
    changed = {line.strip() for line in listing.splitlines() if line.strip()}
    for line in status.splitlines():
        entry = line[3:].strip()
        if entry:
            # rename entries read "old -> new"; the new path is what exists now
            changed.add(entry.split(" -> ")[-1].strip('"'))
    return changed


def _is_contentless_markdown(path):
    """True if a file holds no prose beyond headings and HTML comments — i.e. it
    is still an untouched bootstrap skeleton. Content-based rather than keyed to
    byte size or the skeleton's exact wording, so it stays correct if
    bootstrap_repo.py's skeleton text is ever changed."""
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except OSError:
        return False
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    return not [
        line for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def check_docs_sync(repo_root="."):
    noise_dirs = {
        ".git", ".venv", "venv", "node_modules", "__pycache__",
        ".pytest_cache", "dist", "build", ".next", "target",
        "output", ".claude",
    }
    refs = {
        "handoff": "HANDOFF.md",
        "decisions_index": os.path.join("decisions", "README.md"),
        "claude_md": "CLAUDE.md",
        "openapi": os.path.join("api-contracts", "openapi.yaml"),
    }
    ref_mtimes = {}
    for key, path in refs.items():
        full = os.path.join(repo_root, path)
        ref_mtimes[key] = os.path.getmtime(full) if os.path.isfile(full) else None

    if ref_mtimes["handoff"] is None:
        return  # no HANDOFF.md in this repo — matches prior behavior, no-op

    changed_cache = {}

    def is_newer(rel_path, mtime, ref_key):
        """Genuinely newer than refs[ref_key] — git-confirmed where git can
        answer, mtime otherwise. Computed once per reference doc, on first use,
        so a repo that trips no rule pays for no git calls."""
        if ref_key not in changed_cache:
            changed_cache[ref_key] = _changed_since(repo_root, refs[ref_key])
        changed = changed_cache[ref_key]
        if changed is None:
            return mtime > ref_mtimes[ref_key]
        return rel_path in changed

    skip_names = {"HANDOFF.md", "LOG.md", "TASK.md", "PLAN.md", "MEMORY.md"}
    manifest_names = {"requirements.txt", "package.json", "go.mod"}
    infra_names = {"docker-compose.yml", "Dockerfile"}
    env_example_names = {".env.example", ".env.local.example"}

    newer_than_handoff = None
    decisions_newer = False
    decision_file_newer_than_handoff = None
    decision_count = 0
    manifest_newer = False
    infra_newer = False
    env_example_newer = False
    api_surface_newer = False

    for root, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if d not in noise_dirs]
        rel_root = os.path.relpath(root, repo_root).replace("\\", "/")

        for name in files:
            path = os.path.join(root, name)
            rel_path = (rel_root + "/" + name) if rel_root != "." else name
            try:
                mtime = os.path.getmtime(path)
            except OSError:
                continue

            if newer_than_handoff is None and name not in skip_names:
                if is_newer(rel_path, mtime, "handoff"):
                    newer_than_handoff = rel_path

            if rel_root == "decisions" and name != "README.md" and name.endswith(".md"):
                decision_count += 1
                if (decision_file_newer_than_handoff is None
                        and is_newer(rel_path, mtime, "handoff")):
                    decision_file_newer_than_handoff = rel_path

            if (ref_mtimes["decisions_index"] is not None
                    and rel_root == "decisions" and name != "README.md"
                    and name.endswith(".md")
                    and is_newer(rel_path, mtime, "decisions_index")):
                decisions_newer = True

            if (ref_mtimes["claude_md"] is not None
                    and is_newer(rel_path, mtime, "claude_md")):
                if name in manifest_names:
                    manifest_newer = True
                elif name in infra_names and rel_path.startswith("services/"):
                    infra_newer = True
                elif name in env_example_names:
                    env_example_newer = True

            if (ref_mtimes["openapi"] is not None
                    and is_newer(rel_path, mtime, "openapi")):
                is_py_route = (
                    (rel_path.startswith("services/backend/app/api/") and name.endswith(".py"))
                    or (rel_path.startswith("services/backend/app/domains/") and name == "router.py")
                )
                is_go_route = rel_path == "services/backend-go/main.go"
                if is_py_route or is_go_route:
                    api_surface_newer = True

    # Block only on a git-confirmed decision. Where git couldn't answer the
    # candidate is mtime-only evidence, which downgrades to a passive notice: an
    # unconfirmed block cannot be dismissed and does not self-heal, because the
    # only edit that clears it is the false HANDOFF.md entry it is demanding.
    git_confirmed = changed_cache.get("handoff") is not None
    if decision_file_newer_than_handoff and git_confirmed:
        reason = (
            f"`{decision_file_newer_than_handoff}` is a new/updated decision "
            f"record newer than HANDOFF.md — a genuine architectural decision "
            f"was just recorded but the status snapshot doesn't reflect it "
            f"yet. Update HANDOFF.md (and append a LOG.md entry) for this "
            f"decision before stopping."
        )
        print(json.dumps({"decision": "block", "reason": reason}))
        return

    bullets = []
    if decision_file_newer_than_handoff and not git_confirmed:
        bullets.append(
            f"`{decision_file_newer_than_handoff}` looks newer than HANDOFF.md by "
            f"file timestamp, but git couldn't confirm it (not a repo, or git "
            f"unavailable) — check by hand whether that decision needs a "
            f"HANDOFF.md and LOG.md entry."
        )
    if newer_than_handoff:
        bullets.append(
            f"`{newer_than_handoff}` changed since HANDOFF.md was last updated "
            f"— update HANDOFF.md and append a LOG.md entry before wrapping up."
        )
    if decisions_newer:
        bullets.append(
            "A `decisions/NNNN-*.md` file is newer than `decisions/README.md` "
            "— add/update its row in the index table."
        )
    # MEMORY.md is in skip_names above (correctly — the docs you edit in response
    # to a nudge must not nudge about themselves, or updating one loops forever),
    # which left it the only knowledge doc with no staleness coverage at all.
    # This is that coverage: passive, and gated on the repo having accumulated
    # enough real architectural history for an empty MEMORY.md to be a genuine
    # gap rather than a brand-new repo's normal state.
    memory_path = os.path.join(repo_root, "MEMORY.md")
    if (decision_count >= 3 and os.path.isfile(memory_path)
            and _is_contentless_markdown(memory_path)):
        bullets.append(
            f"MEMORY.md is still an empty bootstrap skeleton while this repo has "
            f"{decision_count} decision records — record the durable project "
            f"conventions that aren't already captured in CLAUDE.md/AGENTS.md, "
            f"decisions/, or git history (or delete it if it holds nothing unique)."
        )
    if manifest_newer:
        bullets.append(
            "A dependency manifest changed after CLAUDE.md — check whether "
            "CLAUDE.md's stack description still matches (skip if this was "
            "just a routine version bump)."
        )
    if infra_newer:
        bullets.append(
            "A docker-compose.yml or Dockerfile under services/ changed "
            "after CLAUDE.md — check the \"how the backend runs\" section "
            "is still accurate."
        )
    if env_example_newer:
        bullets.append(
            "A .env.example / .env.local.example template changed after "
            "CLAUDE.md — check the secrets section still lists the right "
            "variables."
        )
    if api_surface_newer:
        bullets.append(
            "A route/handler file changed after api-contracts/openapi.yaml "
            "— check whether the OpenAPI contract needs updating."
        )

    if bullets:
        # Name the skill that owns each format and state the consequence, in the style
        # hook_self_test_nudge uses. A bare "reminders:" list says what is stale but not
        # who fixes it or why it matters, so it reads as cosmetic and gets deferred --
        # which is exactly how a HANDOFF.md stayed materially false for a whole session
        # in this setup while this hook fired on every turn.
        joined = " ".join(bullets)
        owners = []
        if any(doc in joined for doc in
               ("HANDOFF.md", "LOG.md", "MEMORY.md", "decisions/", "decision")):
            owners.append("`knowledge-manager` — owns HANDOFF/LOG/MEMORY/decisions")
        if "CLAUDE.md" in joined:
            owners.append("`repo-onboarding` — owns CLAUDE.md")
        if "openapi.yaml" in joined:
            owners.append("update the OpenAPI contract alongside the route change")

        count = len(bullets)
        message = (
            f"Docs-sync: {count} project doc{'s are' if count != 1 else ' is'} now out of "
            f"step with the code.\n"
            + "\n".join(f"- {b}" for b in bullets)
            + "\n\nFix via: " + "; ".join(owners)
            + "\nThis is not cosmetic. The next session reads these docs at SessionStart "
              "and trusts them -- a status doc still describing the previous state gets "
              "acted on as if it were true."
        )
        print(json.dumps({"systemMessage": message}))


if __name__ == "__main__":
    try:
        check_docs_sync()
    except Exception:
        pass
