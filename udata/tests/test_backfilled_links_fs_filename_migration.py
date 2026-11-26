from mongoengine.connection import get_db

from udata.core.dataset.factories import DatasetFactory, ResourceFactory
from udata.db import migrations
from udata.tests.api import PytestOnlyDBTestCase

MIGRATION = "2026-11-25-backfilled-links-unset-fs-filename.py"
FS_FILENAME = "elections-2015/20150219-181605/inventaire.xls"
URL = f"https://static.example.org/resources/{FS_FILENAME}"


def migrate():
    migrations.get(MIGRATION).migrate(get_db())


class BackfilledLinksFsFilenameMigrationTest(PytestOnlyDBTestCase):
    def test_link_to_another_dataset_file_loses_its_fs_filename(self):
        hosting_dataset = DatasetFactory(
            resources=[ResourceFactory(filetype="file", fs_filename=FS_FILENAME, url=URL)]
        )
        linking_dataset = DatasetFactory(
            resources=[ResourceFactory(filetype="remote", fs_filename=FS_FILENAME, url=URL)]
        )

        migrate()

        hosting_dataset.reload()
        linking_dataset.reload()
        assert hosting_dataset.resources[0].fs_filename == FS_FILENAME
        assert linking_dataset.resources[0].fs_filename is None
        assert linking_dataset.resources[0].url == URL

    def test_link_to_a_file_of_the_same_dataset_loses_only_its_own_fs_filename(self):
        dataset = DatasetFactory(
            resources=[
                ResourceFactory(filetype="file", fs_filename=FS_FILENAME, url=URL),
                ResourceFactory(filetype="remote", fs_filename=FS_FILENAME, url=URL),
            ]
        )

        migrate()

        dataset.reload()
        assert dataset.resources[0].fs_filename == FS_FILENAME
        assert dataset.resources[1].fs_filename is None

    def test_remote_resource_owning_its_uploaded_file_keeps_its_fs_filename(self):
        dataset = DatasetFactory(
            resources=[ResourceFactory(filetype="remote", fs_filename=FS_FILENAME, url=URL)]
        )

        migrate()

        dataset.reload()
        assert dataset.resources[0].fs_filename == FS_FILENAME
