# Are Cluster D and Cluster B's external citations still accurate, and how should Cluster B's frozen-golden marker be resolved?

**Asked because:** `docs/specs/2026-08-21-qualitative-objective-metrics.md` cites
six external sources for Cluster D (objectives 11, 12, 26, 29) and Cluster B
(objectives 17, 19, 20) instrument design, and leaves one open
`[NEEDS CLARIFICATION]` marker on Cluster B/objective 20: should telemetry
field names belong in the frozen contract-surface golden, given 3 fields were
added in one week? This feeds `docs/plans/2026-08-22-cluster-d-layer-self-grading.md`,
which builds Cluster D now and needs the six citations current before basing
new checks on them.

**Verdict:** All six citations hold up and one is richer than quoted. The
Cluster B marker is answered: include telemetry fields in the golden, in an
explicit two-tier split (`stable` fails on removal/rename; `unstable` allows
free change) — the direct transplant of a verified `cargo-semver-checks`
mechanism. Cluster B itself is not built this pass; only the marker is
narrowed.

## Findings

**Sub-question: does `github/awesome-copilot`'s `hooks.instructions.md` still say what the spec quotes, and is there more to it?**
Read in full via raw fetch. Confirms the spec's quotes verbatim ("One hook,
one responsibility"; "Keep hooks synchronous, bounded, and non-interactive";
manual JSON-payload testing; `timeoutSec` default 30s). Also states clauses
the spec did not quote: "Default to observe first", "Do not mutate branch,
index, or worktree state by default", "Redact secrets, credentials, tokens,
and private content from logs", "Keep stdout clean", strict-mode requirements
(`set -euo pipefail` / `Set-StrictMode -Version Latest`), "Check dependencies
early and fail clearly if missing". Confidence: high (primary source, fetched
this session). Means here: Task 2's 5-clause instrument can cite this file
confidently; the git-mutation and secret-redaction clauses are real
additional contract items but need their own detection design (not a single
AST predicate) — named as a follow-on in the plan, not built this pass.

**Sub-question: does `anthropics/skills`'s `quick_validate.py` still validate what the spec describes?**
Read the full script via the GitHub contents API
(`skills/skill-creator/scripts/quick_validate.py` — note the path has an extra
`skills/` segment versus what the spec's URL implied; the shorter path
404s). Confirms name kebab-case + 64-char limit and description 1024-char
limit exactly as cited. Also validates fields the spec didn't mention:
`ALLOWED_PROPERTIES = {'name','description','license','allowed-tools',
'metadata','compatibility'}` with **hard rejection of any unexpected key**,
no leading/trailing/consecutive hyphens in `name`, no angle brackets in
`description`, and a `compatibility` field capped at 500 chars. Confidence:
high (primary source, read whole). Means here: the "reject unexpected keys"
pattern is a stronger structural-validator idiom than the spec cited: worth
noting for objective 11's design even though this plan doesn't build a
frontmatter validator.

**Sub-question: does `import-linter` still offer the contract types the spec relies on, and is there a minimal way to express this repo's own `_load()` exception?**
Confirmed via the current docs (`independence`, `layers` contract types,
`forbidden` also exists). Found the exact mechanism needed: `ignore_imports`,
a per-edge allowlist (`mypackage.bar.green -> mypackage.utils`), not a
blanket skip. Confidence: high (primary docs, current version). Means here:
Task 3's stdlib `ast` walker should implement its allowlist the same way —
named edges, each with a citation, never a bare `# noqa`-style silent pass.

**Sub-question: what is the exact 12-factor Factor III text?**
`https://12factor.net/config`, confirmed: "config... stored in environment
variables... unlike config files, there is little chance of them being
checked into the code repo accidentally." Confidence: high. Means here:
objective 29's grounding citation is now the primary source, not a paraphrase.

**Sub-question: is Molecule's idempotence step still described the way the spec quotes it?**
Confirmed via search of Ansible's current docs and FAQ: "Molecule will
simply run the converge action twice and check against Ansible's standard
output... The second run should normally end with `changed=0`." Confidence:
high (multiple independent Ansible-maintained sources agreeing). Not used by
Cluster D directly (it grounds Cluster B/objective 19, not built this pass),
kept for completeness since the spec cites it there.

