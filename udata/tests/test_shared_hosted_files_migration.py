from datetime import UTC, datetime

from mongoengine.connection import get_db

from udata.core.dataset.factories import (
    CommunityResourceFactory,
    DatasetFactory,
    ResourceFactory,
)
from udata.db import migrations
from udata.tests.api import PytestOnlyDBTestCase

MIGRATION = "2026-11-27-shared-hosted-files-single-resource.py"
FS_FILENAME = "my-dataset/20250711-211430/data.csv"
URL = f"https://static.example.org/resources/{FS_FILENAME}"


def migrate():
    migrations.get(MIGRATION).migrate(get_db())


def hosted(created_at, **kwargs):
    return ResourceFactory(
        filetype="file",
        fs_filename=FS_FILENAME,
        url=URL,
        created_at_internal=created_at,
        **kwargs,
    )


class SharedHostedFilesMigrationTest(PytestOnlyDBTestCase):
    def test_the_oldest_resource_keeps_the_file_the_others_become_links(self):
        dataset = DatasetFactory(
            resources=[
                hosted(datetime(2025, 7, 11, 21, 14, 31, tzinfo=UTC)),
                hosted(datetime(2025, 7, 11, 21, 14, 30, tzinfo=UTC)),
                hosted(datetime(2025, 7, 11, 21, 14, 32, tzinfo=UTC)),
            ]
        )

        migrate()

        dataset.reload()
        assert [r.filetype for r in dataset.resources] == ["remote", "file", "remote"]
        assert [r.fs_filename for r in dataset.resources] == [None, FS_FILENAME, None]
        assert [r.url for r in dataset.resources] == [URL, URL, URL]

    def test_a_resource_of_a_deleted_dataset_does_not_keep_the_file(self):
        deleted = DatasetFactory(
            deleted=datetime(2026, 1, 1, tzinfo=UTC),
            resources=[hosted(datetime(2025, 7, 11, 21, 14, 30, tzinfo=UTC))],
        )
        alive = DatasetFactory(resources=[hosted(datetime(2025, 7, 11, 21, 14, 31, tzinfo=UTC))])

        migrate()

        deleted.reload()
        alive.reload()
        assert deleted.resources[0].filetype == "remote"
        assert deleted.resources[0].fs_filename is None
        assert alive.resources[0].filetype == "file"
        assert alive.resources[0].fs_filename == FS_FILENAME

    def test_a_file_held_by_a_community_resource_stays_with_it(self):
        community = CommunityResourceFactory(filetype="file", fs_filename=FS_FILENAME, url=URL)
        dataset = DatasetFactory(
            resources=[
                hosted(datetime(2025, 7, 11, 21, 14, 30, tzinfo=UTC)),
                hosted(datetime(2025, 7, 11, 21, 14, 31, tzinfo=UTC)),
            ]
        )

        migrate()

        dataset.reload()
        community.reload()
        assert [r.filetype for r in dataset.resources] == ["remote", "remote"]
        assert [r.fs_filename for r in dataset.resources] == [None, None]
        assert community.fs_filename == FS_FILENAME

    def test_a_file_held_by_a_single_resource_is_untouched(self):
        dataset = DatasetFactory(resources=[hosted(datetime(2025, 7, 11, 21, 14, 30, tzinfo=UTC))])

        migrate()

        dataset.reload()
        assert dataset.resources[0].filetype == "file"
        assert dataset.resources[0].fs_filename == FS_FILENAME
