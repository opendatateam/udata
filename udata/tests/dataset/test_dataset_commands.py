from tempfile import NamedTemporaryFile

import pytest

from udata.core.dataset.factories import DatasetFactory


@pytest.mark.usefixtures("clean_db")
class DatasetCommandTest:
    def test_dataset_archive_one(self, cli):
        dataset = DatasetFactory()

        cli("dataset", "archive-one", str(dataset.id))

        dataset.reload()
        assert dataset.archived is not None

    def test_dataset_archive(self, cli):
        datasets = [DatasetFactory() for _ in range(2)]

        with NamedTemporaryFile(mode="w", encoding="utf8") as temp:
            temp.write("\n".join((str(d.id) for d in datasets)))
            temp.flush()

            cli("dataset", "archive", temp.name)

        for dataset in datasets:
            dataset.reload()
            assert dataset.archived is not None
