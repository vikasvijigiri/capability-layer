"""pre-tool -- refuses the next tool call while a halt is in effect.

`tools/halt.py --halt "<reason>"` writes a flag under `.claude/hooks/state/`
(gitignored, machine-local). This hook is the other half: it reads that flag
before any tool runs and denies rather than asks, because a halt that can be
talked past is not a halt.

Decision policy: `deny`, never `ask`. An `ask` can be answered "yes, do it
anyway", which defeats the point of a kill switch -- the whole reason to halt
is that nobody should decide about the next action mid-flight, not even by
approving one more.

Fails toward denial, not away from it -- the opposite of most hooks here.
`02-branch-guard.py` and the others fail OPEN, because a guard that cannot
read git state must not wedge the repo on a transient error. This one is
different: the sole purpose of a halt is to stop everything, so an error
reading the flag is treated as "assume halted" rather than "let it through".
`tools/halt.py:status()` already returns `{"halted": True, "reason": "unknown
..."}` for an unreadable flag for exactly this reason -- this hook does not
need its own fallback logic, only to trust that contract.

Registration: UNREGISTERED as of 2026-08-10. Wiring this into
`.claude/settings.json` and `.claude/hooks/hooks_registry.json` is a separate
task (Task 12 of `docs/plans/2026-08-10-checklist-completion.md`) assigned to
another agent. Fire it directly for now:

    HOOK_PAYLOAD='{}' python .claude/hooks/pre-tool/01-halt-guard.py
    python tools/run_hook.py pre-run '{}'

Per `decisions/2026-08-04-hooks-never-name-a-skill.md`, this hook names no
skill -- it names `tools/halt.py --resume`, a tool, not a workflow stage.

Scope: the mutating set, not every tool
---------------------------------------
Registered against `Bash|PowerShell|Edit|Write|NotebookEdit|Task` rather than
every tool, and that is a design decision rather than a concession to the
"narrow matcher" rule in `guide/how_to_create_hooks.md`.

**A halt that blocks reads cannot be investigated.** Someone who hits this needs
to open the flag, read the reason and check what state the tree is in before
deciding to resume — and every one of those is a `Read` or a `Grep`. Blocking
work while leaving diagnosis available is the useful shape; blocking everything
turns a kill switch into a lockout.

Everything that changes state or spawns more work is covered, which is what
"halt" has to mean to be worth having.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _hooklib import deny, load_payload  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.halt import status  # noqa: E402


def main():
    load_payload()  # keeps the same call contract as every other hook here

    st = status()
    if not st.get("halted"):
        return

    reason = st.get("reason", "unknown")
    deny(
        f"halt-guard: work is halted ({reason}). No tool calls are allowed "
        f"until it is lifted. Resume with:\n\n"
        f"    python tools/halt.py --resume"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Reading the flag failed outright (not just an unreadable JSON body,
        # which status() already handles) -- e.g. the state dir is
        # unreachable. Deny anyway: this hook fails toward halting, the
        # opposite of every other guard in this repo.
        deny(
            "halt-guard: could not determine halt state, denying out of "
            "caution. Resume with:\n\n    python tools/halt.py --resume"
        )
