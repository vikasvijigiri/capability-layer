---
name: accessibility-audit
description: Keyboard access, semantics, focus, contrast, text scaling, forms, screen readers, alt text, motion, touch targets, error recovery. For UI changes, design QA, accessibility regressions, release gates. Do NOT use an automated scan alone as proof.
when_to_use: when a user-facing interface needs accessibility evidence or remediation
effort: high
model: sonnet
disable-model-invocation: false
---

# Accessibility Audit

Combine automated checks with keyboard and assistive-technology reasoning. Fix
the user's path, not only the reported rule.

## Audit sequence

1. Identify supported platforms, browsers, assistive technologies, input
   methods, language, zoom/text scaling, and critical user journeys.
2. Inspect semantics: landmarks, heading order, names/roles/values, labels,
   descriptions, relationships, live regions, and table structure.
3. Test keyboard-only flow: reachability, order, visible focus, skip links,
   dialogs, menus, traps, escape behavior, drag alternatives, and error return.
4. Check contrast against actual backgrounds, text resize, reflow, target size,
   focus contrast, color-independent meaning, and forced-colors behavior.
5. Check images, icons, media, language, validation, loading, empty, error,
   permission, and success states. Verify reduced-motion behavior.
6. Run available automated tools, then manually verify every critical journey.
   Record tool/version, scope, false positives, and untested surfaces.

## Severity

Block release for inaccessible critical journeys, keyboard traps, missing names
for essential controls, unusable errors, or content that cannot be perceived or
operated. Rank other findings by user impact and frequency.

## Evidence

Record URL/component, steps, expected/actual behavior, affected users, tool
output, screenshots or recordings where permitted, and a regression test or
manual test case for each fix.

## Next step

Hand UI fixes to `architecture`, built test-first per
`.claude/skills/implementation/references/test-driven-development.md`; hand final evidence
to `testing` and `code-review`.

## Routing

- Enter for any user-facing UI change or accessibility release gate.
- Pair with `architecture` when tokens, states, or interaction rules are missing.
- Do not use as a substitute for product research with users with disabilities.

## Success

Critical journeys work with keyboard and supported assistive technology, the
automated and manual evidence is recorded, fixes have regression coverage, and
remaining exceptions have owners and dates.
