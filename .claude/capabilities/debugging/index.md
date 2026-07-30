# Debugging Capability Package

Purpose: diagnostics, reproducing bugs, logs correlation, profiling and
hotfix guidance.

Keywords: debugging, rca, logs, repro, profiler, bug, error, crash, broken, not working, exception, stack trace, why is this failing, weird behavior, root cause, memory leak, heap growing, oom, flaky test, intermittent failure, fails in ci, traceback, stacktrace, failing, failure, hangs, deadlock, segfault, panic, regression, silently, no output

Entry point: load this file only for debugging tasks. It points to skills and
workflows that safely reproduce and diagnose failures.

Layout


Routing

Prefer blueprints first. When executing hotfixes, always require human
approval and validators.

Skills

The 5 skills for this capability are discoverable Claude Code skills
under `.claude/skills/`, each prefixed `debugging-`. They are invoked by name via
the Skill tool, not loaded from this directory:

- `debugging-flaky-test-diagnoser`
- `debugging-log-parser`
- `debugging-memory-leak-detector`
- `debugging-profiler-orchestrator`
- `debugging-repro-script`

This index still owns routing that a flat skill list cannot express: which
blueprint or workflow takes precedence, and which validator must run before
any side effect is committed.

Artefacts

Canonical copies live in top-level `.claude/` directories, prefixed
`debugging-`. The copies still under `capabilities/debugging/` are superseded and
must not be linked to.

- `.claude/blueprints/` — `debugging-rca`
- `.claude/validators/` — `debugging-hotfix`
- `.claude/workflows/` — `debugging-repro`
