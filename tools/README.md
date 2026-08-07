# Tools

Helper scripts and the repo's test suites.

- `run_hook.py` — trigger a hook manually: `python tools/run_hook.py <event> '<json>'`.
  Passes the payload via `HOOK_PAYLOAD`; scripts read it through
  `_hooklib.load_payload()`, which handles both that and stdin.

Test suites, all run by `/verify`. The count is not stated here on purpose — it
was "six" while the real number quietly grew to 22, and a number nothing
enforces is a number that rots. `.claude/project-checks.json`'s `test` array is
the live list. Four worth knowing by name because they gate things other suites
do not:

- `test_hooks.py` — every hook script against realistic payloads.
- `test_process_router.py` — skill routing: matching, fail-open, and that every
  heading names a real skill and every skill has an entry.
- `test_hook_registration.py` — disk, `settings.json` and `hooks_registry.json`
  agree, in all three directions.
- `test_artifact_autocommit.py` — what the `Stop` auto-commit will and will not take.
- `test_project_checks.py` — check detection per project type, and the credential
  patterns on both axes (path and content).

Not a suite, but run by the commit gate as a lint check:

- `check_config_json.py` — every tracked `.json` parses, and `settings.json`
  registers no hook that is missing from disk. A stray comma there silently
  turns the whole hook layer off.
- `test_referenced_paths.py` — every hook or tool path named in prose exists, or
  is marked gone on the same line. Added after deleting three hooks broke four
  skills and a slash command with every suite still green.

`test_docs_gates.py` was deleted on 2026-08-02 with the two hooks it covered
(`post-run/05-docs-gate.py`, `pre-commit/05-docs-required.py`).

```bash
PYTHONIOENCODING=utf-8 python tools/test_hooks.py
```

`resolve_capability.py`, `test_resolver.py`, `test_router.py`,
`generate_registry.py`, `run_workflow.py` and `validator_runner.py` were deleted
on 2026-08-01 with the capability layer they served. They are in `eaab430`.
