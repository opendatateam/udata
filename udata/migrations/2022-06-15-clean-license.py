'''
Clean and migrate licenses
'''
import logging

from udata.models import License, Dataset

log = logging.getLogger(__name__)


def migrate(db):
    log.info('Processing License.')

    datasets = Dataset.objects().no_cache().timeout(False)
    licenses = License.objects().no_cache().timeout(False)
    dataset_count = 0
    license_count = 0
    # Migrate datasets license
    for dataset in datasets:
        # same ?
        if dataset.license.title is 'Licence Ouverte / Open Licence' or dataset.license.title not in ['Open Data Commons Open Database License (ODbL)',
                                                                                                      'Licence Ouverte / Open Licence version 2.0']:
            new_license = License.objects(title='Licence Ouverte / Open Licence version 2.0').first()
            dataset.license = new_license
            dataset.save()
            dataset_count += 1
    # Delete unnecessary licenses
    for license in licenses:
        if license.title not in ['Open Data Commons Open Database License (ODbL)',
                                 'Licence Ouverte / Open Licence version 2.0']:
            license.delete()
            license_count += 1

    log.info(f'{dataset_count} dataset objects modified')
    log.info(f'{license_count} license objects deleted')
    log.info('Done')
