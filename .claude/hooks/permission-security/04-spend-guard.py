"""permission-security -- fires on Bash/PowerShell calls that invoke a
cloud-provider CLI (vercel, netlify, flyctl, railway, supabase, doctl,
heroku, aws, gcloud, az).

Scope, by design: fast, deterministic, mechanical checks only.

Decision policy, deliberately different from the branch/attribution checks:
deny or allow, **never** ask. This check exists specifically for autonomous
runs where nobody is present to answer a prompt -- an unanswered "ask" would
either hang indefinitely or fall back unpredictably. So this check only ever
denies (with a reason) or allows silently.

Allowlist-first, not blocklist-first: a command is denied by default and only
allowed through if it matches a known-safe, free-tier command shape. A
blocklist of "paid-looking flags" can never be complete -- that's a
false-negative risk with real money attached -- so the default is deny, not
allow.

Moved from `pre-deploy/01-spend-guard.py` on 2026-08-21 (renumbered to 04
since it now shares a family with the three commit-time checks), refactored
into a `check(payload) -> str | None` function so `00-dispatch.py` can call
it in-process. Behavior unchanged.
"""

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
from _hooklib import load_payload as _load_payload  # noqa: E402

import re


VENDOR_PATTERNS = {
    "heroku": re.compile(r"\bheroku\b"),
    "aws": re.compile(r"\baws\b"),
    "gcloud": re.compile(r"\bgcloud\b"),
    "az": re.compile(r"\baz\b"),
    "doctl": re.compile(r"\bdoctl\b"),
    "vercel": re.compile(r"\bvercel\b"),
    "netlify": re.compile(r"\bnetlify\b"),
    "flyctl": re.compile(r"\bflyctl\b"),
    "railway": re.compile(r"\brailway\b"),
    "supabase": re.compile(r"\bsupabase\b"),
}

# aws/gcloud/az/doctl: free-tier status isn't statically checkable from a
# command string, so only read-only verbs are ever allowed.
READONLY_VERB_PATTERNS = [
    re.compile(r"\bdescribe[-\w]*\b"),
    re.compile(r"\blist[-\w]*\b"),
    re.compile(r"\bget[-\w]*\b"),
    re.compile(r"\bshow\b"),
    re.compile(r"\bls\b"),
]
MUTATING_VERB_PATTERNS = [
    re.compile(r"\bcreate[-\w]*\b"),
    re.compile(r"\bdelete[-\w]*\b"),
    re.compile(r"\brun-instances\b"),
    re.compile(r"\bapply\b"),
    re.compile(r"\bdeploy\b"),
    re.compile(r"\bput[-\w]*\b"),
    re.compile(r"\bupdate[-\w]*\b"),
    re.compile(r"\bset[-\w]*\b"),
    re.compile(r"\bterminate[-\w]*\b"),
    re.compile(r"\bstart[-\w]*\b"),
    re.compile(r"\bstop[-\w]*\b"),
]

SAFE_SHAPES = {
    "vercel": [
        re.compile(r"\bvercel\s+deploy\b"),
        re.compile(r"\bvercel\s+--prod\b"),
        re.compile(r"\bvercel\s+--yes\b"),
        re.compile(r"\bvercel\s+env\s+(ls|add|rm)\b"),
        re.compile(r"\bvercel\s+logs\b"),
        re.compile(r"\bvercel\s+ls\b"),
        re.compile(r"\bvercel\s+domains\s+ls\b"),
        re.compile(r"\bvercel\s+whoami\b"),
        re.compile(r"\bvercel\s+login\b"),
        re.compile(r"\bvercel\s+link\b"),
    ],
    "netlify": [
        re.compile(r"\bnetlify\s+deploy\b"),
        re.compile(r"\bnetlify\s+env:(list|set|get|unset)\b"),
        re.compile(r"\bnetlify\s+status\b"),
        re.compile(r"\bnetlify\s+logs\b"),
        re.compile(r"\bnetlify\s+link\b"),
        re.compile(r"\bnetlify\s+login\b"),
        re.compile(r"\bnetlify\s+sites:list\b"),
    ],
    "flyctl": [
        re.compile(r"\bflyctl\s+deploy\b"),
        re.compile(r"\bflyctl\s+launch\b"),
        re.compile(r"\bflyctl\s+status\b"),
        re.compile(r"\bflyctl\s+logs\b"),
        re.compile(r"\bflyctl\s+secrets\s+set\b"),
        re.compile(r"\bflyctl\s+auth\b"),
        re.compile(r"\bflyctl\s+apps\s+list\b"),
    ],
    "railway": [
        re.compile(r"\brailway\s+up\b"),
        re.compile(r"\brailway\s+logs\b"),
        re.compile(r"\brailway\s+variables\s+set\b"),
        re.compile(r"\brailway\s+status\b"),
        re.compile(r"\brailway\s+login\b"),
        re.compile(r"\brailway\s+link\b"),
    ],
    "supabase": [
        re.compile(r"\bsupabase\s+projects\s+create\b.*--plan\s+free\b"),
        re.compile(r"\bsupabase\s+db\s+push\b"),
        re.compile(r"\bsupabase\s+functions\s+deploy\b"),
        re.compile(r"\bsupabase\s+status\b"),
        re.compile(r"\bsupabase\s+login\b"),
        re.compile(r"\bsupabase\s+link\b"),
    ],
}

