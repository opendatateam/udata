'''
The purpose here is to fill every resource with a fs_filename string field.
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
                schema = resource.schema
                resource.schema = {'name': None}
                if schema is not None and isinstance(schema, str):
                        resource.schema = {'name': schema}   
                save_res = True
        if save_res:
            try:
                dataset.save()
            except Exception as e:
                log.warning(e)
                pass

    log.info('Completed.')
