# API Tokens

## Overview

Opaque, randomly generated tokens that authenticate API requests via the `X-API-KEY` header. Each user can have multiple active tokens. The plaintext is returned only once at creation.

Tokens are stored as HMAC-SHA256 hashes in a dedicated `api_token` MongoDB collection. Revoked tokens are kept for audit (soft-delete via `revoked_at`).

## Previous system

The old system generated a JWS (JSON Web Signature) token but never actually verified or decoded it — authentication was a simple string comparison against the `apikey` field stored in plaintext on the `User` document. The JWS format added no security value since it was treated as an opaque string.

- **One key per user**: generating a new key invalidated the previous one, breaking any integration still using it.
- **Plaintext stored in DB**: the token was stored as-is, so a database leak directly exposed all API keys.
- **No revocation or expiration**: the only way to invalidate a key was to generate a new one or delete it, with no audit trail.
- **No usage tracking**: no way to know when or by what a key was last used.

## Design decisions

### HMAC-SHA256 instead of plain SHA-256

A plain hash would let an attacker who obtains a database dump verify token candidates offline. HMAC-SHA256 with a server-side secret (`API_TOKEN_SECRET`) means the DB alone is not enough — the attacker also needs the secret.

A slow hash (bcrypt/argon2) is unnecessary here: tokens have 48 bytes of entropy from `secrets.token_urlsafe`, making brute-force infeasible regardless of hash speed.

### Separate `API_TOKEN_SECRET` instead of reusing `SECRET_KEY`

`SECRET_KEY` is used by Flask for session signing and by Flask-Security for password reset tokens. If a token hash secret needs to be rotated (e.g. suspected leak), rotating `SECRET_KEY` would invalidate all sessions and pending password resets. A dedicated secret allows independent rotation.

### `API_TOKEN_PREFIX` and display prefix

A configurable prefix (default: `udata_`) is prepended to every generated token. This serves two purposes: secret scanning tools (GitHub, GitLeaks, etc.) can detect leaked tokens via pattern matching, and different prefixes per environment (e.g. `udata_prod_`, `udata_demo_`) let users identify which environment a token belongs to.

Since the plaintext is never stored, we also save a `token_prefix`: the first 8 characters of the random part (after the global prefix). This lets users identify which token is which in the UI. The global prefix is not included in `token_prefix` because it's the same for all tokens of a given environment and wouldn't help distinguish them.

### Scope defaults to `admin`

Tokens currently grant full access matching the user's permissions. The scope is `admin` to reflect this reality. When restricted scopes are added (phase 2), new values like `normal` will be introduced with the corresponding permission checks.

### Revocation as soft-delete

Deleting a token marks it as revoked (`revoked_at` timestamp) rather than removing the record from the database. This keeps an audit trail (who created what, when it was revoked). No cleanup job for now (see Future work).

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `API_TOKEN_PREFIX` | `udata_` | Prefix for secret scanning tool detection. |
| `API_TOKEN_SECRET` | *(empty — must be set)* | HMAC key for token hashing. The app refuses to start without it. |

## Migration

The migration `2026-01-28-migrate-apikeys-to-api-tokens.py` hashes each existing `User.apikey` with HMAC-SHA256 into the new collection, then removes the `apikey` field from all user documents.

The migration is idempotent (checks for existing hashes before inserting). Existing API keys continue to work after migration because the same plaintext produces the same HMAC hash.

## Future work

- **Restricted scopes (phase 2)**: add `normal` scope with permission enforcement, so that admin-only endpoints require `scope="admin"` + `is_admin`
- **Refresh tokens**: add `refresh` kind for short-lived JWT access tokens in the SPA
- **Bulk revocation**: `DELETE /api/1/me/tokens/` (all my tokens), admin endpoint for revoking a user's tokens
- **Default expiration**: configurable duration applied when no explicit `expires_at` is provided
- **Token cleanup**: background job to purge revoked and/or expired tokens after a retention period (similar to GitLab's daily cleanup)
