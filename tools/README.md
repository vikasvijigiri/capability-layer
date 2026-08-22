# Tools

Helper scripts and the repo's test suites.

- `run_hook.py` — trigger a hook manually: `python tools/run_hook.py <event> '<json>'`.
  Passes the payload via `HOOK_PAYLOAD`; scripts read it through
  `_hooklib.load_payload()`, which handles both that and stdin.
- `security_gate.py` — `python tools/security_gate.py --base main`. Five clauses,
  every one a fact about the artefact rather than about process: a security
  control that lost an entry between base and head, a secret anywhere in the
  branch (the permission-security scan sees one commit at a time), a sensitive path no
  `test_map` glob covers, an agent that may write and declares no
  `allowed-paths:`, and a moved dependency tree `deps.py` rejects. Exit `0`/`1`/`2`,
  and `2` is not `0`. Read its docstring before adding a clause — the reason it
  is not a receipt is the whole design.

Test suites, all run by `/verify`. The count is not stated here on purpose — it
was "six" while the real number quietly grew to 22, and a number nothing
enforces is a number that rots. `.claude/project-checks.json`'s `test` array is
the live list. A few worth knowing by name because they gate things other suites
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
(`stop-finalization/05-docs-gate.py`, `permission-security/05-docs-required.py`).

```bash
PYTHONIOENCODING=utf-8 python tools/<a suite in this repo>.py
```

`resolve_capability.py`, `test_resolver.py`, `test_router.py`,
`generate_registry.py`, `run_workflow.py` and `validator_runner.py` were deleted
on 2026-08-01 with the capability layer they served. They are in `eaab430`.
