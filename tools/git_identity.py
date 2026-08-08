#!/usr/bin/env python3
"""Which GitHub owners could this repository be published under.

    python tools/git_identity.py            # a table, ranked
    python tools/git_identity.py --json     # the same, for a command to consume

Why this exists
---------------
`/publish` resolved the owner with a single `gh api user --jq .login`. Three
things that gets wrong, all of them silently:

  - **Organisations are invisible.** Most repositories worth publishing belong to
    an org, and `gh api user` never names one. The command would create the
    repository under a personal account and nobody would notice until the URL.
  - **A second account is invisible.** `gh` supports several logins, including
    enterprise hosts. Only the active one was ever seen.
  - **An unauthenticated `gh` produced nothing at all**, and a command that
    resolves an owner to the empty string will happily build `gh repo create
    /name`.

So this reports every candidate it can find, each labelled with where it came
from, and ranks them. It **decides nothing** -- `/publish` asks the user, and the
answer is a click. Ranking only sets which option is offered first.

Sources, in the order they are trusted:

    gh-active   `gh api user` -- the account gh would actually use
    gh-org      `gh api user/orgs` -- orgs the active account belongs to
    gh-account  `gh auth status` -- every logged-in account, any host
    remote      an existing `origin`, parsed from its URL
    git-email   `user.email`, when it is a GitHub noreply address
    git-name    `user.name`, last because it is a display name, not a login

Everything degrades to "no candidates" rather than raising. A missing `gh`, no
network, or a fresh machine must not turn "I cannot tell who you are" into a
crash -- the command handles the empty case by asking for a username.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# `12345678+octocat@users.noreply.github.com` and the older `octocat@users.noreply.github.com`
NOREPLY = re.compile(r"^(?:\d+\+)?([A-Za-z0-9][A-Za-z0-9-]*)@users\.noreply\.github\.com$")

# git@github.com:owner/repo.git · https://github.com/owner/repo · ssh://git@host/owner/repo
REMOTE_OWNER = re.compile(
    r"(?:[:/])([A-Za-z0-9][A-Za-z0-9-]*)/[^/]+?(?:\.git)?/?$")

# `gh auth status` prints e.g. "  ✓ Logged in to github.com account octocat (keyring)"
GH_ACCOUNT = re.compile(
    r"Logged in to (\S+) (?:as|account) ([A-Za-z0-9][A-Za-z0-9-]*)")

# A GitHub login: alphanumeric and single hyphens, 1-39 chars, no leading hyphen.
VALID_LOGIN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}$")

# Lower sorts first.
RANK = {
    "gh-active": 0,
    "gh-org": 1,
    "gh-account": 2,
    "remote": 3,
    "git-email": 4,
    "git-name": 5,
}


def _run(args: list[str], cwd: Path | None = None, timeout: int = 20) -> str:
    """stdout+stderr, or '' for any failure. `gh auth status` writes to stderr,
    so both streams are read -- reading only stdout found no accounts at all."""
    try:
        proc = subprocess.run(
            args, cwd=str(cwd or ROOT), capture_output=True,
            encoding="utf-8", errors="replace",
            stdin=subprocess.DEVNULL, timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return (proc.stdout or "") + (proc.stderr or "")


def valid(login: str) -> bool:
    return bool(login) and bool(VALID_LOGIN.match(login))


def gather(root: Path, offline: bool = False) -> list[dict]:
    """Every candidate owner, deduped, ranked, each with its source.

    `offline` skips the two calls that need the network, so the discovery can be
    exercised without depending on a live GitHub.
    """
    found: list[tuple[str, str, str, str]] = []   # (owner, source, kind, host)

    if not offline:
        active = _run(["gh", "api", "user", "--jq", ".login"]).strip()
        # `gh` prints its errors to the same streams, so a failure can look like a
        # login. Only a syntactically valid single token is accepted.
        if valid(active.splitlines()[0].strip() if active else ""):
            found.append((active.splitlines()[0].strip(), "gh-active", "user",
                          "github.com"))

        orgs = _run(["gh", "api", "user/orgs", "--jq", ".[].login"])
        for line in orgs.splitlines():
            name = line.strip()
            if valid(name):
                found.append((name, "gh-org", "org", "github.com"))

    status = _run(["gh", "auth", "status"])
    for host, login in GH_ACCOUNT.findall(status):
        if valid(login):
            found.append((login, "gh-account", "user", host))

    remotes = _run(["git", "remote", "-v"], cwd=root)
    for line in remotes.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        match = REMOTE_OWNER.search(parts[1])
        if match and valid(match.group(1)):
            found.append((match.group(1), "remote", "unknown", "github.com"))

    email = _run(["git", "config", "--get", "user.email"], cwd=root).strip()
    noreply = NOREPLY.match(email)
    if noreply and valid(noreply.group(1)):
        found.append((noreply.group(1), "git-email", "user", "github.com"))

    name = _run(["git", "config", "--get", "user.name"], cwd=root).strip()
    # A display name is usually "Ada Lovelace", which is not a login. Only offered
    # when it happens to be login-shaped, and ranked last regardless.
    if valid(name):
        found.append((name, "git-name", "unknown", "github.com"))

    best: dict[str, dict] = {}
    for owner, source, kind, host in found:
        key = owner.lower()
        current = best.get(key)
        if current is None or RANK[source] < RANK[current["source"]]:
            best[key] = {"owner": owner, "source": source, "kind": kind,
                         "host": host, "also": []}
        if current is not None and source not in current["also"] \
                and source != current["source"]:
            current["also"].append(source)

    return sorted(best.values(), key=lambda c: (RANK[c["source"]], c["owner"].lower()))


REASON = {
    "gh-active": "the account gh is currently authenticated as",
    "gh-org": "an organisation this account belongs to",
    "gh-account": "a logged-in gh account",
    "remote": "owner of an existing git remote",
    "git-email": "from a GitHub noreply address in user.email",
    "git-name": "user.name, which is a display name and may not be a login",
}


def render(candidates: list[dict], authed: bool) -> str:
    if not candidates:
        return (
            "no candidate owners found.\n\n"
            + ("`gh` is not authenticated. `gh auth login` is an interactive "
               "browser flow and cannot be scripted, so it has to be run by hand "
               "in a terminal.\n" if not authed else "")
            + "Publishing needs a GitHub username or organisation typed in."
        )
    lines = [f"{len(candidates)} candidate owner(s):", ""]
    width = max(len(c["owner"]) for c in candidates) + 2
    for candidate in candidates:
        also = (f"  (also seen as: {', '.join(candidate['also'])})"
                if candidate["also"] else "")
        host = "" if candidate["host"] == "github.com" else f"  [{candidate['host']}]"
        lines.append(f"  {candidate['owner']:<{width}}{candidate['kind']:<9}"
                     f"{REASON[candidate['source']]}{host}{also}")
    lines.append("")
    lines.append("Ranked, not chosen. `/publish` asks; the answer is the user's.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--json", action="store_true", dest="as_json")
    ap.add_argument("--offline", action="store_true",
                    help="skip the calls that need the network")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    candidates = gather(root, offline=args.offline)
    authed = "Logged in to" in _run(["gh", "auth", "status"])

    if args.as_json:
        print(json.dumps({
            "candidates": candidates,
            "gh_authenticated": authed,
            "needs_manual_entry": not candidates,
        }, indent=2))
    else:
        print(render(candidates, authed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
