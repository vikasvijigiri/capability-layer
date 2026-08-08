#!/usr/bin/env python3
"""Tests for tools/git_identity.py -- who a repository could be published under.

The property that matters is **no silent wrong owner**. `/publish` used a single
`gh api user --jq .login`, which names only the active personal account: an
organisation was invisible, and the repository would land under the wrong owner
with no symptom except the URL. Measured on this machine, that one call would
have missed two orgs the account belongs to.

So: every candidate is found and labelled, an unparseable or hostile value is
never offered, and an unauthenticated machine degrades to "ask for a username"
rather than to an empty string interpolated into `gh repo create /name`.

Run: python tools/test_git_identity.py
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"OK: {name}")
    else:
        print(f"FAIL: {name}{(' -- ' + detail) if detail else ''}")
        failures.append(name)


def load(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    assert spec is not None and spec.loader is not None, f"cannot load {rel}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


gi = load("tools/git_identity.py", "git_identity_mod")


# --- login validation: the value gets interpolated into a gh command ---------

for good in ["octocat", "NG-VikasV", "ngenux", "a", "a-b-c", "x" * 39, "0start"]:
    check(f"accepts a real login: {good!r}", gi.valid(good))

for bad in ["", "-leading", "trailing-", "two--hyphens", "x" * 40,
            "has space", "semi;colon", "sla/sh", "dot.dot", "quote'",
            "$(whoami)", "a`b`", "under_score", "at@sign"]:
    check(f"rejects {bad!r}", not gi.valid(bad),
          "this value would be interpolated into `gh repo create`")


# --- remote URL parsing, in every shape git actually writes ------------------

REMOTES = [
    ("git@github.com:octocat/hello.git", "octocat"),
    ("git@github.com:octocat/hello", "octocat"),
    ("https://github.com/octocat/hello.git", "octocat"),
    ("https://github.com/octocat/hello", "octocat"),
    ("https://github.com/octocat/hello/", "octocat"),
    ("ssh://git@github.com/NG-VikasV/capability-layer.git", "NG-VikasV"),
    ("https://ghe.example.com/some-org/repo.git", "some-org"),
]
for url, want in REMOTES:
    match = gi.REMOTE_OWNER.search(url)
    check(f"parses the owner from {url[:44]}",
          bool(match) and match.group(1) == want,
          f"got {match.group(1) if match else None!r}, wanted {want!r}")


# --- the noreply email form, which is the only email that names a login ------

for email, want in [
    ("12345678+octocat@users.noreply.github.com", "octocat"),
    ("octocat@users.noreply.github.com", "octocat"),
]:
    match = gi.NOREPLY.match(email)
    check(f"reads a login out of {email[:38]}",
          bool(match) and match.group(1) == want)

for email in ["vikas.v@ngenux.com", "someone@gmail.com",
              "a@users.noreply.gitlab.com"]:
    check(f"ignores a non-GitHub address: {email}", not gi.NOREPLY.match(email),
          "a work address is not a GitHub login and must not be offered as one")


# --- gh auth status parsing --------------------------------------------------

STATUS = """github.com
  x Logged in to github.com account octocat (keyring)
  - Active account: true
ghe.example.com
  x Logged in to ghe.example.com account work-user (keyring)
"""
accounts = gi.GH_ACCOUNT.findall(STATUS)
check("finds every logged-in account, not just the active one",
      sorted(accounts) == [("ghe.example.com", "work-user"),
                           ("github.com", "octocat")], str(accounts))
check("...including the enterprise host, which is not github.com",
      any(host != "github.com" for host, _ in accounts))


# --- ranking: the answer offered first must be the likeliest -----------------

check("the active gh account outranks everything", gi.RANK["gh-active"] == 0)
check("an org outranks a plain logged-in account",
      gi.RANK["gh-org"] < gi.RANK["gh-account"],
      "an org is usually the intended owner and was previously invisible")
check("user.name ranks last, because a display name is not a login",
      gi.RANK["git-name"] == max(gi.RANK.values()))
check("every source has a rank and a human reason",
      set(gi.RANK) == set(gi.REASON),
      f"rank-only: {sorted(set(gi.RANK) - set(gi.REASON))}, "
      f"reason-only: {sorted(set(gi.REASON) - set(gi.RANK))}")


# --- degradation: a machine with nothing configured --------------------------
#
# The case that must not produce an empty owner. `gh repo create /name` is a
# valid-looking command built from a missing answer.

bare = Path(tempfile.mkdtemp()) / "bare"
bare.mkdir()
subprocess.run(["git", "init", "--quiet"], cwd=str(bare),
               capture_output=True, text=True)
subprocess.run(["git", "config", "user.email", "nobody@example.com"],
               cwd=str(bare), capture_output=True, text=True)
subprocess.run(["git", "config", "user.name", "Ada Lovelace"],
               cwd=str(bare), capture_output=True, text=True)

offline = gi.gather(bare, offline=True)
check("a repo with no remote and a non-GitHub email yields no local candidate",
      not [c for c in offline if c["source"] in ("remote", "git-email")],
      str(offline))
check("...and a display name with a space is not offered as a login",
      not [c for c in offline if c["owner"] == "Ada Lovelace"], str(offline))
check("...and the empty case renders as an instruction, not a blank",
      "username" in gi.render([], authed=False).lower(),
      gi.render([], authed=False)[:80])
check("...and says gh is unauthenticated when it is",
      "gh auth login" in gi.render([], authed=False))
check("...and does not say that when gh IS authenticated",
      "gh auth login" not in gi.render([], authed=True))

# A repo whose only signal is its remote still yields exactly one candidate.
subprocess.run(["git", "remote", "add", "origin",
                "https://github.com/some-org/thing.git"],
               cwd=str(bare), capture_output=True, text=True)
from_remote = [c for c in gi.gather(bare, offline=True) if c["source"] == "remote"]
check("an existing remote is a candidate on its own",
      len(from_remote) == 1 and from_remote[0]["owner"] == "some-org",
      str(from_remote))


# --- every candidate is well-formed -----------------------------------------

for candidate in gi.gather(ROOT, offline=True):
    check(f"candidate {candidate['owner']!r} is a valid login",
          gi.valid(candidate["owner"]))
    check(f"candidate {candidate['owner']!r} carries its source",
          candidate["source"] in gi.RANK)


# --- the command that consumes this actually names it ------------------------
#
# The layer's most-repeated failure is prose naming a thing that resolves to
# nothing. `/publish` is the only consumer, so the reference is asserted both
# ways: the command must call this script, and must NOT still resolve the owner
# with the single call that hid two orgs.

publish = (ROOT / ".claude" / "commands" / "publish.md").read_text(encoding="utf-8")
check("/publish calls the discovery script",
      "tools/git_identity.py" in publish)
check("/publish no longer resolves the owner with a bare `gh api user`",
      "gh api user --jq .login" not in publish.split("## Never")[0]
      or "Never resolve it with a single" in publish,
      "that call names only the active personal account")
check("/publish asks which owner before asking whether to publish",
      publish.index("Ask which owner") < publish.index("to confirm"),
      "choosing where is not agreeing to create")
check("/publish states the manual-entry path for an unauthenticated machine",
      "needs_manual_entry" in publish)
check("/publish validates what comes back before using it",
      "Validate whatever comes back" in publish,
      "the answer is free text and lands in a shell command")

print()
if failures:
    print(f"{len(failures)} failed: {', '.join(failures)}")
    sys.exit(1)
print("All git-identity tests passed")
