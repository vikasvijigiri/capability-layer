# Research Capability Package

Purpose: research, discovery, papers, competitive analysis, and sourcing
credible references.

Keywords: research, papers, literature-review, citation, evidence, look into, investigate, compare options, what's the best way, find out, survey, benchmark, competitive analysis, versus, which is faster, which is cheaper

Entry point: load this file for `research` tasks. It lists skills and workflows
for document search, citation extraction, and evidence scoring.

Layout


Routing

Load this index first; prefer a blueprint if one exists, else a workflow, else
compose from the `research-` skills in the Skill tool list. Always run `.claude/validators/research-citation-check.md` before reporting findings.

Skills

The 5 skills for this capability are discoverable Claude Code skills
under `.claude/skills/`, each prefixed `research-`. They are invoked by name via
the Skill tool, not loaded from this directory:

- `research-benchmark-comparison`
- `research-citation-scoring`
- `research-competitive-analysis`
- `research-papers-extraction`
- `research-web-search`

This index still owns routing that a flat skill list cannot express: which
blueprint or workflow takes precedence, and which validator must run before
any side effect is committed.

Artefacts

Canonical copies live in top-level `.claude/` directories, prefixed
`research-`. The copies still under `capabilities/research/` are superseded and
must not be linked to.

- `.claude/validators/` — `research-citation-check`
