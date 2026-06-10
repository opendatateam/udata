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
   - If `geopf_metadata_id` is already in dataset extras: update the existing metadata record.
   - Otherwise: upload (with 409 upsert fallback), publish to CSW, tag, and store the ID in extras.

On any failure the task attempts to delete the livraison to avoid orphaned uploads, then re-raises so the error is visible in Celery.

## State tracking

Progress is recorded in extras so it survives across Celery retries and is visible in the API.

Resource extras:
- `geopf_status` — `pending` | `done` | `error`
- `geopf_stored_data_id` — entrepôt stored data ID
- `geopf_datasheet_name` — fiche grouping tag (= `dataset.id`)
- `geopf_fiche_url` — direct URL to the fiche on cartes.gouv.fr
- `geopf_last_synced_at` — ISO 8601 timestamp of last successful push
- `geopf_error` — error message (only on `error` status)

Dataset extras:
- `geopf_metadata_id` — entrepôt metadata ID (avoids re-uploading metadata on subsequent resource syncs)

## ISO 19115 metadata

One metadata document is generated per dataset (not per resource) and pushed as `ISOAP` to the entrepôt.

| ISO 19115 field | Source |
|---|---|
| `fileIdentifier` | `dataset.id` |
| `organisationName` | `dataset.organization.name` or `dataset.owner.fullname` |
| `dateStamp` | `dataset.last_modified` |
| `title` | `dataset.title` |
| `date` (creation) | `dataset.created_at` |
| `abstract` | `dataset.description`, falls back to `dataset.title` |
| `keywords` | `dataset.tags` |
| `otherConstraints` | `dataset.license.url` or `dataset.license.title` (omitted if no license) |
| Bounding box | Computed from `dataset.spatial.geom` (MultiPolygon); defaults to France métropolitaine |
| `language` | Hardcoded `fre` |
| `hierarchyLevel` | Hardcoded `dataset` |

## Configuration

```python
GEOPF_API_BASE = "https://data.geopf.fr/api"  # default
GEOPF_DATASTORE_ID = "<your entrepôt UUID>"
GEOPF_TOKEN = "<your Bearer token>"
```

The plugin is registered as a udata entry point (`udata.plugins`) and activated by adding `geopf` to the `PLUGINS` list.

## Limitations

- Only `gpkg` resources are synchronised; other formats are silently skipped.
- Updates to an existing resource are not yet handled — the task only fires on `on_resource_added`.
- Resource deletion on the Géoplateforme side is not yet implemented.
- SRS is hardcoded to `EPSG:4326` (WGS 84) for both upload creation and processing parameters; files in other projections will fail or produce incorrect results.
