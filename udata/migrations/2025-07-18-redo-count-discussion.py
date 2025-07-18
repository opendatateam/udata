"""
This migration updates Topic.featured to False when it is None.
"""

import logging

import click

from udata.core.dataservices.models import Dataservice
from udata.core.dataset.models import Dataset

log = logging.getLogger(__name__)


def migrate(db):
    dataservices = Dataservice.objects(metrics__discussions__gt=0)
    dataservices_count = dataservices.count()

    with click.progressbar(dataservices, length=dataservices_count) as dataservices:
        for dataservice in dataservices:
            try:
                dataservice.count_discussions()
            except Exception as err:
                log.error(f"Cannot count discussions for dataservice {dataservice.id} {err}")

    reuses = Dataservice.objects(metrics__discussions__gt=0)
    reuses_count = reuses.count()

    with click.progressbar(reuses, length=reuses_count) as reuses:
        for reuse in reuses:
            try:
                reuse.count_discussions()
            except Exception as err:
                log.error(f"Cannot count discussions for reuse {reuse.id} {err}")
    
    datasets = Dataset.objects(metrics__discussions__gt=0)
    datasets_count = datasets.count()

    with click.progressbar(datasets, length=datasets_count) as datasets:
        for dataset in datasets:
            try:
                dataset.count_discussions()
            except Exception as err:
                log.error(f"Cannot count discussions for dataset {dataset.id} {err}")
