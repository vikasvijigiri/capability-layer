# Backend / database / auth — free tier

- **Use Supabase as the default backend-as-a-service** — Postgres database,
  auth, file storage, and edge functions from one free-tier account, not
  four separate vendors to provision, monitor, and keep alive.
- **Free tier limits (verified against `supabase.com/pricing`, 2026-08):**
  - 500 MB database (shared CPU, 500 MB RAM)
  - 50,000 monthly active users on Auth
  - 1 GB file storage
  - 5 GB egress + 5 GB cached egress
  - 500,000 edge-function invocations/month
  - 2 active projects per account
  - **A free project pauses after 7 days of inactivity** — the single
    biggest free-tier gotcha. A demo, an MVP with no traffic over a
    weekend, or a staging project all hit this. Mitigate with a scheduled
    keep-alive ping (a GitHub Actions cron hitting a health endpoint) or
    accept the pause and resume manually before a demo.
- **Do not add a second auth vendor.** Supabase Auth is bundled and free at
  this scale (50K MAU) — a separate service (Clerk, Auth0) adds its own
  free-tier ceiling and its own pause/expiry policy to track for no
  functional gain until traffic outgrows Supabase itself.
- **500 MB is the real constraint**, not the 50K MAU. Plan schema and media
  storage (use Supabase Storage or R2, never inline blobs in Postgres) with
  that ceiling in mind from day one — migrating off a free-tier database
  under real user load is a harder problem than designing around the limit
  up front.
