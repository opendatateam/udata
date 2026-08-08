# Géoplateforme integration

udata can synchronise resources (`gpkg` by default, see `GEOPF_PUSHABLE_FORMATS`) to the IGN [Géoplateforme](https://geoplateforme.fr/) entrepôt, making them available as vector tiles on [cartes.gouv.fr](https://cartes.gouv.fr), on demand from the frontend (cdata) and on behalf of the user who triggers it.

Two independent flows, each triggered explicitly by a user, each running as its own Celery task:

- **Push**: data.gouv.fr → Géoplateforme. Uploads a resource and its metadata.
- **Pull**: Géoplateforme → data.gouv.fr (the "reverse sync"). Reads back the OGC services (offerings) a user configured on cartes.gouv.fr for a pushed dataset, and mirrors them as resources.

## Data model mapping

| data.gouv.fr | Géoplateforme |
|---|---|
| Dataset | Fiche de données (`datasheet_name = dataset.id`) |
| Resource | Stored data (`stored_data` name = `resource.id`) |
| Dataset metadata | ISO 19115 metadata (one per fiche) |

All entrepôt entities belonging to the same fiche (uploads, stored data, metadata) carry the same `datasheet_name` tag so the platform groups them correctly.

**Multiple resources of the same dataset** each get their own `stored_data` (different names), but the shared `datasheet_name` tag is what groups them back under one fiche despite that, and they share a single ISO 19115 metadata document, `sync_metadata` updating the existing `geopf:push:metadata-id` from the second push onward instead of duplicating it.

**A dataset lives in exactly one entrepôt:** the frontend lets the user pick one (via `GET /api/1/geopf/datastores/`) and passes it explicitly as `datastore_id` on the dataset's first push; it's stored as `geopf:push:datastore-id` (dataset extra) once that push succeeds (a failed push doesn't pin anything), then reused as-is by every later push of that dataset, matching how geopf itself scopes a fiche to one entrepôt.

## Authentication

udata calls the entrepôt API **as the data.gouv.fr user who asks for it**. This is a per-user OAuth 2.0 `authorization_code` link (udata is a confidential OIDC client of geopf's Keycloak), driven by the frontend (cdata). There is no anonymous route into the entrepôt API and no service-account credential; this applies equally to push and pull, neither has an unauthenticated path.

| Step | Call | Kind |
|---|---|---|
| Check link status | `GET /api/1/geopf/status/` | JSON |
| Start the OAuth link | `GET /api/1/geopf/login/?dataset_id=<id>` | browser navigation, requires an existing udata session |
| OAuth callback | `GET /api/1/geopf/auth` | browser navigation; exchanges the code, persists the token, redirects back to the dataset's cdata admin geopf page |
| Disconnect | `DELETE /api/1/geopf/token/` | JSON |
| List available entrepôts | `GET /api/1/geopf/datastores/` | JSON |

Tokens are stored per user (`GeopfToken`, one document per user, `access_token`/`refresh_token` encrypted at rest with Fernet; see `GEOPF_TOKEN_ENCRYPTION_KEY`), refreshed automatically before use when expired. Both access and refresh tokens currently live 12h on sso.geopf.fr; the push task additionally refreshes proactively when the token wouldn't outlive the pipeline's worst-case duration (two poll timeouts), so long polls can't outrun it.

`/status/` reflects usability, not just presence: it attempts a refresh if the access token is expired (refreshing it as a side effect) and only reports `connected: false` if that fails, meaning the refresh token is also dead and the user needs to reconnect.

`/token/` (disconnect) revokes the refresh token at sso.geopf.fr before deleting the local `GeopfToken`, so a leaked token can't still be used against the geopf API after the user disconnects. Revocation is best-effort: if the IdP is unreachable, the failure is only logged and the local link is removed regardless.

Datastores are discovered by`/datastores/`  via `GET {GEOPF_API_BASE}/users/me`, whose `communities_member[]` each carry a `community.datastore` id and a `rights` array (`COMMUNITY`, `PROCESSING`, `ANNEX`, `BROADCAST`, `UPLOAD`). Only memberships with `UPLOAD` + `PROCESSING` + `BROADCAST` together are returned, since those are exactly the rights the push pipeline needs (upload, vector integration, and a visible offering); anything less can't complete a push.

The login endpoint takes a `dataset_id`, not a redirect path, to avoid open redirect concerns. The callback resolves it server-side to the dataset's admin geopf page (`/admin/datasets/<id>/geopf`), falling back to the homepage if it's missing or unknown.

If there is no token or the refresh fails, calls raise `GeopfReauthRequired`, surfaced by the API as `424` so the frontend can prompt the user to (re)connect. This is the same for both push and pull. This "custom" code (`424`) is used to make it easy for the frontend to distinguish between udata-related (`40x`) failures and upstream ones.

## State tracking

Both push and pull follow the same two-level pattern:

- **Extras**: essential fields written at each lifecycle transition. Persist in MongoDB independently of Celery, so they survive broker restarts and result-backend expiry. The primary surface for the API consumer.
- **Celery results**: the full execution record (return value, exception, traceback, timing) of the task, stored by `ignore_result=False`. Useful for debugging failures. Retrieve via `GET /api/1/workers/tasks/{task_id}/`, using the task-id extra as the bridge between the two layers.

Each flow's specific extras keys are listed in its own section below.

## Push: data.gouv.fr → Géoplateforme

Triggered explicitly by the user via `POST /api/1/geopf/push/<dataset_id>/<resource_id>/` (only offered for resources whose format is in `GEOPF_PUSHABLE_FORMATS`): `202` + Celery task id, or `424` if not connected. Runs as a Celery task.

### Workflow

1. **Download**: fetch the file from storage (local) or remote URL into a temp file; compute MD5.
2. **Upload (livraison)**: create an upload, push the file and its MD5 checksum, close the upload.
3. **Wait for checks**: poll `/uploads/{id}/checks` until `asked` and `in_progress` are empty; fail if any check fails.
4. **Tag upload**: attach `datasheet_name` tag so the upload is associated with the fiche.
5. **Processing**: discover the datastore's registered "vector integration" processing (`GET /datastores/{datastore}/processings`, matched by type: input accepts a `VECTOR` upload, output is a `VECTOR-DB` stored_data), launch it, poll until `SUCCESS`.
6. **Delete upload**: clean up the livraison once processing has consumed it.
7. **Tag stored data**: attach `datasheet_name` tag to the resulting stored data.
8. **Metadata**: generate ISO 19115 XML from the dataset and push it:
   - If `geopf:push:metadata-id` is already in dataset extras: update the existing metadata record.
   - Otherwise: upload (with 409 upsert fallback), tag, and store the ID in extras.

On any failure the task attempts to delete the livraison to avoid orphaned uploads, then re-raises so the error is visible in Celery.

### State tracking

#### Push resource extras

Set on the original pushed resource by the push pipeline.

| Key | Values / type | Description |
|---|---|---|
| `geopf:push:status` | `pending` \| `done` \| `error` \| `timeout` | Lifecycle state of the push. Set to `pending` when the task starts, updated on completion or failure. |
| `geopf:push:task-id` | Celery task UUID | ID of the Celery task running this push. Set when the task starts. Query via `GET /api/1/workers/tasks/<id>/` for status and traceback. |
| `geopf:push:stored-data-id` | UUID string | Entrepôt stored data ID produced by the pipeline. Used by the pull flow to discover offerings. |
| `geopf:push:last-synced-at` | ISO 8601 | Timestamp of the last successful push. |
| `geopf:push:error` | string | Error message from the last failed attempt. Only present on `error` or `timeout` status. |

#### Push dataset extras

| Key | Type | Description |
|---|---|---|
| `geopf:push:datastore-id` | UUID string | Entrepôt (datastore) this dataset is pushed into. Set on the dataset's first *successful* push, reused as-is by every later push. |
| `geopf:push:metadata-id` | UUID string | Entrepôt metadata record ID. Stored after the first successful metadata upload to avoid re-creating the record on subsequent pushes. |
| `geopf:push:fiche-url` | URL | Direct link to the dataset's fiche on cartes.gouv.fr. Set after the first successful push of any resource. |

### ISO 19115 metadata

One metadata document is generated per dataset (not per resource) and pushed as `ISOAP` to the entrepôt.

| ISO 19115 field | Source |
|---|---|
| `fileIdentifier` | `dataset.id`, prefixed `SANDBOX_` when pushing to `SANDBOX_DATASTORE_ID` (see Limitations) |
| `organisationName` (metadata contact + data contact) | `dataset.organization.name` or `dataset.owner.fullname` |
| `electronicMailAddress` (metadata contact + data contact) | First `dataset.contact_points` entry with an email; omitted if none, see note below |
| `pointOfContact` in `identificationInfo` | Org name + email (omitted if no org/owner) |
| `dateStamp` | `dataset.last_modified` |
| `title` | `dataset.title` |
| `date` (creation) | `dataset.created_at` |
| `abstract` | `dataset.description`, falls back to `dataset.title` |
| `keywords` | `dataset.tags` |
| `topicCategory` | First `dataset.tags` entry matching a known ISO 19115 topic category keyword; omitted if no match |
| Bounding box | Computed from `dataset.spatial.geom` (raw MultiPolygon only); omitted if unavailable |
| `language` | Hardcoded `fre` |
| `hierarchyLevel` | Hardcoded `dataset` |

> **Note:** cartes.gouv.fr displays `hierarchyLevel=dataset` as "Lot" in its UI. This is the platform's own French label for dataset-level metadata, not an error.

## Pull: Géoplateforme → data.gouv.fr (reverse sync)

An *offering* is Géoplateforme's term for an OGC service endpoint (WFS, WMS, WMTS, TMS, …) derived from stored data. Once a resource has been pushed, a user can create a service for it through the cartes.gouv.fr dashboard; the pull flow reads those offerings back and mirrors them as resources in udata.

Triggered explicitly via `POST /api/1/geopf/pull-offerings/<dataset_id>/`, as the current user: `202` + Celery task id, or `424` if not connected. Runs as a Celery task, same pattern as push.

### Workflow

1. Resolve the dataset's datastore (`geopf:push:datastore-id` dataset extra; datasets with no pin yet are skipped), and collect `geopf:push:stored-data-id` from each of its push resources.
2. For each stored data id, query `GET /datastores/{datastore_id}/offerings?stored_data={stored_data_id}`.
3. For each offering: create a new resource if none with matching `geopf:offering:id` exists, or update the URL if it changed.
4. Remove any resources whose `geopf:offering:id` no longer appears in the live offering set.

### State tracking

#### Pull dataset extras

| Key | Values / type | Description |
|---|---|---|
| `geopf:pull:status` | `pending` \| `done` \| `error` | Lifecycle state of the pull. Set to `pending` when the task starts, updated on completion or failure. |
| `geopf:pull:task-id` | Celery task UUID | ID of the Celery task running the pull. Query via `GET /api/1/workers/tasks/<id>/` for status and traceback. |
| `geopf:pull:last-synced-at` | ISO 8601 | Timestamp of the last successful pull. |
| `geopf:pull:error` | string | Error message from the last failed pull. Only present on `error` status. |

#### Offering resource extras

Set on resources created (or updated) by the pull flow. These resources are distinct from the original push resource.

| Key | Type | Description |
|---|---|---|
| `geopf:offering:id` | UUID string | Entrepôt offering ID. Primary key used to match existing resources on subsequent syncs. |
| `geopf:offering:last-synced-at` | ISO 8601 | Timestamp of the last sync that observed this offering. |

## CLI

### Push

```
udata geopf push-resource <dataset_id> <resource_id> (--user-id <id> | --token <token>) [--datastore-id <id>]
```

Runs the full upload pipeline synchronously for a single resource, same path as the Celery task. `--user-id` uses that user's stored `GeopfToken` (refreshed as needed); `--token` bypasses stored-token resolution entirely with a raw access token, for ops/debugging. `--datastore-id` is required unless the dataset already has one pinned. Useful for retrying after a timeout or failure. If the previous attempt left a livraison on Géoplateforme, delete it via the cartes.gouv.fr UI before retrying.

```
udata geopf push-metadata <dataset_id> (--user-id <id> | --token <token>) [--datastore-id <id>]
```

Pushes or refreshes the ISO 19115 metadata for a dataset without triggering a full resource upload. Same `--user-id`/`--token`/`--datastore-id` options as `push-resource`. Useful for iterating on metadata content or fixing a metadata record after a failed pipeline run. Prints the metadata ID and fiche URL on success.

### Pull

```
udata geopf pull-offerings <dataset_id> (--user-id <id> | --token <token>)
```

Pulls live offerings from Géoplateforme and syncs them as resources for the given dataset, against the dataset's own `geopf:push:datastore-id` (no-op if the dataset has no pinned datastore). Same `--user-id`/`--token` options as `push-resource`. Prints the count of live offerings found. Useful for triggering an immediate pull or verifying the pull logic.

## Configuration

```python
GEOPF_API_BASE = "https://data.geopf.fr/api"  # default
GEOPF_DASHBOARD_BASE = "https://cartes.gouv.fr"  # default, used to build fiche URLs

# Resource formats eligible for push. Only gpkg is actually processed today
# (SRS detection is gpkg-specific, see Limitations), so adding a format here
# without matching support in udata/geopf/srs.py would fail at upload time.
GEOPF_PUSHABLE_FORMATS = frozenset({"gpkg"})  # default

# Maximum size (bytes) of a remote resource file downloaded for a push
GEOPF_MAX_REMOTE_FILE_SIZE = 1_000_000_000  # default, 1 GB

# OAuth2/OIDC client registration against geopf's Keycloak
GEOPF_OAUTH_CLIENT_ID = "<confidential client id>"
GEOPF_OAUTH_CLIENT_SECRET = "<confidential client secret>"
GEOPF_OAUTH_OPENID_CONF_URL = "https://sso.geopf.fr/realms/geoplateforme/.well-known/openid-configuration"  # default
GEOPF_OAUTH_SCOPE = "openid"  # default

# Fernet key used to encrypt GeopfToken.access_token/refresh_token at rest
GEOPF_TOKEN_ENCRYPTION_KEY = "<fernet key>"
```

The plugin is registered as a udata entry point (`udata.plugins`) and activated by adding `geopf` to the `PLUGINS` list. Note that the API endpoints (`udata/geopf/api.py`) are always registered as a core namespace, regardless of plugin activation; only the OAuth client registration and the config-gated behavior are conditional.

## Limitations

- Only formats listed in `GEOPF_PUSHABLE_FORMATS` are synchronised (`gpkg` by default); other formats are silently skipped. SRS detection (`udata/geopf/srs.py`) only supports `gpkg` today, so adding a format to the setting alone isn't enough to actually push it.
- Updates to an existing pushed resource are not yet handled: a resource can only be pushed once via `POST /api/1/geopf/push/<dataset_id>/<resource_id>/`.
- SRS is auto-detected from the file before upload. GeoPackage reads the WKT definition from `gpkg_spatial_ref_sys` (via sqlite3 + pyproj). Other vector formats (Shapefile via `.prj`, GeoJSON/KML/KMZ/GPX which are always WGS 84) and raster formats (GeoTIFF via rasterio) can be added to `udata/geopf/srs.py` without changing the pipeline.
- Bounding box is only extracted from raw `dataset.spatial.geom`; zone-based spatial coverage (the common case) has no stored geometry in udata and produces no extent in the metadata.
- `topicCategory` is inferred from free-form tags via a keyword mapping; it will often be absent and is never guaranteed to be accurate.
