'''
Clean and migrate licenses
'''
import logging

from udata.models import License, Dataset

log = logging.getLogger(__name__)


def migrate(db):
    log.info('Processing License.')

    datasets = Dataset.objects().no_cache().timeout(False)
    dataset_count = 0
    # Migrate datasets license
    for dataset in datasets:
        if dataset.license.title in ['Licence Ouverte / Open Licence', 'License Not Specified']:
            new_license = License.objects(title='Licence Ouverte / Open Licence version 2.0').first()
            dataset.license = new_license
            dataset.save()
            dataset_count += 1
    # Delete unnecessary license
    license = License.objects(title='Licence Ouverte / Open Licence').first()
    license.delete()

    log.info(f'{dataset_count} dataset objects modified')
    log.info('Done')
