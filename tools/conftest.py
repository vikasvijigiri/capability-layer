"""Keep pytest out of this directory's contract suites.

Why this file exists
--------------------
`install.py` ships `tools/` into every repository the layer installs into, and
that includes ~42 `test_*.py` contract suites. They are standalone scripts: they
assert at module level and call `sys.exit()` when done, which is the right shape
for `python tools/test_x.py` and a fatal shape for pytest.

pytest collects any `test_*.py` under its rootdir. Collecting one of these means
importing it, and importing it means the `sys.exit()` runs during collection.
Measured 2026-08-16 in a freshly installed Python product:

    INTERNALERROR> File ".../product/tools/test_package.py", line 109
    INTERNALERROR>   sys.exit(0)
    INTERNALERROR> SystemExit: 0
    no tests ran in 32.16s

The product's own suite never ran. Installing the layer broke the host's test
runner -- the single worst thing a portable layer can do, and it shipped for
months because nothing asserted that a fresh install is green.

Why the fix is here rather than in the host's config
----------------------------------------------------
A `conftest.py` applies to its own directory downward, so this excludes exactly
the shipped suites and nothing else. The alternatives were worse:

  * writing `norecursedirs` into the host's `pyproject.toml` or `pytest.ini`
    edits a file the layer promises never to overwrite;
  * a root-level `conftest.py` claims a filename the host may want;
  * renaming the suites breaks the cross-references between them -- four other
    suites name `tools/test_worktree.py` by path;
  * moving them under `.claude/` breaks `ROOT = parents[1]` in all 42.

They stay runnable exactly as before: `python tools/test_x.py`, and
`tools/verify_layer.py` runs the set. This only stops pytest importing them.
"""

collect_ignore_glob = ["test_*.py"]
