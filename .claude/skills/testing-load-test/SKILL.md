---
name: testing-load-test
model: haiku
description: Designs and runs a load or stress test to find where a system degrades, using a realistic traffic shape rather than a flat request loop. Use for "can this handle the load", "load test this", "what happens under traffic", "will it survive launch", "how many users can we take", "stress test", "it falls over under load", "performance test before release". Prefer this over hoping production traffic behaves like your laptop - systems fail at a threshold, and the only way to know the threshold is to cross it deliberately. Do NOT use to profile a single slow function; that is debugging-profiler-orchestrator.
effort: low
---

# Testing Load Test

## Steps

1. **Define the question before generating traffic.** "Can we handle launch" is not
   testable; "does p95 stay under 500ms at 200 concurrent users" is. Without a threshold
   there is no pass or fail, only numbers.
2. **Model realistic traffic shape.** Real load is bursty, mixed across endpoints, and
   arrives with cold caches. A flat loop against one endpoint measures that endpoint, not
   the system.
3. **Use realistic data volume.** A table with a thousand rows behaves nothing like one
   with ten million; testing against a small dataset measures the wrong system entirely.
4. **Ramp, do not slam.** Increasing load progressively finds the *knee* - the point where
   response time turns non-linear - which is the number worth knowing.
5. **Watch resources, not just response times.** CPU, memory, connection pools, disk and
   queue depth reveal which one runs out first, and that is the actual capacity limit.
6. **Find the failure mode.** Does it degrade gracefully, queue, shed load, or fall over?
   A system that collapses at 101 percent is far more dangerous than one that slows down.

## Rules

- **Never load test production** without explicit approval - it is an outward-facing action
  with real user impact.
- **Report the threshold and the bottleneck**, not a single throughput figure. "1000 rps"
  without saying what broke first is not actionable.
- State the difference between the test environment and production; an untested divergence
  invalidates the number.


## Routing

**Validator (required): `.claude/validators/testing-coverage-gate.md`.** CLAUDE.md makes this mandatory
before any side effect is committed - it is not optional cleanup after the fact. Run it and
report the result; a skipped validator is a failed run, not a fast one.
