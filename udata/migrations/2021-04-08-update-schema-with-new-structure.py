"""
The purpose here is to update every resource's metadata 'schema'
with a new format (string to object)
"""

import logging

from udata.models import Dataset

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Processing resources.")

    datasets = Dataset.objects().no_cache().timeout(False)
    for dataset in datasets:
        save_res = False
        for resource in dataset.resources:
            if hasattr(resource, "schema"):
                schema = resource.schema
                resource.schema = {"name": None}
                if schema is not None and isinstance(schema, str):
                    resource.schema = {"name": schema}
                save_res = True
        if save_res:
            try:
                dataset.save()
            except Exception as e:
                log.warning(e)
                pass

    log.info("Completed.")
