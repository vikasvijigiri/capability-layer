"""`python -m capability_layer` — the invocation that works when PATH does not.

A console script is only reachable if its directory is on PATH, and on Windows a
`pip install` that cannot write to site-packages silently becomes a **user**
install:

    Defaulting to user installation because normal site-packages is not writeable

The scripts then land in `%APPDATA%\\Python\\Python3xx\\Scripts`, which is not on
PATH by default. The package is installed, importable, and completely
uninvocable — `capability-layer : The term 'capability-layer' is not recognized`.

That is not hypothetical and it is not rare: it happened to the first person who
followed this project's own README, and it had happened an hour earlier to
`pip-audit` inside this repo, where the checks reported `tool missing` for a
package that was installed. A lookup failure wearing the costume of an
environment fact.

So there are two ways in, and this is the one that cannot be broken by PATH:

    capability-layer install --into .      # needs Scripts/ on PATH
    cl install --into .                    # same
    python -m capability_layer install --into .   # needs only the interpreter

Both routes call the same `main`, so they cannot drift.
"""

from __future__ import annotations

import sys

from capability_layer.cli import main

if __name__ == "__main__":
    sys.exit(main())
