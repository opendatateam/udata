'''
The purpose here is to update every resource's metadata 'schema' name.
'''
import logging

from udata.models import Dataset

log = logging.getLogger(__name__)


def migrate(db):
    log.info('Processing resources.')

    datasets = Dataset.objects().no_cache().timeout(False)
    for dataset in datasets:
        save_res = False
        for resource in dataset.resources:
            if hasattr(resource, 'schema'):
                for key, value in resource.schema.items():
                    if key == 'name' and value is None:
                        resource.schema = {}
                        save_res = True
        if save_res:
            try:
                dataset.save()
            except Exception as e:
                log.warning(e)
                pass

    log.info('Completed.')
