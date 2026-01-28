# API Tokens

## Overview

API tokens are opaque, randomly generated strings that authenticate API requests via the `X-API-KEY` header. Tokens are stored as HMAC-SHA256 hashes (keyed with `API_TOKEN_SECRET`) in a dedicated `api_token` MongoDB collection. The plaintext token is returned only once at creation and cannot be retrieved afterwards.

Each user can have multiple active tokens simultaneously.

## Architecture

### Token generation

1. A random token is generated using `secrets.token_urlsafe(48)`
2. A configurable prefix is prepended (setting `API_TOKEN_PREFIX`, default: `udata_`)
3. The full plaintext token is hashed with HMAC-SHA256 using `API_TOKEN_SECRET` as key
4. The hash, a display prefix (first 8 chars of the random part), and metadata are stored in the `api_token` collection
5. The plaintext is returned once in the creation response and never stored

### Authentication flow

1. Client sends `X-API-KEY: <plaintext_token>` header
2. Server computes HMAC-SHA256 of the token using `API_TOKEN_SECRET`
3. Lookup in `api_token` collection by hash (must not be revoked or expired)
4. If found, `login_user(token.user)` and update usage metadata (last_used_at, user_agents)

HMAC-SHA256 is used instead of plain SHA-256 so that a database leak alone is not enough to verify token candidates — the attacker also needs `API_TOKEN_SECRET`. A slow hash (bcrypt/argon2) is unnecessary because the tokens have high entropy (48 bytes from `secrets.token_urlsafe`), making brute-force infeasible regardless.

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `API_TOKEN_PREFIX` | `udata_` | Prefix prepended to generated tokens. Useful for secret scanning tools (e.g., GitHub, GitLeaks) to identify leaked tokens. |
| `API_TOKEN_SECRET` | *(empty – must be set)* | HMAC key used to hash tokens before storage. Must be set to a unique, random value per environment. The app will refuse to start if this is not configured. |

## API Endpoints

### `GET /api/1/me/tokens/`

List all active (non-revoked) tokens for the authenticated user.

Response: array of token objects (without plaintext or hash).

### `POST /api/1/me/tokens/`

Create a new API token. The plaintext token is included in the response **only this one time**.

Request body (all optional):
- `name`: a label to identify the token (e.g., "CI pipeline")
- `expires_at`: ISO 8601 expiration date

Response (201): token object with additional `token` field containing the plaintext.

### `DELETE /api/1/me/tokens/<id>/`

Revoke a token. The token record is kept in database for audit purposes but is marked as revoked and will no longer authenticate.

Response: 204 on success, 404 if the token doesn't exist or is already revoked.

## ApiToken model fields

| Field | Description |
|-------|-------------|
| `token_hash` | HMAC-SHA256 hash (not exposed via API) |
| `token_prefix` | First 8 chars of the random part, for display/identification |
| `user` | Reference to the User (not exposed via API) |
| `name` | User-given label |
| `scope` | Token scope (currently: `admin` — full access) |
| `kind` | Token type (currently: `api_key`) |
| `created_at` | Creation timestamp |
| `last_used_at` | Last authentication timestamp |
| `user_agents` | List of User-Agent strings that used this token (capped at 20) |
| `revoked_at` | Revocation timestamp (null if active) |
| `expires_at` | Expiration timestamp (null if no expiration) |

## Migration

The migration `2026-01-28-migrate-apikeys-to-api-tokens.py`:

1. Hashes each existing `user.apikey` (JWS token) with HMAC-SHA256 (using `API_TOKEN_SECRET`)
2. Creates a corresponding `api_token` document with `name="Migrated API key"`
3. Removes the `apikey` field from all user documents

The migration is idempotent (checks for existing hashes before inserting).

**Important**: existing API keys continue to work after migration because the same plaintext sent in `X-API-KEY` will produce the same HMAC-SHA256 hash (as long as `API_TOKEN_SECRET` hasn't changed).

## Future work

### Restricted scopes (phase 2)

The `scope` field currently defaults to `admin` (full access, matching user permissions). Planned additions:
- `normal` scope: restricted to non-admin endpoints
- Store the scope in `flask.g.token_scope` during authentication
- Enforce in `_apply_secure`: admin routes require `scope="admin"` + user `is_admin`
- Admins with a `normal`-scoped token should not bypass ownership checks

### Refresh tokens (phase 2+)

The `kind` field currently only has `api_key`. Planned:
- `refresh` kind for short-lived JWT access tokens in the SPA
- Refresh token flow: exchange refresh token for a new short-lived JWT

### Bulk revocation

- `DELETE /api/1/me/tokens/` (without id): revoke all tokens for current user
- Admin endpoint `DELETE /api/1/users/<id>/tokens/`: revoke all tokens for a given user

### Default expiration

Configurable default expiration duration in settings, applied when no explicit `expires_at` is provided.
