# Reproduction Workflow — .claude/workflows/debugging-repro.md

> **How to run this.** This is a document you follow, not an executable. Claude Code
> has no workflow runtime. The owning skill routes here; read the steps, run each with
> the Skill or Agent tool, and finish with the validator named below.


Purpose: safely reproduce an incident in a sandbox and run RCA.

Stages

1. Recreate environment snapshot
2. Replay traffic or test harness
3. Run `log-parser` and profiler
4. Produce RCA report and remediation plan

Safety

- Use synthetic data when possible
- Human approval required before live fixes
