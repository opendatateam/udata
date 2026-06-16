import os
from datetime import UTC, datetime, timedelta
from tempfile import NamedTemporaryFile, TemporaryDirectory
from unittest.mock import patch

import pytest

from udata.commands import cli as cli_cmd
from udata.core import storages
from udata.core.dataset.factories import (
    CommunityResourceFactory,
    DatasetFactory,
    ResourceFactory,
)
from udata.tests.api import PytestOnlyDBTestCase


class DatasetCommandTest(PytestOnlyDBTestCase):
    def test_dataset_archive_one(self):
        dataset = DatasetFactory()

        self.cli("dataset", "archive-one", str(dataset.id))

        dataset.reload()
        assert dataset.archived is not None

    def test_dataset_archive(self):
        datasets = [DatasetFactory() for _ in range(2)]

        with NamedTemporaryFile(mode="w", encoding="utf8") as temp:
            temp.write("\n".join((str(d.id) for d in datasets)))
            temp.flush()

            self.cli("dataset", "archive", temp.name)

        for dataset in datasets:
            dataset.reload()
            assert dataset.archived is not None


@pytest.mark.usefixtures("instance_path")
class DatasetCheckFilesCommandTest(PytestOnlyDBTestCase):
    def write_file(self, fs_filename, *, age_days=30, content=b"data"):
        """Write a real file in the resources storage and backdate its mtime."""
        with self.app.app_context():
            storages.resources.write(fs_filename, content)
            path = storages.resources.path(fs_filename)
        past = (datetime.now() - timedelta(days=age_days)).timestamp()
        os.utime(path, (past, past))
        return path

    def exists(self, fs_filename):
        with self.app.app_context():
            return storages.resources.exists(fs_filename)

    def run_check(self, *extra_args):
        """Run `dataset check-files` and return (orphans, broken_references)."""
        with TemporaryDirectory() as tmp:
            output = os.path.join(tmp, "orphans.txt")
            self.cli("dataset", "check-files", "--output", output, *extra_args)
            with open(output) as f:
                orphans = [line for line in f.read().splitlines() if line]
            broken_path = output + ".broken-references"
            broken = []
            if os.path.exists(broken_path):
                with open(broken_path) as f:
                    broken = [line for line in f.read().splitlines() if line]
        return orphans, broken

    def test_dry_run_lists_orphans_and_keeps_files(self):
        referenced = "ds/20200101-000000/kept.csv"
        orphan = "ds/20200101-000000/orphan.csv"
        self.write_file(referenced)
        self.write_file(orphan)
        DatasetFactory(resources=[ResourceFactory(fs_filename=referenced)])

        orphans, broken = self.run_check()

        assert orphans == [orphan]
        assert broken == []
        # Dry-run: nothing is deleted.
        assert self.exists(orphan)
        assert self.exists(referenced)

    def test_delete_removes_only_orphans(self):
        referenced = "ds/20200101-000000/kept.csv"
        orphan = "ds/20200101-000000/orphan.csv"
        self.write_file(referenced)
        self.write_file(orphan)
        DatasetFactory(resources=[ResourceFactory(fs_filename=referenced)])

        self.run_check("--delete", "--yes")

        assert not self.exists(orphan)
        assert self.exists(referenced)

    def test_recent_files_are_protected_from_deletion(self):
        old_orphan = "ds/20200101-000000/old.csv"
        recent_orphan = "ds/20200101-000000/recent.csv"
        self.write_file(old_orphan, age_days=30)
        self.write_file(recent_orphan, age_days=1)

        orphans, _ = self.run_check("--delete", "--yes")

        # The recent file is never even considered an orphan.
        assert orphans == [old_orphan]
        assert not self.exists(old_orphan)
        assert self.exists(recent_orphan)

    def test_soft_deleted_dataset_files_are_kept(self):
        """Files of a soft-deleted (not yet purged) dataset are still legitimate."""
        fs_filename = "ds/20200101-000000/soft-deleted.csv"
        self.write_file(fs_filename)
        DatasetFactory(
            resources=[ResourceFactory(fs_filename=fs_filename)],
            deleted=datetime.now(UTC),
        )

        orphans, _ = self.run_check("--delete", "--yes")

        assert orphans == []
        assert self.exists(fs_filename)

    def test_community_resource_files_are_kept(self):
        fs_filename = "ds/20200101-000000/community.csv"
        self.write_file(fs_filename)
        CommunityResourceFactory(fs_filename=fs_filename)

        orphans, _ = self.run_check("--delete", "--yes")

        assert orphans == []
        assert self.exists(fs_filename)

    def test_broken_references_are_reported_not_deleted(self):
        """A resource pointing to a missing file is a broken reference, not an orphan."""
        missing = "ds/20200101-000000/missing.csv"
        DatasetFactory(resources=[ResourceFactory(fs_filename=missing)])

        orphans, broken = self.run_check("--delete", "--yes")

        assert orphans == []
        assert broken == [missing]

    def test_non_local_backend_fails_fast(self):
        """On a backend without direct filesystem access (e.g. S3), the command
        refuses to run upfront instead of crashing mid-scan."""
        backend = storages.resources.backend
        # A non-local backend has no `root` (BaseBackend.root is None).
        with patch.object(backend, "root", None):
            result = self.app.test_cli_runner().invoke(cli_cmd, ["dataset", "check-files"])

        assert result.exit_code != 0
        assert "local filesystem backend" in result.output
