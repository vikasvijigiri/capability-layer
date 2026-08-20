# Skill-quality digest: capability-layer-maintenance vs affaan-m/ECC

Date: 2026-08-19
Ours: `.claude/skills/capability-layer-maintenance/SKILL.md` (119 lines)
Comparable: `affaan-m/ECC`, `skills/skill-stocktake/SKILL.md` (audits Claude
skills/commands for quality; Quick Scan / Full Stocktake, verdict-driven,
script-backed inventory). Six ECC files were read in full before choosing it —
`skills/ecc-guide/SKILL.md`, `skills/configure-ecc/SKILL.md`,
`skills/skill-comply/SKILL.md`, `skills/rules-distill/SKILL.md`,
`skills/hookify-rules/SKILL.md`, `commands/harness-audit.md` — because
skill-stocktake is the only one whose job is auditing-and-repairing the agent
layer's own skills/commands, closest to our scope (which additionally covers
hooks, agents, CLAUDE.md, AGENTS.md, harnesses.json).

## Gaps in ours (with fixes)

1. **No worked example anywhere, and no good/bad calibration.** Our Procedure
   (lines 56–95) states five abstract steps ("record the reason for the
   latter," "include before/after counts") with no filled instance of any of
   it. skill-stocktake's Phase 2 gives explicit good/bad pairs for its
   `reason` field, e.g. Bad: `"Superseded"` vs Good: `"disable-model-invocation:
   true already set; superseded by continuous-learning-v2 which covers all the
   same patterns plus confidence scoring. No unique content remains."`
   `rules-distill/SKILL.md` goes further with a full filled end-to-end
   transcript (scan output → subagent batches → summary table → user
   approves/skips by number → applied results). Fix: add one filled
   Inventory→Compare→Repair→Record trace to our skill, plus a bad/good pair
   for the "record the reason" line in step 2.

2. **No enumerated verdict taxonomy for step 2 (Compare).** skill-stocktake
   names five verdicts with definitions (Keep/Improve/Update/Retire/`Merge
   into [X]`) and a rule for what makes a Retire or Merge reason acceptable.
   Our step 2 only says "Separate a real deviation from an intentional
   extension" — no enumerated categories, so two reviewers could disagree on
   what counts as a deviation worth repairing versus recording. Fix: name the
   possible outcomes of Compare (e.g. drift/intentional-extension/stale
   reference/duplicate-source) the way skill-stocktake names its verdicts.

3. **Inventory step has no named command, unlike skill-stocktake's `scan.sh`.**
   skill-stocktake's Phase 1 runs `scripts/scan.sh`, which mechanically
   enumerates skill files and mtimes and prints a scan-summary table
   (`✓ ~/.claude/skills/ (17 files)`). Our step 1 ("Count and inspect the
   canonical directories... Search for deleted paths, duplicate sources,
   stale counts") is prose-only — it never names a script or command to run,
   even though this repo already has `tools/` scripts elsewhere. Fix: point
   Inventory at a concrete command (or note explicitly that none exists yet).

4. **Verify step's own text drops the scoped command it names.** Step 4 says
   "Run the scoped validator first, then the complete repository suite" but
   the code block underneath shows only `python tools/run_checks.py --tier
   all --require-test` — the scoped command (`--scoped`, per CLAUDE.md) is
   never actually written out. skill-stocktake's two-tier design (Quick
   Scan vs Full Stocktake) states both invocations explicitly. Fix: add the
   `--scoped` line before the `--tier all` line.

## Where ours is better

1. **Tool-enforced boundary, not prose-only.** `tools/test_process_router.py`
   (verified: lines 1273–1278) asserts `capability-layer-maintenance` names
   `no-slop` and vice versa — a real test fails if either skill's prose drops
   the cross-reference. None of the six ECC files carry an equivalent
   test-backed boundary; skill-stocktake's scope section ("targets the
   following paths") and rules-distill's phase boundaries are prose-only,
   nothing fails a build if they drift.

2. **Explicit hook-authorship guardrail with a named failure mode.** Our
   "Hook contract" section (lines 96–107) forbids hooks from authoring
   strategic content in named files and requires a docstring+test-declared
   behavior classification (detect drift / enforce safety / record state /
   never author strategic content). None of the six ECC files — including
   `hookify-rules/SKILL.md`, which documents hook *syntax* in detail — address
   this specific risk (a hook silently rewriting CLAUDE.md/README/decisions).

3. **`allowed-tools` restriction in frontmatter.** Ours declares
   `allowed-tools: Read Grep Glob Bash`, mechanically limiting what the skill
   can invoke. Of the six ECC files, only `skill-comply` declares an
   equivalent `tools:` restriction; `skill-stocktake`, `rules-distill`,
   `ecc-guide`, `configure-ecc`, and `hookify-rules` declare none.

## Verdict

skill-stocktake is more teachable (verdict taxonomy, good/bad reason
calibration, one real script-backed inventory step) while
capability-layer-maintenance is more mechanically enforced (test-pinned
cross-skill boundary, tool allowlist, an explicit anti-pattern guardrail for
hooks) — the same asymmetry the writing-plans/ECC pass found: ECC's skills
teach by example, ours constrains by mechanism, and each is missing a real
piece of the other.
