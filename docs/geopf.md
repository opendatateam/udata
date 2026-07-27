# Géoplateforme integration

udata can synchronise GeoPackage (`.gpkg`) resources to the IGN [Géoplateforme](https://geoplateforme.fr/) entrepôt, making them available as vector tiles on [cartes.gouv.fr](https://cartes.gouv.fr), on demand from the frontend (cdata) and on behalf of the user who triggers it.

## Data model mapping

| data.gouv.fr | Géoplateforme |
|---|---|
| Dataset | Fiche de données (`datasheet_name = dataset.id`) |
| Resource (gpkg) | Stored data (`stored_data` name = `resource.id`) |
| Dataset metadata | ISO 19115 metadata (one per fiche) |

All entrepôt entities belonging to the same fiche (uploads, stored data, metadata) carry the same `datasheet_name` tag so the platform groups them correctly.

## Authentication

udata calls the entrepôt API **as the data.gouv.fr user who asks for it**, not as a shared service identity — géoplateforme grants access according to that user's own rights on the platform. This is a per-user OAuth 2.0 `authorization_code` link (udata is a confidential OIDC client of geopf's Keycloak, `sso.geopf.fr`, realm `geoplateforme`), driven by the frontend (cdata):

| Step | Call | Kind |
|---|---|---|
| Check link status | `GET /api/1/geopf/status/` | JSON |
| Start the OAuth link | `GET /api/1/geopf/login/?dataset_id=<id>` | browser navigation, requires an existing udata session |
| OAuth callback | `GET /api/1/geopf/auth` | browser navigation; exchanges the code, persists the token, redirects back to the dataset's cdata page |
| Disconnect | `DELETE /api/1/geopf/token/` | JSON |
| List available entrepôts | `GET /api/1/geopf/datastores/` | JSON |
| Trigger a push | `POST /api/1/geopf/push/<dataset_id>/<resource_id>/` | JSON, 202 + Celery task id, or 409 if not connected |

Tokens are stored per user (`GeopfToken`, one document per user, `access_token`/`refresh_token` encrypted at rest with Fernet — see `GEOPF_TOKEN_ENCRYPTION_KEY`), refreshed automatically before use when expired. If there is no token or the refresh fails, calls raise `GeopfReauthRequired`, surfaced by the API as `409` so the frontend can prompt the user to (re)connect.

The login endpoint takes a `dataset_id`, not a redirect path — the callback resolves it to the dataset's cdata page itself (`Dataset.self_web_url()`), falling back to the homepage if it's missing or unknown. This means the client can never influence the actual redirect target, so there is no open-redirect surface to defend.

The periodic reverse sync (below) is a background job with no per-user identity to authenticate as, so it keeps using a separate, static `GEOPF_TOKEN` service-account bearer token — the push flow above is the only part that moved to per-user OAuth.

## Workflow

Triggered explicitly by the user via `POST /api/1/geopf/push/<dataset_id>/<resource_id>/` (only offered for `gpkg` resources). Runs as a Celery task.

1. **Download** — fetch the file from storage (local) or remote URL into a temp file; compute MD5.
2. **Upload (livraison)** — create an upload, push the file and its MD5 checksum, close the upload.
3. **Wait for checks** — poll `/uploads/{id}/checks` until `asked` and `in_progress` are empty; fail if any check fails.
4. **Tag upload** — attach `datasheet_name` tag so the upload is associated with the fiche.
5. **Processing** — launch the vector integration processing job; poll until `SUCCESS`.
6. **Delete upload** — clean up the livraison once processing has consumed it.
7. **Tag stored data** — attach `datasheet_name` tag to the resulting stored data.
8. **Metadata** — generate ISO 19115 XML from the dataset and push it:
   - If `geopf:push:metadata-id` is already in dataset extras: update the existing metadata record.
   - Otherwise: upload (with 409 upsert fallback), tag, and store the ID in extras.

On any failure the task attempts to delete the livraison to avoid orphaned uploads, then re-raises so the error is visible in Celery.

## State tracking

State is tracked at two levels that complement each other:

- **Resource/dataset extras** — essential fields written at each lifecycle transition. Persist in MongoDB independently of Celery, so they survive broker restarts and result-backend expiry. The primary surface for the API consumer: a quick `GET /api/1/datasets/{id}/` shows the current status of every push resource without touching Celery.
- **Celery results** — the full execution record (return value, exception, traceback, timing) stored by `ignore_result=False`. Useful for debugging failures. Retrieve via `GET /api/1/workers/tasks/{task_id}/` using the `geopf:push:task-id` value from the resource extras as the bridge between the two layers. Periodic `geopf.sync-offerings` job runs are also visible there via the jobs API (`GET /api/1/workers/jobs/`).

### Push resource extras

Set on the original `.gpkg` resource by the push pipeline.

| Key | Values / type | Description |
|---|---|---|
| `geopf:push:status` | `pending` \| `done` \| `error` \| `timeout` | Lifecycle state of the push. Set to `pending` when the task starts, updated on completion or failure. |
| `geopf:push:task-id` | Celery task UUID | ID of the Celery task running this push. Set when the task starts. Query via `GET /api/1/workers/tasks/<id>/` for status and traceback. |
| `geopf:push:stored-data-id` | UUID string | Entrepôt stored data ID produced by the pipeline. Used by the reverse sync to discover offerings. |
| `geopf:push:datastore-id` | UUID string | Entrepôt (datastore) this resource was pushed into. |
| `geopf:push:last-synced-at` | ISO 8601 | Timestamp of the last successful push. |
| `geopf:push:error` | string | Error message from the last failed attempt. Only present on `error` or `timeout` status. |

### Dataset extras

| Key | Type | Description |
|---|---|---|
| `geopf:push:metadata-id` | UUID string | Entrepôt metadata record ID. Stored after the first successful metadata upload to avoid re-creating the record on subsequent pushes. |
| `geopf:push:fiche-url` | URL | Direct link to the dataset's fiche on cartes.gouv.fr. Set after the first successful push of any resource. |

## ISO 19115 metadata

One metadata document is generated per dataset (not per resource) and pushed as `ISOAP` to the entrepôt.

| ISO 19115 field | Source |
|---|---|
| `fileIdentifier` | `dataset.id` |
| `organisationName` (metadata contact + data contact) | `dataset.organization.name` or `dataset.owner.fullname` |
| `electronicMailAddress` (metadata contact + data contact) | First `dataset.contact_points` entry with an email; omitted if none — see note below |
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

> **Note:** cartes.gouv.fr displays `hierarchyLevel=dataset` as "Lot" in its UI — this is the platform's own French label for dataset-level metadata, not an error.


## Reverse sync: offerings → resources

An *offering* is Géoplateforme's term for an OGC service endpoint (WFS, WMS, WMTS, TMS, …) derived from stored data. Once a dataset has been pushed, the reverse sync reads those offerings and mirrors them as resources in udata.

### Workflow

1. Collect `(geopf:push:datastore-id, geopf:push:stored-data-id)` pairs from the dataset's push resources — same per-resource datastore-selection logic as the push flow, falling back to `GEOPF_DATASTORE_ID` for resources pushed before per-resource datastore tracking existed.
2. For each pair, query `GET /datastores/{datastore_id}/offerings?stored_data={stored_data_id}`.
3. For each offering: create a new resource if none with matching `geopf:offering:id` exists, or update the URL if it changed.
4. Remove any resources whose `geopf:offering:id` no longer appears in the live offering set.

Authenticated with the static `GEOPF_TOKEN` service-account token (see "Authentication" above) — unlike the push flow, this isn't per-user: a periodic background job has no acting user to authenticate as, and authenticating it as whichever user last pushed a resource turned out not to work reliably (their OAuth refresh token doesn't survive long inactivity; see `udata/geopf/tasks.py:sync_geopf_offerings` history for what was tried and ruled out).

### Offering resource extras

Set on resources created (or updated) by the reverse sync. These resources are distinct from the original push resource.

| Key | Type | Description |
|---|---|---|
| `geopf:offering:id` | UUID string | Entrepôt offering ID. Primary key used to match existing resources on subsequent syncs. |
| `geopf:offering:last-synced-at` | ISO 8601 | Timestamp of the last sync that observed this offering. |

### Periodic job

The job `geopf.sync-offerings` runs automatically (schedule configured via Celery Beat). It processes every dataset that has `geopf:push:metadata-id` in its extras (i.e., any dataset with at least one successful push). Per-dataset errors are logged and collected; if any fail, the job raises an `ExceptionGroup` at the end so Celery records the run as failed.