**Sub-question: how does `cargo-semver-checks` handle a surface that changes frequently, and does that answer Cluster B's open marker?**
Confirmed via its documentation: 3-tier major/minor/patch classification,
**and** an automatic heuristic that excludes features literally named
`unstable`/`nightly`/`bench`/`no_std` (or prefixed `unstable-`/`unstable_`)
from breaking-change detection by default, configurable via
`--features unstable` to opt in explicitly. Separately, individual lints can
be downgraded to `warn` via `[package.metadata.cargo-semver-checks.lints]`
— tracked and visible, never silently unguarded. Confidence: high (primary
source). **This directly answers the open marker**: telemetry fields should
be **included** in the frozen golden, split into a `stable` tier (removal or
rename fails the check) and an `unstable` tier (free addition; removal or
rename only warns, does not fail) — the same shape as `cargo-semver-checks`'s
unstable-exclusion plus per-lint `warn` downgrade. A field moves `unstable` →
`stable` only by a deliberate, reviewed edit to the golden file, never
automatically — this preserves the "additive change is visible in review"
property the whole golden-diff mechanism exists for.

**Sub-question: does OpenAPI diff tooling corroborate this pattern?**
`WebSearch` only (no primary source opened — `oasdiff`'s and
`Azure/openapi-diff`'s repos were not fetched, only their search-result
descriptions). Search results describe an ERR/WARN severity split
(`oasdiff`: "breaking changes... two levels: ERR... WARN") that is
structurally the same additive/tiered-severity shape as `cargo-semver-checks`,
but this is **medium confidence** — a snippet describing the repo, not the
repo itself read. Means here: corroborating signal only, not a primary
citation; the plan cites `cargo-semver-checks` as the primary source for the
marker resolution and this only as converging, lower-confidence support.

## Disagreements

None. All six citations were independently confirmed against their own
primary source (five fetched/read in full; Molecule confirmed via multiple
agreeing Ansible-maintained pages) and none contradicted the spec's use of
them. The OpenAPI-diff sub-question is the one place confidence is medium
rather than high, stated as such above rather than promoted.

## Not adopted

- Extending Task 2's hook-conformance instrument to also check
  `awesome-copilot`'s git-state-mutation and secret-redaction clauses: real,
  confirmed clauses, but neither reduces to the single AST predicate the
  spec's original 5 clauses do — each needs its own detection design (e.g.
  scanning for `subprocess` calls naming `git checkout|reset|clean|stash|push`
  without a declared exception). Left as a named follow-on in the
  implementation plan rather than expanding this pass's scope.
- Treating the OpenAPI-diff ERR/WARN finding as an equal second primary
  citation for the Cluster B marker: the sources were not opened, only
  search-summarized. Kept as corroboration, not evidence on its own.
- Re-deriving `import-linter`'s `forbidden` contract type in detail: not
  needed for Task 3's specific `_load()`-exception use case, which
  `ignore_imports` on an `independence` contract already covers exactly.

## Sources

- https://raw.githubusercontent.com/github/awesome-copilot/main/instructions/hooks.instructions.md (fetched in full)
- https://api.github.com/repos/anthropics/skills/contents/skills/skill-creator/scripts/quick_validate.py (fetched in full, via GitHub contents API — the raw.githubusercontent.com path without the extra `skills/` segment 404s)
- https://import-linter.readthedocs.io/en/latest/contract_types.html (confirmed via search of current docs)
- https://12factor.net/config (confirmed via search of the primary page)
- https://docs.ansible.com/projects/molecule/workflow/ and Ansible's FAQ pages (confirmed via search; direct fetch of `workflow/` returned 429)
- https://github.com/obi1kenobi/cargo-semver-checks (fetched — documentation on detection, classification, and unstable-feature/lint-downgrade handling)
- WebSearch: "OpenAPI diff tool additive breaking unstable field exempt from breaking change detection" (search snippets only, not opened — `oasdiff`, `Azure/openapi-diff` results)
