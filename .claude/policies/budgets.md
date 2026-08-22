# Budgets policy

Part of Notion §24's "Policy Gate" — how much a unit of work may cost
before that itself becomes a finding.

**Elapsed/turn budget**: `python tools/budget.py` — reports turns and
elapsed time against a ceiling, read from the chain ledger. Reports;
never halts, since that is the kill switch's job (`policies/escalation.md`).

**Risk tier** (how far work may travel before a human looks at it):
`python tools/scope.py --plan <plan>` — `0` low, `1` medium, `2` high,
forced high by a shared/control/sensitive surface, and `undetermined` is
always read as `high`. `.claude/workflow.md`'s risk-tier table names every
forcing clause.

**Change scope** (how much of the repository a change is checked
against): `python tools/scope.py` — `0` small, `1` major, `2`
undetermined, a veto list not a score; `undetermined` is always read as
`major`.

**Verification cost**: take the cheapest tier that answers the question —
`--scoped` mid-chain, `--tier all` once before delivery (`CLAUDE.md`'s
own working agreement).

Nothing here restates any instrument; each is code, run fresh each time.
