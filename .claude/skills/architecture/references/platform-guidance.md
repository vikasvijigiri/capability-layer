# Platform-specific design guidance

Read the section matching the request's target platform(s) after Inputs step 1
identifies them, before drafting `design-contract.md`'s Tokens and Components
sections. This file only adds what changes *per platform* — the contract
sections themselves (product feeling, accessibility floor, Design QA) are
platform-agnostic and stay in `design-contract.md`.

## Web

Already the default shape of `design-contract.md` — CSS custom-property
tokens, WCAG AA contrast, keyboard reachability, CSS breakpoints, and
`prefers-reduced-motion` are all written web-first. No separate section
needed here; read the base contract.

## iOS (Apple Human Interface Guidelines)

- **Typography:** use the Dynamic Type scale (`.largeTitle` through
  `.caption2`), not fixed point sizes. Every text style must remain legible at
  the largest accessibility text size.
- **Iconography:** SF Symbols at the matching weight/scale of adjacent text;
  a custom icon must match SF Symbols' optical size and stroke weight.
- **Layout:** respect safe areas and the system's layout margins; do not
  hardcode a status-bar or home-indicator height.
- **Navigation:** state which pattern owns the surface —
  `NavigationStack`/`NavigationLink` for drill-down, `NavigationSplitView` for
  iPad two/three-column, `TabView` for top-level sections. Name the
  transition (push, sheet, full-screen-cover) per screen, not "navigate to X".
- **Components:** prefer native SwiftUI controls (`Button`, `List`, `Form`,
  `Menu`) over recreating platform chrome; a custom control must still expose
  the five interaction states `design-contract.md` requires.
- **Motion:** system-standard spring parameters (`response`/`dampingFraction`)
  over fixed-duration easing; state the reduced-motion fallback explicitly —
  `accessibilityReduceMotion`, not just "disable animation".
- **Accessibility floor, in addition to the base contract:** every interactive
  view has `.accessibilityLabel`/`.accessibilityHint` where the visual label
  alone is insufficient; VoiceOver reading order matches visual order unless a
  named reason overrides it; Dynamic Type tested at the largest
  accessibility size, not just the default.

## Android (Material Design 3)

- **Typography:** the Material 3 type scale (`displayLarge` through
  `labelSmall`) via `MaterialTheme.typography`, not raw `sp` values.
- **Color:** dynamic color (Material You) support is a named decision, not a
  default — state whether the surface adopts the user's system palette or a
  fixed brand palette, and why.
- **Elevation and surface:** use Material 3 tonal elevation (surface color
  shifts), not drop-shadow elevation, unless the project's base contract
  names shadow elevation as the chosen system.
- **Layout:** respect edge-to-edge display and gesture-navigation insets;
  do not hardcode a system-bar height.
- **Navigation:** state which pattern owns the surface — `NavigationBar`
  (bottom, 3-5 top-level destinations), `NavigationRail`/`NavigationDrawer`
  for larger screens, `TopAppBar` variant per screen.
- **Components:** prefer Material 3 Compose components over custom
  recreations; a custom control must still expose the five interaction
  states `design-contract.md` requires, plus Android's ripple/state-layer
  feedback on press.
- **Motion:** name the Material motion scheme (standard, emphasized) and
  token (`MotionScheme.standard().defaultSpatialSpec()` etc.) rather than an
  arbitrary duration; state the reduced-motion fallback via the system
  "remove animations" setting, not just "disable animation".
- **Accessibility floor, in addition to the base contract:** minimum touch
  target 48x48dp; every interactive composable sets `Modifier.semantics`
  with a real content description where the visual label alone is
  insufficient; TalkBack reading order matches visual order unless a named
  reason overrides it.

## Cross-platform note

When one surface spans platforms (a shared design system, or a web app with a
native companion), state per-component which platform owns the canonical
version and which platforms adapt it — do not silently assume web patterns
translate to native chrome, or that a native pattern reads correctly on the
web. Genuinely different platforms; genuinely different conventions.
