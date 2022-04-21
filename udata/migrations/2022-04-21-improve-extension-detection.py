'''
Recompute resources extension with improved detection
'''
import logging

from udata.models import Dataset
from udata.core.storages.utils import extension

log = logging.getLogger(__name__)


def migrate(db):
    log.info('Processing Datasets.')

    datasets = Dataset.objects().no_cache().timeout(False)
    count = 0
    for dataset in datasets:
        for resource in [res for res in dataset.resources if res.fs_filename]:
            detected_format = extension(resource.fs_filename)
            if detected_format != resource.format:
                resource.format = detected_format
                count += 1
                resource.save()

    log.info(f'Modified {count} resource objects')
    log.info('Done')
