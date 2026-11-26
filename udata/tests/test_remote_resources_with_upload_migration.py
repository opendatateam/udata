from mongoengine.connection import get_db

from udata.core.dataset.factories import DatasetFactory, ResourceFactory
from udata.db import migrations
from udata.tests.api import PytestOnlyDBTestCase

MIGRATION = "2026-11-26-remote-resources-with-upload-to-file.py"
FS_FILENAME = "my-dataset/20240101-120000/data.csv"


def migrate():
    migrations.get(MIGRATION).migrate(get_db())


class RemoteResourcesWithUploadMigrationTest(PytestOnlyDBTestCase):
    def test_remote_resource_targeting_its_stored_file_becomes_file(self):
        uploaded = ResourceFactory(
            filetype="remote",
            fs_filename=FS_FILENAME,
            url=f"https://static.example.org/resources/{FS_FILENAME}",
        )
        hosted = ResourceFactory(filetype="file")
        dataset = DatasetFactory(resources=[uploaded, hosted])

        migrate()

        dataset.reload()
        assert [r.filetype for r in dataset.resources] == ["file", "file"]
        assert dataset.resources[0].url == f"https://static.example.org/resources/{FS_FILENAME}"

    def test_remote_resource_whose_url_was_edited_stays_remote(self):
        resource = ResourceFactory(
            filetype="remote", fs_filename=FS_FILENAME, url="https://example.org/other.csv"
        )
        dataset = DatasetFactory(resources=[resource])

        migrate()

        dataset.reload()
        assert dataset.resources[0].filetype == "remote"

    def test_remote_resource_without_upload_stays_remote(self):
        resource = ResourceFactory(filetype="remote", url="https://example.org/data.csv")
        dataset = DatasetFactory(resources=[resource])

        migrate()

        dataset.reload()
        assert dataset.resources[0].filetype == "remote"
