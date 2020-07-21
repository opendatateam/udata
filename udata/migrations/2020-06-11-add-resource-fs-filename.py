'''
The purpose here is to fill every resource with a fs_filename string field.
'''
import logging
from urllib.parse import urlparse

from udata.models import Dataset, CommunityResource

log = logging.getLogger(__name__)


def migrate(db):
    log.info('Processing resources.')

    datasets = Dataset.objects().no_cache().timeout(False)
    for dataset in datasets:
        save_res = False
        for resource in dataset.resources:
            if resource.url.startswith('https://static.data.gouv.fr'):
                parsed = urlparse(resource.url)
                fs_name = parsed.path.strip('/resource/')
                resource.fs_filename = fs_name
                save_res = True
        if save_res:
            try:
                dataset.save()
            except Exception as e:
                log.warning(e)
                pass

    log.info('Processing community resources.')

    community_resources = CommunityResource.objects().no_cache().timeout(False)
    for community_resource in community_resources:
        parsed = urlparse(community_resource.url)
        fs_name = parsed.path.strip('/resource/')
        community_resource.fs_filename = fs_name
        try:
            community_resource.save()
        except Exception as e:
            log.warning(e)
            pass

    log.info('Completed.')
