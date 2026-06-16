import json
import logging
import os
from datetime import datetime, timedelta

import click
import requests
from bson import ObjectId

from udata.commands import cli, echo, exit_with_error, header, success, white
from udata.core import storages
from udata.core.dataset.constants import DEFAULT_LICENSE
from udata.models import CommunityResource, Dataset, License

from . import actions

log = logging.getLogger(__name__)

# Use CKAN license group from opendefinition as default license list
DEFAULT_LICENSE_FILE = "http://licenses.opendefinition.org/licenses/groups/ckan.json"  # noqa

FLAGS_MAP = {
    "domain_content": "domain_content",
    "domain_data": "domain_data",
    "domain_software": "domain_software",
    "is_generic": "generic",
    "is_okd_compliant": "okd_compliant",
    "is_osi_compliant": "osi_compliant",
}


@cli.command()
@click.argument("source", default=DEFAULT_LICENSE_FILE)
def licenses(source=DEFAULT_LICENSE_FILE):
    """Feed the licenses from a JSON file"""
    if source.startswith("http"):
        json_licenses = requests.get(source).json()
    else:
        with open(source) as fp:
            json_licenses = json.load(fp)

    if len(json_licenses):
        log.info("Dropping existing licenses")
        License.drop_collection()

    for json_license in json_licenses:
        flags = []
        for field, flag in FLAGS_MAP.items():
            if json_license.get(field, False):
                flags.append(flag)

        license = License.objects.create(
            id=json_license["id"],
            title=json_license["title"],
            url=json_license["url"] or None,
            maintainer=json_license["maintainer"] or None,
            flags=flags,
            active=json_license.get("active", False),
            alternate_urls=json_license.get("alternate_urls", []),
            alternate_titles=json_license.get("alternate_titles", []),
        )
        log.info('Added license "%s"', license.title)
    try:
        License.objects.get(id=DEFAULT_LICENSE["id"])
    except License.DoesNotExist:
        License.objects.create(**DEFAULT_LICENSE)
        log.info('Added license "%s"', DEFAULT_LICENSE["title"])
    success("Done")


@cli.group("dataset")
def grp():
    """Dataset related operations"""
    pass


@grp.command()
@click.argument("dataset_id")
@click.option("-c", "--comment", is_flag=True, help="Post a comment when archiving")
def archive_one(dataset_id, comment):
    """Archive one dataset"""
    try:
        dataset = Dataset.objects.get(id=dataset_id)
    except Dataset.DoesNotExist:
        exit_with_error("Cannot find a dataset with id %s" % dataset_id)
    else:
        actions.archive(dataset, comment)


def human_size(num):
    """Human readable byte size (binary units)."""
    value = float(num)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(value) < 1024:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} PiB"


def collect_referenced_filenames():
    """Set of every fs_filename referenced by a resource in database.

    Includes resources embedded in *every* dataset (soft-deleted and archived
    ones too: their files stay legitimate until `udata purge` runs) and every
    CommunityResource.
    """
    referenced = set()

    dataset_pipeline = [
        {"$unwind": "$resources"},
        {"$match": {"resources.fs_filename": {"$ne": None}}},
        {"$project": {"_id": 0, "f": "$resources.fs_filename"}},
    ]
    for row in Dataset.objects.aggregate(*dataset_pipeline):
        referenced.add(row["f"])

    community_pipeline = [
        {"$match": {"fs_filename": {"$ne": None}}},
        {"$project": {"_id": 0, "f": "$fs_filename"}},
    ]
    for row in CommunityResource.objects.aggregate(*community_pipeline):
        referenced.add(row["f"])

    return referenced


