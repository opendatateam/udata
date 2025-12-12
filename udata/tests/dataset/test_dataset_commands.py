from tempfile import NamedTemporaryFile

from udata.core.dataset.factories import DatasetFactory
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
