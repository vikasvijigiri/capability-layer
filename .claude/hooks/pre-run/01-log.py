"""pre-run -- fires on UserPromptSubmit, i.e. before any work starts on a turn.

Records that a run began. Never blocks, never inspects the prompt: deciding
whether a prompt "is a task" needs judgment a hook does not have.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _hooklib import load_payload, write_log  # noqa: E402


def main():
    write_log("pre-run.log", "PRE-RUN", load_payload())


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
