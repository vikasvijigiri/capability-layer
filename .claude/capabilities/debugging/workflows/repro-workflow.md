> **Superseded.** The canonical copy of this file is `.claude/workflows/debugging-repro.md`.
> This copy is kept for history only — do not edit it, and do not link to it.
> References were migrated on 2026-07-30.

# Reproduction Workflow — debugging/workflows/repro-workflow.md

Purpose: safely reproduce an incident in a sandbox and run RCA.

Stages

1. Recreate environment snapshot
2. Replay traffic or test harness
3. Run `log-parser` and profiler
4. Produce RCA report and remediation plan

Safety

- Use synthetic data when possible
- Human approval required before live fixes