## CLI

```
udata geopf push-resource <dataset_id> <resource_id> (--user-id <id> | --token <token>) [--datastore-id <id>]
```

Runs the full upload pipeline synchronously for a single GPKG resource — same path as the Celery task. `--user-id` uses that user's stored `GeopfToken` (refreshed as needed); `--token` bypasses stored-token resolution entirely with a raw access token, for ops/debugging. `--datastore-id` defaults to `GEOPF_DATASTORE_ID` if omitted. Useful for retrying after a timeout or failure. If the previous attempt left a livraison on Géoplateforme, delete it via the cartes.gouv.fr UI before retrying.

```
udata geopf push-metadata <dataset_id> (--user-id <id> | --token <token>) [--datastore-id <id>]
```

Pushes or refreshes the ISO 19115 metadata for a dataset without triggering a full resource upload. Same `--user-id`/`--token`/`--datastore-id` options as `push-resource`. Useful for iterating on metadata content or fixing a metadata record after a failed pipeline run. Prints the metadata ID and fiche URL on success.

```
udata geopf sync-offerings <dataset_id>
```

Pulls live offerings from Géoplateforme and syncs them as resources for the given dataset, using the static `GEOPF_TOKEN` (no `--user-id`/`--token` options — this path isn't per-user), against each resource's own `geopf:push:datastore-id` (falling back to `GEOPF_DATASTORE_ID`). Prints the count of live offerings found. Useful for triggering an immediate sync or verifying the reverse-sync logic.

## Configuration

```python
GEOPF_API_BASE = "https://data.geopf.fr/api"  # default
# FIXME: temporary default datastore, until cdata has a datastore picker and
# every push carries an explicit datastore_id chosen by the user.
GEOPF_DATASTORE_ID = "<your entrepôt UUID>"

# Static service-account bearer token, used only by the periodic reverse sync
# (geopf.sync-offerings) — the push flow uses per-user OAuth instead (below).
GEOPF_TOKEN = "<your Bearer token>"

# OAuth2/OIDC client registration against geopf's Keycloak
GEOPF_OAUTH_CLIENT_ID = "<confidential client id>"
GEOPF_OAUTH_CLIENT_SECRET = "<confidential client secret>"
GEOPF_OAUTH_OPENID_CONF_URL = "https://sso.geopf.fr/realms/geoplateforme/.well-known/openid-configuration"
GEOPF_OAUTH_SCOPE = "default"  # default

# Fernet key used to encrypt GeopfToken.access_token/refresh_token at rest
GEOPF_TOKEN_ENCRYPTION_KEY = "<fernet key>"
```

The plugin is registered as a udata entry point (`udata.plugins`) and activated by adding `geopf` to the `PLUGINS` list. Note that the API endpoints (`udata/geopf/api.py`) are always registered as a core namespace, regardless of plugin activation — only the OAuth client registration and the config-gated behavior are conditional.

## Limitations

- Only `gpkg` resources are synchronised; other formats are silently skipped.
- Updates to an existing pushed resource are not yet handled — a resource can only be pushed once via `POST /api/1/geopf/push/<dataset_id>/<resource_id>/`.
- There's no datastore picker in cdata yet — every push falls back to the single `GEOPF_DATASTORE_ID`, even though a user may have access to several entrepôts. `GET /api/1/geopf/datastores/` already lists what's available; wiring a picker in cdata is follow-up work.
- SRS is auto-detected from the file before upload. GeoPackage reads the WKT definition from `gpkg_spatial_ref_sys` (via sqlite3 + pyproj). Other vector formats (Shapefile via `.prj`, GeoJSON/KML/KMZ/GPX which are always WGS 84) and raster formats (GeoTIFF via rasterio) can be added to `udata/geopf/srs.py` without changing the pipeline.
- Bounding box is only extracted from raw `dataset.spatial.geom`; zone-based spatial coverage (the common case) has no stored geometry in udata and produces no extent in the metadata.
- `topicCategory` is inferred from free-form tags via a keyword mapping; it will often be absent and is never guaranteed to be accurate.
- Contact points have no UI and must be set via API (`POST /api/1/contacts/`, then `PUT /api/1/datasets/{id}/`); datasets uploaded through the standard funnel will have no contact point and the metadata email fields will be absent. Run `udata geopf push-metadata` after adding one.
