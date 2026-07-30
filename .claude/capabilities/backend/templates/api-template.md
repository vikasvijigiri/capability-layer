> **Superseded.** The canonical copy of this file is `.claude/templates/backend-api.md`.
> This copy is kept for history only — do not edit it, and do not link to it.
> References were migrated on 2026-07-30.

# API Config Template — backend/templates/api-template.md

Example env snippet for OAuth-enabled API:

```
OAUTH_PROVIDER=google
OAUTH_CLIENT_ID={{ client_id }}
OAUTH_CLIENT_SECRET={{ vault://path/to/client_secret }}
OAUTH_REDIRECT_URIS={{ redirect_uris_csv }}
OAUTH_SCOPES={{ scopes_csv }}
```

Usage

Use this template with `oauth-skill` to generate a ready-to-test config.