@grp.command()
@click.option(
    "--delete",
    is_flag=True,
    help="Actually delete orphan files. Without it the command is a dry-run (report only).",
)
@click.option(
    "--days",
    default=7,
    show_default=True,
    help="Ignore files modified within the last N days "
    "(protects in-flight uploads not yet committed to the database snapshot).",
)
@click.option(
    "--output",
    default="orphan-resources.txt",
    show_default=True,
    help="File where the list of orphan files is written (one fs_filename per line).",
)
@click.option(
    "-y",
    "--yes",
    is_flag=True,
    help="Do not ask for confirmation before deleting (for non-interactive runs).",
)
def check_files(delete, days, output, yes):
    """Find (and optionally delete) orphan resource files on storage.

    Cross-references every file in the `resources` storage against the
    fs_filename of every resource in database (dataset resources, including
    soft-deleted datasets, and community resources). A single pass over the
    storage reports both:

    \b
    - orphan files: on storage but referenced by no resource (wasted space);
    - broken references: referenced by a resource but missing on storage.

    Only orphan files are deletable, and only with --delete.
    """
    storage = storages.resources

    # This command relies on direct filesystem access (os.stat below) to read
    # each file's size and mtime cheaply. The storage-agnostic alternative
    # (storage.metadata()) would re-read every file in full to recompute a sha1
    # on the local backend, which is prohibitive when scanning the whole bucket.
    # So we require a local backend and fail fast with a clear message instead
    # of crashing mid-scan on an S3 backend (storage.path() raises there).
    if not storage.backend.root:
        exit_with_error(
            f"`dataset check-files` only supports a local filesystem backend, "
            f"but the `resources` storage uses {storage.backend.__class__.__name__}."
        )

    # 1. Snapshot every referenced file BEFORE walking the storage, so a file
    #    uploaded during the walk can never be mistaken for an orphan.
    header("Collecting referenced files from database")
    referenced = collect_referenced_filenames()
    success(f"{len(referenced)} files referenced in database")

    # 2. Single cross-referencing pass over the storage. A first cheap pass only
    #    counts files (directory metadata, no content read) so the progress bar
    #    can show a percentage and an ETA.
    header("Counting files on storage")
    total = sum(1 for _ in storage.list_files())
    echo(white(f"{total:,} files to scan"))

    cutoff = datetime.now() - timedelta(days=days)
    orphans = []
    orphans_size = 0
    skipped_recent = 0

    def progress_info(_item):
        return f"{len(orphans):,} orphans, {human_size(orphans_size)}"

    header("Scanning storage")
    with click.progressbar(
        storage.list_files(),
        length=total,
        label="Scanning",
        item_show_func=progress_info,
    ) as bar:
        for fs_filename in bar:
            if fs_filename in referenced:
                # Mark as seen; whatever stays in `referenced` is a broken reference.
                referenced.discard(fs_filename)
                continue

            try:
                stat = os.stat(storage.path(fs_filename))
            except FileNotFoundError:
                # Vanished between listing and stat (concurrent delete): skip.
                continue

            if datetime.fromtimestamp(stat.st_mtime) > cutoff:
                skipped_recent += 1
            else:
                orphans.append(fs_filename)
                orphans_size += stat.st_size

    broken_references = referenced

    # 3. Report.
    header("Result")
    echo(white(f"Files scanned on storage: {total:,}"))
    echo(white(f"Orphan files: {len(orphans):,} ({human_size(orphans_size)} reclaimable)"))
    echo(white(f"Recent files protected (< {days} days): {skipped_recent:,}"))
    echo(
        white(f"Broken references (referenced but missing on storage): {len(broken_references):,}")
    )

    with open(output, "w") as f:
        f.write("\n".join(orphans))
        if orphans:
            f.write("\n")
    success(f"Orphan list written to {output}")

    if broken_references:
        broken_output = output + ".broken-references"
        with open(broken_output, "w") as f:
            f.write("\n".join(sorted(broken_references)) + "\n")
        success(f"Broken references list written to {broken_output}")

    if not orphans:
        return

    if not delete:
        echo("Dry-run: nothing deleted. Re-run with --delete to remove the orphan files.")
        return

    if not yes:
        click.confirm(
            f"Delete {len(orphans):,} orphan files ({human_size(orphans_size)})?",
            abort=True,
        )

    header("Deleting orphan files")
    deleted = 0
    errors = 0
    for fs_filename in orphans:
        try:
            storage.delete(fs_filename)
            deleted += 1
        except Exception as e:  # noqa  (never stop on a single failure)
            log.error("Unable to delete %s: %s", fs_filename, e)
            errors += 1
    success(f"Deleted {deleted:,} files, {errors:,} failed")


@grp.command()
@click.argument("filepath")
@click.option("-c", "--comment", is_flag=True, help="Post a comment when archiving")
def archive(filepath, comment):
    """Archive multiple datasets from a list in a file (one id per line)"""
    count = 0
    errors = 0
    log.info("Archiving datasets...")
    with open(filepath) as inputfile:
        for line in inputfile.readlines():
            line = line.rstrip()
            if not line:
                continue
            try:
                dataset = Dataset.objects.get(id=ObjectId(line))
            except Exception as e:  # noqa  (Never stop on failure)
                log.error("Unable to archive dataset %s: %s", line, e)
                errors += 1
                continue
            else:
                actions.archive(dataset, comment)
                count += 1
    log.info("Archived %s datasets, %s failed", count, errors)
