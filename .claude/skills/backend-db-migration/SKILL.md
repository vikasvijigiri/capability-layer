---
name: backend-db-migration
model: sonnet
description: Generates a reversible database migration (schema change + rollback) with a data-safety check for existing rows. Use for "add a column/table", "migrate the schema", "database migration", "change this db structure", "add a field", "change the table", "we need a new column", "store one more thing per user". Prefer this over editing the schema by hand - the rollback path and existing-row safety are what a migration is for. Do NOT use for a one-off data fix with no schema change — that's a script, not a migration. Implementation-level; for choosing the stack, database or architecture pattern in the first place, use `stack-selector`.
effort: medium
---

# DB Migration Skill

Generates a forward + rollback migration pair and checks the change against existing data for safety.

## When to use
- "add a column/table", "migrate the schema", "database migration"

## Steps
1. Diff `schema_change` against `current_schema`.
2. Generate the forward migration and a matching rollback.
3. Flag any destructive step (drop column/table, type narrowing) against existing data.
4. Return `migration_script` + `rollback_script` + safety flags.

## Notes
Any destructive step requires explicit human confirmation before running against a real database.

## Routing

**Validator (required): `.claude/validators/backend-change.md`.** CLAUDE.md makes this mandatory before any side effect is committed - it is not optional cleanup after the fact. Run it and report the result; a skipped validator is a failed run, not a fast one.

Before composing from scratch, check `.claude/blueprints/backend-oauth.md` - a matching blueprint takes precedence over a hand-built solution.

## Human gate

Gate before running a migration against any database that is not a local throwaway. The brief must state whether the down-migration has actually been tested, and whether the change is destructive to existing rows -- a dropped or narrowed column is irreversible regardless of what the down-migration claims, because the data is already gone.

Gate the down-migration separately if it is ever run in anger.

Invoke `approval-brief` and let it run the `AskUserQuestion` dialogue. Do not write your own prose "shall I proceed?" -- the dialogue shape, the option wording and the no-bundling rule live in that one skill so they cannot drift apart here.
