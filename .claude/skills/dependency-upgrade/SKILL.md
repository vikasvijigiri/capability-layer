---
name: dependency-upgrade
model: sonnet
description: Plans and executes a dependency or framework version upgrade, reading the breaking changes and staging the work rather than bumping and hoping. Use for "upgrade this", "bump the version", "we are on an old version", "migrate to v3", "update our dependencies", "this package is out of date", "move to the new major", "security patch needs a newer version". Prefer this over changing the version number and running the tests - a passing suite proves the paths you cover still work, not that the upgrade is safe. Do NOT use for adding a new dependency; that is a stack-selector decision.
effort: medium
---

# Dependency Upgrade

## Steps

1. **Read the changelog between the versions you are actually crossing** - every major in
   between, not just the target. Skipped majors stack their breaking changes.
2. **List the breaking changes that apply to this codebase.** Most will not. Grep for each
   removed or renamed API rather than assuming.
3. **Check transitive impact.** A major bump often forces peer dependencies up with it;
   that is usually the larger part of the work and the part that surprises people.
4. **Establish the baseline** - full suite green *before* the bump, output recorded. An
   upgrade started from a red suite cannot be evaluated.
5. **Upgrade one dependency at a time** where possible. Simultaneous bumps make attribution
   impossible when something breaks.
6. **Run the suite, then check what the suite does not cover.** Untested paths are exactly
   where an upgrade breaks silently - name them explicitly as unverified.
7. **Security check** the new versions via `security-dependency-audit` - upgrades can
   introduce advisories as well as resolve them.

## Rules

- **Never use the lockfile as the edit surface.** Change the manifest and let the package
  manager regenerate; the `pre-edit` guard blocks lockfile edits for this reason.
- **A green suite is necessary, not sufficient.** Say plainly which behaviour was verified
  by execution and which by inspection.
- Record the reason for a pinned or held-back version - an unexplained pin becomes
  permanent.
