from mongoengine.connection import get_db

from udata.core.dataset.factories import (
    CommunityResourceFactory,
    DatasetFactory,
    ResourceFactory,
)
from udata.db import migrations
from udata.tests.api import PytestOnlyDBTestCase

MIGRATION = "2026-11-26-remote-resources-with-upload-to-file.py"
FS_FILENAME = "my-dataset/20240101-120000/data.csv"
URL = f"https://static.example.org/resources/{FS_FILENAME}"


def migrate():
    migrations.get(MIGRATION).migrate(get_db())


class RemoteResourcesWithUploadMigrationTest(PytestOnlyDBTestCase):
    def test_remote_resource_targeting_its_stored_file_becomes_file(self):
        uploaded = ResourceFactory(filetype="remote", fs_filename=FS_FILENAME, url=URL)
        hosted = ResourceFactory(filetype="file")
        dataset = DatasetFactory(resources=[uploaded, hosted])

        migrate()

        dataset.reload()
        assert [r.filetype for r in dataset.resources] == ["file", "file"]
        assert dataset.resources[0].fs_filename == FS_FILENAME
        assert dataset.resources[0].url == URL

    def test_link_to_a_file_of_another_dataset_becomes_its_owner(self):
        # A 2020 backfilled link whose file is held by no other resource anymore
        fs_filename = "deleted-dataset/20161125-133530/data.csv"
        url = f"https://static.example.org/resources/{fs_filename}"
        resource = ResourceFactory(filetype="remote", fs_filename=fs_filename, url=url)
        dataset = DatasetFactory(slug="my-dataset", resources=[resource])

        migrate()

        dataset.reload()
        assert dataset.resources[0].filetype == "file"
        assert dataset.resources[0].fs_filename == fs_filename

    def test_remote_resource_whose_url_was_edited_loses_its_fs_filename(self):
        resource = ResourceFactory(
            filetype="remote", fs_filename=FS_FILENAME, url="https://example.org/other.csv"
        )
        dataset = DatasetFactory(resources=[resource])

        migrate()

        dataset.reload()
        assert dataset.resources[0].filetype == "remote"
        assert dataset.resources[0].fs_filename is None
        assert dataset.resources[0].url == "https://example.org/other.csv"

    def test_remote_resource_without_upload_is_untouched(self):
        resource = ResourceFactory(filetype="remote", url="https://example.org/data.csv")
        dataset = DatasetFactory(resources=[resource])

        migrate()

        dataset.reload()
        assert dataset.resources[0].filetype == "remote"
        assert dataset.resources[0].fs_filename is None

    def test_link_to_a_community_resource_file_loses_its_fs_filename(self):
        fs_filename = "other-dataset/community/20150302-120940/data.xlsx"
        url = f"https://static.example.org/resources/{fs_filename}"
        community = CommunityResourceFactory(filetype="file", fs_filename=fs_filename, url=url)
        link = ResourceFactory(filetype="remote", fs_filename=fs_filename, url=url)
        dataset = DatasetFactory(resources=[link])

        migrate()

        dataset.reload()
        community.reload()
        assert dataset.resources[0].filetype == "remote"
        assert dataset.resources[0].fs_filename is None
        assert community.fs_filename == fs_filename

    def test_remote_community_resource_targeting_its_stored_file_becomes_file(self):
        community = CommunityResourceFactory(filetype="remote", fs_filename=FS_FILENAME, url=URL)

        migrate()

        community.reload()
        assert community.filetype == "file"
        assert community.fs_filename == FS_FILENAME

    def test_remote_community_resource_whose_url_was_edited_loses_its_fs_filename(self):
        community = CommunityResourceFactory(
            filetype="remote", fs_filename=FS_FILENAME, url="https://example.org/other.csv"
        )

        migrate()

        community.reload()
        assert community.filetype == "remote"
        assert community.fs_filename is None

    def test_each_resource_of_a_dataset_is_migrated(self):
        dataset = DatasetFactory(
            resources=[
                ResourceFactory(filetype="remote", fs_filename=FS_FILENAME, url=URL),
                ResourceFactory(
                    filetype="remote",
                    fs_filename="my-dataset/20240102-120000/old.csv",
                    url="https://example.org/old.csv",
                ),
            ]
        )

        migrate()

        dataset.reload()
        assert [r.filetype for r in dataset.resources] == ["file", "remote"]
        assert [r.fs_filename for r in dataset.resources] == [FS_FILENAME, None]
