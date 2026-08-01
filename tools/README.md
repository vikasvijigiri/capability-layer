# Tools

Helper scripts and the repo's test suites.

- `run_hook.py` — trigger a hook manually: `python tools/run_hook.py <event> '<json>'`.
  Passes the payload via `HOOK_PAYLOAD`; scripts read it through
  `_hooklib.load_payload()`, which handles both that and stdin.

Test suites — all four run by `/verify`:

- `test_hooks.py` — every hook script against realistic payloads.
- `test_process_router.py` — skill routing: matching, fail-open, and that every
  heading names a real skill and every skill has an entry.
- `test_docs_gates.py` — the `Stop` block and the unlogged-commit deny.
- `test_docs_staleness.py` — the `UserPromptSubmit` staleness nudge.

```bash
PYTHONIOENCODING=utf-8 python tools/test_hooks.py
```

`resolve_capability.py`, `test_resolver.py`, `test_router.py`,
`generate_registry.py`, `run_workflow.py` and `validator_runner.py` were deleted
on 2026-08-01 with the capability layer they served. They are in `eaab430`.
