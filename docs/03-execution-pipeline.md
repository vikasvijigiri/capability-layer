# 03 — Execution Pipeline

## Stages
1. Intake & intent extraction
2. Planning & task decomposition
3. Model + tool execution
4. Validation & verification
5. Reflection & learning

## Guarantees
- Each stage emits structured events for tracing.
- Side effects are guarded by validators and can be rolled back or audited.

## Policies
- Token budgeting before heavy operations.
- Early-stop heuristics when confidence thresholds reached.
- Parallelize independent sub-tasks when safe.