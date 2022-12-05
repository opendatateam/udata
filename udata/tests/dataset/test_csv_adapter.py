from datetime import datetime, timedelta

import pytest

from udata.core.dataset.csv import ResourcesCsvAdapter, DatasetCsvAdapter
from udata.core.dataset.factories import DatasetFactory, ResourceFactory
from udata.core.dataset.models import Dataset


@pytest.mark.frontend
@pytest.mark.usefixtures('clean_db')
class DatasetCSVAdapterTest:

    def test_resources_csv_adapter(self):
        date_created = datetime(2022, 12, 31)
        date_modified = date_created + timedelta(days=1)
        another_date = date_created + timedelta(days=42)
        dataset = DatasetFactory(
            resources=[ResourceFactory(harvest={
                'created_at': date_created,
                'modified_at': date_modified,
                'uri': 'http://domain.gouv.fr/dataset/uri',
            })],
            harvest={
                'domain': 'example.com',
                'backend': 'dummy_backend',
                'modified_at': another_date,
                'created_at': another_date,
            },
        )
        DatasetFactory(resources=[ResourceFactory()])
        adapter = ResourcesCsvAdapter(Dataset.objects.all())
        rows = list(adapter.rows())
        d_row = [r for r in rows if str(dataset.id) in r][0]
        # harvest.created_at
        assert date_created.isoformat() in d_row
        # harvest.modified_at
        assert date_modified.isoformat() in d_row
        # dataset harvest dates should not be here
        assert another_date.isoformat() not in d_row

    def test_datasets_csv_adapter(self):
        date_created = datetime(2022, 12, 31)
        date_modified = date_created + timedelta(days=1)
        dataset = DatasetFactory(
            harvest={
                'domain': 'example.com',
                'backend': 'dummy_backend',
                'modified_at': date_modified,
                'created_at': date_created,
            },
        )
        DatasetFactory(resources=[ResourceFactory()])
        adapter = DatasetCsvAdapter(Dataset.objects.all())
        rows = list(adapter.rows())
        d_row = [r for r in rows if str(dataset.id) in r][0]
        # harvest.created_at
        assert date_created.isoformat() in d_row
        # harvest.modified_at
        assert date_modified.isoformat() in d_row
        # harvest.backend
        assert 'dummy_backend' in d_row
        # harvest.domain
        assert 'example.com' in d_row
