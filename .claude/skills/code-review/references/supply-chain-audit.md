---
name: supply-chain-audit
description: Audit dependencies and the build chain for vulnerable or unpinned packages, lockfile drift, unsafe scripts, provenance gaps, license conflicts, secret exposure and CI tampering. Before release or after dependency changes. Do NOT use as a replacement for a full application security review.
when_to_use: when dependency, build, CI, package, or provenance risk needs review
effort: high
model: sonnet
disable-model-invocation: false
---

# Supply-Chain Audit

Audit what enters the product, how it is resolved, how it executes, and how it
is promoted. Prefer repository-native scanners and lockfile evidence over prose.

## Audit order

1. Inventory manifests, lockfiles, registries, package managers, images, build
   tools, GitHub Actions, plugins, and generated artifacts.
2. Check direct and transitive vulnerabilities using the ecosystem's supported
   audit command. Record tool version, database date, scope, and exceptions.
3. Compare manifests to lockfiles and verify reproducible resolution, integrity
   hashes, registry sources, and expected platform-specific variants.
4. Inspect install, build, test, and release scripts for arbitrary execution,
   curl-to-shell behavior, mutable tags, untrusted pull requests, and secret
   exposure.
5. Review license obligations, package ownership, maintainer changes, typosquat
   risk, abandoned dependencies, and provenance/attestation availability.
6. Rank findings by exploitability, blast radius, reachability, and remediation
   reversibility. Give an exact upgrade, pin, removal, isolation, or exception.

## Release blockers

Block release for exploitable reachable vulnerabilities, lockfile drift,
unreviewed install scripts, leaked credentials, untrusted CI write access,
unknown registry provenance for production artifacts, or an unexplained license
conflict. A documented risk acceptance needs owner, expiry, scope, and mitigation.

## Evidence

Record commands, outputs, dependency paths, advisory identifiers, and the exact
artifact or commit inspected. Do not report a clean supply chain because one
scanner passed.

## Next step

Route code changes to `test-driven-development` and `verifying-work`; route
release blockers to `systematic-debugging` and `releasing` after remediation.

## Routing

- Enter after dependency or CI changes, before release, or when provenance is
  uncertain.
- Pair with `security-review` for trust-boundary analysis.
- Do not use for a narrow application vulnerability review alone.

## Success

The dependency and build inventory is complete, reproducibility and provenance
are evidenced, findings are ranked, and every exception has an owner and expiry.