PAID_SIGNAL_PATTERNS = [
    re.compile(r"--plan(?:=|\s+)(?!free\b)\S+"),
    re.compile(r"--tier(?:=|\s+)(?!free\b)\S+"),
    re.compile(r"--sku(?:=|\s+)(?!free\b)\S+"),
    re.compile(r"--upgrade\b"),
    re.compile(r"--billing\b"),
    re.compile(r"--pro\b"),
    re.compile(r"--team\b"),
    re.compile(r"--enterprise\b"),
    re.compile(r"--dedicated\b"),
    re.compile(r"--reserved\b"),
    re.compile(r"--credit-card\b"),
    re.compile(r"--vm-size\b"),
    re.compile(r"--memory\b"),
]

CHAIN_OPERATOR_PATTERN = re.compile(r"&&|;|\|(?!\|)|`|\$\(")


def detect_vendor(command):
    for name, pattern in VENDOR_PATTERNS.items():
        if pattern.search(command):
            return name
    return None


def is_readonly_only(command):
    has_readonly = any(p.search(command) for p in READONLY_VERB_PATTERNS)
    has_mutating = any(p.search(command) for p in MUTATING_VERB_PATTERNS)
    return has_readonly and not has_mutating


def matches_paid_signal(command):
    for pattern in PAID_SIGNAL_PATTERNS:
        if pattern.search(command):
            return pattern.pattern
    return None


def matches_safe_shape(vendor, command):
    return any(p.search(command) for p in SAFE_SHAPES.get(vendor, []))


def check(payload: dict) -> str | None:
    """The deny reason if this command is not a verifiably free-tier call."""
    if payload.get("tool_name") not in ("Bash", "PowerShell"):
        return None

    command = (payload.get("tool_input") or {}).get("command") or ""
    if not command.strip():
        return None

    vendor = detect_vendor(command)
    if vendor is None:
        return None  # not a cloud-CLI command -- nothing for this check

    if CHAIN_OPERATOR_PATTERN.search(command):
        return (
            f"deploy-spend-guard: command chaining/piping isn't verifiable as "
            f"a single safe shape for '{vendor}' -- split into separate "
            f"commands and retry."
        )

    if vendor == "heroku":
        return "deploy-spend-guard: heroku has had no free tier since 2022 -- blocked outright."

    if vendor in ("aws", "gcloud", "az", "doctl"):
        if is_readonly_only(command):
            return None  # allow silently
        return (
            f"deploy-spend-guard: '{vendor}' mutating commands aren't "
            f"statically verifiable as free-tier -- only read-only "
            f"(describe/list/get/show/ls) calls are allowed for this vendor."
        )

    # Remaining vendors: PaaS hosts with a real, CLI-drivable free tier.
    paid_signal = matches_paid_signal(command)
    if paid_signal:
        return f"deploy-spend-guard: command matches a paid-tier signal ({paid_signal}) -- denied."

    if matches_safe_shape(vendor, command):
        return None  # allow silently

    return (
        f"deploy-spend-guard: command doesn't match a recognized free-tier "
        f"shape for '{vendor}'; add an explicit allowlist entry to this "
        f"check if this is actually $0."
    )


if __name__ == "__main__":
    from _hooklib import deny as _deny  # noqa: E402
    try:
        data = _load_payload()
        reason = check(data)
        if reason:
            _deny(reason)
    except Exception:
        pass
