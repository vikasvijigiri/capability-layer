"""
PreToolUse hook -- denies a write outside a dispatched agent's declared file
scope.

Every agent already declares a `tools:` allowlist the harness enforces; that
allowlist says WHAT an agent may call, never WHERE it may write. Until this
hook existed, an agent's file scope was prompt instruction only -- a sentence
in its own `.md` telling it to stay inside its brief -- and nothing stopped a
write outside that sentence except the agent choosing to honour it. This is
the mechanism instead of the prompt.

Scope of enforcement, deliberately narrow:

  - Fires only on Edit / Write / NotebookEdit.
  - Applies only inside a DISPATCHED agent's run -- identified by the
    `UAIOS_AGENT_NAME` environment variable the dispatcher sets before it
    launches the agent. The interactive/main session sets no such variable,
    so an ordinary edit in the main session is untouched by this guard: there
    is no declared scope for "the session", only for a dispatched agent.
  - Only agents whose `tools:` line grants `Write` or `Edit` are scoped at
    all -- a read-only agent has nothing to enforce.

Scope resolution, per agent, read from its own frontmatter in
`.claude/agents/<name>.md`:

  - `allowed-paths: <comma-separated globs>` -- a STATIC scope, fixed at
    review time (e.g. `researcher`, which only ever writes the one digest
    directory it is dispatched into).
  - `allowed-paths: dispatched` -- scope is decided per round, not per agent
    (e.g. `implementer`, whose files are whatever task it was handed).
    The dispatcher then supplies the actual globs for THIS run in
    `UAIOS_AGENT_SCOPE` (comma-separated, repo-relative, `fnmatch` globs).

**If the scope cannot be established, deny.** That covers every failure mode
uniformly: an agent name the guard cannot resolve, a writing agent with no
`allowed-paths` field, or a `dispatched` agent whose dispatcher never set
`UAIOS_AGENT_SCOPE`. An unscoped write is exactly the case this hook exists
for, so silence is never the safe answer here the way it is for an
unmatched path pattern elsewhere in this file.

Decision policy: deny, naming the agent, the attempted path, and (when known)
the declared scope. No `ask` -- a subagent cannot see or resolve an
interactive prompt, so `ask` would behave exactly like `allow`.
"""

import fnmatch
import json
import re
import sys as _sys
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
from _hooklib import load_payload as _load_payload  # noqa: E402

ROOT = _Path(__file__).resolve().parents[3]
AGENTS_DIR = ROOT / ".claude" / "agents"

EDIT_TOOL_NAMES = {"Edit", "Write", "NotebookEdit"}

# Sentinel meaning "this agent's scope is decided per dispatch, not fixed in
# its own file" -- see the module docstring.
DISPATCHED_SENTINEL = "dispatched"

FRONTMATTER_RE = re.compile(r"^---\r?\n(.*?)\r?\n---", re.S)


def deny(reason):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))


def agent_frontmatter(agent_name):
    """The parsed frontmatter fields for `.claude/agents/<agent_name>.md`, or
    None when the file is missing or unparsable. Never raises."""
    path = AGENTS_DIR / f"{agent_name}.md"
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    match = FRONTMATTER_RE.match(text)
    if not match:
        return None
    fields = {}
    for line in match.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "\t", "#")):
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip()
    return fields


def resolved_scope(agent_name, env):
    """The list of glob patterns this agent may write to right now, or None
    when no scope could be established. `env` is injectable for testing."""
    fields = agent_frontmatter(agent_name)
    if fields is None:
        return None
    declared = fields.get("allowed-paths", "")
    if not declared:
        return None
    if declared.strip().lower() == DISPATCHED_SENTINEL:
        declared = env.get("UAIOS_AGENT_SCOPE", "")
        if not declared.strip():
            return None
    patterns = [p.strip() for p in declared.split(",") if p.strip()]
    return patterns or None


def normalised(path):
    """`path` relative to the repo root, forward-slashed, when possible --
    otherwise the forward-slashed path as given. A path outside the repo can
    never match a repo-relative glob, which is the correct (denying) outcome
    rather than an error."""
    posix = str(path).replace("\\", "/")
    try:
        rel = _Path(path).resolve().relative_to(ROOT)
        return str(rel).replace("\\", "/")
    except (OSError, ValueError):
        return posix


def in_scope(path, patterns):
    norm = normalised(path)
    for pattern in patterns:
        pat = pattern.replace("\\", "/")
        if norm == pat:
            return True
        if fnmatch.fnmatch(norm, pat):
            return True
    return False


def main(env=None):
    import os
    env = env if env is not None else os.environ

    try:
        data = _load_payload()
    except Exception:
        return

    tool_name = data.get("tool_name")
    if tool_name not in EDIT_TOOL_NAMES:
        return

    agent_name = env.get("UAIOS_AGENT_NAME", "").strip()
    if not agent_name:
        # No dispatched agent in play -- this is the main session, which has
        # no declared file scope to enforce.
        return

    tool_input = data.get("tool_input") or {}
    path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not path:
        return

    patterns = resolved_scope(agent_name, env)
    if patterns is None:
        deny(
            f"agent-scope-guard: '{agent_name}' has no resolvable file scope "
            f"for this write to '{path}'. An unscoped write is denied, not "
            f"allowed by default -- declare `allowed-paths:` in "
            f".claude/agents/{agent_name}.md, or (for a dispatched scope) set "
            f"UAIOS_AGENT_SCOPE before dispatch."
        )
        return

    if in_scope(path, patterns):
        return

    deny(
        f"agent-scope-guard: '{agent_name}' may write only "
        f"{', '.join(patterns)}, and '{path}' is outside that scope. Report "
        f"NEEDS_CONTEXT and name the path instead of writing it."
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
