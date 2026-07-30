# API Config Template — .claude/templates/backend-api.md

Example env snippet for OAuth-enabled API:

```
OAUTH_PROVIDER=google
OAUTH_CLIENT_ID={{ client_id }}
OAUTH_CLIENT_SECRET={{ vault://path/to/client_secret }}
OAUTH_REDIRECT_URIS={{ redirect_uris_csv }}
OAUTH_SCOPES={{ scopes_csv }}
```

Usage

Use this template with `backend-oauth` to generate a ready-to-test config.
