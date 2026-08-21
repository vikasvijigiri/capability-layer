# Security policy

Part of Notion §24's "Policy Gate."

**Deterministic gate**: `python tools/security_gate.py --base <base>` —
five clauses, each a fact about the artefact (`control-weakened`,
`secret-in-branch`, `sensitive-unmapped`, `agent-unscoped`,
`dependency-risk`), never a receipt that a review happened
(`decisions/2026-08-02-gate-on-blast-radius.md`). Exit `0` clean · `1` a
clause fired · `2` unevaluated.

**Runtime enforcement**: `permission-security/00-dispatch.py` denies
secrets, protected-branch commits, AI attribution, and non-free-tier cloud
spend before a `Bash`/`PowerShell` call proceeds.

**Licence/SBOM**: `python tools/deps.py --sbom`.

**The `security` skill** is the trigger surface and procedure for using
all three together — read `.claude/skills/security/SKILL.md`. Nothing
here duplicates its content.
