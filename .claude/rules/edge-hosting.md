# Web hosting / CDN / object storage — free tier

- **Use Cloudflare as the default for hosting, CDN, and object storage** —
  Pages/Workers for compute, R2 for files, free DNS/SSL/CDN, one vendor
  instead of three.
- **Why Cloudflare over a traditional free-tier server (Render, Koyeb,
  Railway):** those sleep the app when idle and pay a real cold-start
  penalty on the next request — acceptable for a demo, not for a
  production app a real user might hit first thing. Cloudflare's edge
  model has no idle-sleep state.
- **The real constraint this trades in:** Workers run on the Workers
  runtime, not a persistent Node process — a long-running connection,
  a native binary dependency, or a framework that assumes a traditional
  server needs an edge-compatible runtime (Hono, Next.js's edge runtime,
  itty-router) or a different architecture. Confirm the framework choice
  supports this **before** committing to the hosting choice, not after.
- **R2 object storage free tier:** 10 GB-month storage, 1M Class A
  operations/month, 10M Class B operations/month, **zero egress fees on
  any storage class** — the actual differentiator over S3-compatible
  alternatives, which meter egress by the GB.
- **If the app genuinely needs a persistent Node server** (a long-lived
  WebSocket, a background worker that can't be a Cloudflare Worker/Durable
  Object), accept Render's free tier and its cold start explicitly — do
  not silently ping it awake with a cron job to defeat the sleep policy,
  which is a fair-use violation on most free tiers, not a solution.
