# Mobile app builds (iOS + Android) — free tier

- **Use Expo + EAS Build as the default for a React Native mobile app** —
  it is the only credible zero-cost path to a real iOS binary without
  owning Mac hardware (a native Xcode build otherwise requires one).
- **Free tier limits (verified against `expo.dev/pricing`, 2026-08):**
  - 15 Android builds + 15 iOS builds per month
  - 1 build at a time (no concurrency) — a second build queues behind
    the first, which matters for CI timing on a team, not a solo MVP
  - 45-minute build timeout per build — a large native-dependency tree
    can hit this; keep native modules to what the app actually needs
  - EAS Update (over-the-air JS updates, skipping a full store
    resubmission): 1,000 monthly active users free
- **Plan around the 30-builds/month ceiling.** A CI pipeline that
  triggers a build on every push burns the free quota fast — build on
  merge to the release branch, not on every commit, and use `expo start`
  / a local dev client for iteration instead of a full EAS build.
- **App store fees are the one cost this cannot avoid**: Apple Developer
  Program is $99/year, Google Play's one-time registration is $25 — both
  are identity/distribution fees unrelated to build infrastructure, and
  no free tier removes them. Budget for these explicitly; they are not a
  hosting cost this rule can zero out.
