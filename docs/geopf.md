# Géoplateforme integration

udata can automatically synchronise GeoPackage (`.gpkg`) resources to the IGN [Géoplateforme](https://geoplateforme.fr/) entrepôt, making them available as vector tiles on [cartes.gouv.fr](https://cartes.gouv.fr).

## Data model mapping

| data.gouv.fr | Géoplateforme |
|---|---|
| Dataset | Fiche de données (`datasheet_name = dataset.id`) |
| Resource (gpkg) | Stored data (`stored_data` name = `resource.id`) |
| Dataset metadata | ISO 19115 metadata (one per fiche) |

All entrepôt entities belonging to the same fiche (uploads, stored data, metadata) carry the same `datasheet_name` tag so the platform groups them correctly.

## Workflow

Triggered automatically when a `gpkg` resource is added to a dataset (via the `on_resource_added` signal). Runs as a Celery task.

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

Progress is recorded in extras so it survives across Celery retries and is visible in the API.

### Push resource extras

Set on the original `.gpkg` resource by the push pipeline.

| Key | Values / type | Description |
|---|---|---|
| `geopf:push:status` | `pending` \| `done` \| `error` \| `timeout` | Lifecycle state of the push. Set to `pending` at dispatch time, updated on completion or failure. |
| `geopf:push:task-id` | Celery task UUID | ID of the Celery task that ran (or is running) this push. Query via `GET /api/1/tasks/<id>/` for status and traceback. |
| `geopf:push:stored-data-id` | UUID string | Entrepôt stored data ID produced by the pipeline. Used by the reverse sync to discover offerings. |
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

> **Note:** Contact points have no UI — they must be created via `POST /api/1/contacts/` and attached to the dataset via `PUT /api/1/datasets/{id}/`. This means a dataset going through the standard contribution funnel will have no contact point set at the time the gpkg resource is first uploaded, and the email fields will be absent from the metadata. Contact points must be added separately after the fact, then `udata geopf push-metadata` run to refresh the metadata.

## Reverse sync: services → resources

Once a dataset has been pushed to Géoplateforme, the stored data are exposed as OGC services (WFS, WMS, WMTS, TMS, …). The reverse sync reads those offerings and mirrors them as resources in udata.

### Workflow

1. Collect stored data IDs from `geopf:push:stored-data-id` on the dataset's push resources.
2. For each stored data ID, query `GET /datastores/{id}/offerings?stored_data={id}`.
3. For each offering: create a new resource if none with matching `geopf:offering:id` exists, or update the URL if it changed.
4. Remove any resources whose `geopf:offering:id` no longer appears in the live offering set.

### Offering resource extras

Set on resources created (or updated) by the reverse sync. These resources are distinct from the original push resource.

| Key | Type | Description |
|---|---|---|
| `geopf:offering:id` | UUID string | Entrepôt offering ID. Primary key used to match existing resources on subsequent syncs. |
| `geopf:offering:last-synced-at` | ISO 8601 | Timestamp of the last sync that observed this offering. |

### Periodic job

The job `geopf.sync-services` runs automatically (schedule configured via Celery Beat). It processes every dataset that has `geopf:push:metadata-id` in its extras (i.e., any dataset with at least one successful push). Per-dataset errors are logged and collected; if any fail, the job raises an `ExceptionGroup` at the end so Celery records the run as failed.

## CLI

```
udata geopf push-resource <dataset_id> <resource_id>
```

Runs the full upload pipeline synchronously for a single GPKG resource — same path as the Celery task. Useful for retrying after a timeout or failure. If the previous attempt left a livraison on Géoplateforme, delete it via the cartes.gouv.fr UI before retrying.

```
udata geopf push-metadata <dataset_id>
```

Pushes or refreshes the ISO 19115 metadata for a dataset without triggering a full resource upload. Useful for iterating on metadata content or fixing a metadata record after a failed pipeline run. Prints the metadata ID and fiche URL on success.

```
udata geopf sync-services <dataset_id>
```

Pulls live offerings from Géoplateforme and syncs them as resources for the given dataset. Prints the count of live offerings found. Useful for triggering an immediate sync or verifying the reverse-sync logic.

## Configuration

```python
GEOPF_API_BASE = "https://data.geopf.fr/api"  # default
GEOPF_DATASTORE_ID = "<your entrepôt UUID>"
GEOPF_TOKEN = "<your Bearer token>"
```

The plugin is registered as a udata entry point (`udata.plugins`) and activated by adding `geopf` to the `PLUGINS` list.

## Limitations

- Only `gpkg` resources are synchronised; other formats are silently skipped.
- Updates to an existing pushed resource are not yet handled — the push task only fires on `on_resource_added`.
- SRS is hardcoded to `EPSG:4326` (WGS 84) for both upload creation and processing parameters; files in other projections will fail or produce incorrect results.
- Bounding box is only extracted from raw `dataset.spatial.geom`; zone-based spatial coverage (the common case) has no stored geometry in udata and produces no extent in the metadata.
- `topicCategory` is inferred from free-form tags via a keyword mapping; it will often be absent and is never guaranteed to be accurate.
