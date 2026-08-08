---
name: performance-engineering
description: Measure and improve latency, throughput, resource usage, startup, bundle size, database behaviour and regressions, with reproducible workloads and budgets. For slow paths, scale changes, release readiness. Do NOT use for intuition-only optimization or as a substitute for correctness testing.
when_to_use: when a product has a performance target, regression, or scale risk
effort: high
model: sonnet
disable-model-invocation: false
---

# Performance Engineering

Measure first, identify the bottleneck, change one meaningful variable, and
measure again under the same conditions.

## Method

1. Define the user-visible objective and budget: p50/p95/p99 latency,
   throughput, startup, memory, CPU, network, bundle, or cost.
2. Build a representative workload with fixed dataset, environment, warm/cold
   state, concurrency, and sample count. Record variance and limitations.
3. Establish a baseline and profile before changing code. Attribute time and
   resources to a specific layer: client, network, service, database, queue,
   storage, or external dependency.
4. Change the smallest bottleneck, preserve behavior, and rerun the same
   workload. Do not trade correctness, security, or operability for a number.
5. Add a regression benchmark or threshold to the project's checks when the
   risk is repeatable. Document noise, hardware, and acceptable variance.

## Inspect explicitly

- N+1 queries, unbounded reads, missing indexes, serialization, allocations,
  retries, timeouts, cache invalidation, connection pools, and backpressure;
- client render count, asset weight, images, hydration, accessibility, and
  mobile network behavior;
- load shape, queue saturation, tail latency, error rate, and graceful
  degradation under dependency failure.

## Evidence

Report baseline, change, workload, environment, distribution, and result. A
single fast local run is not a performance claim.

## Next step

Hand code changes to `test-driven-development` and `verifying-work`; hand
production thresholds and dashboards to `observability-sre`.

## Routing

- Enter for explicit performance requirements, regressions, scale changes, or
  performance-sensitive releases.
- Pair with `systematic-debugging` when the bottleneck is unexplained.
- Do not use for premature optimization without a measurable target.

## Success

The bottleneck is evidenced, the change improves the declared budget under a
repeatable workload, correctness remains green, and a regression guard exists.
