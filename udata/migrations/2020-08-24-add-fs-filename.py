"""
The purpose here is to fill every resource with a fs_filename string field.
"""

import logging
from urllib.parse import urlparse

from udata.core import storages
from udata.models import CommunityResource, Dataset

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Processing resources.")

    datasets = Dataset.objects().no_cache().timeout(False)
    for dataset in datasets:
        save_res = False
        for resource in dataset.resources:
            if resource.url.startswith(storages.resources.base_url):
                parsed = urlparse(resource.url)
                fs_name = parsed.path.replace("/resources/", "")
                resource.fs_filename = fs_name
                save_res = True
            elif resource.fs_filename is not None:
                resource.fs_filename = None
                save_res = True
        if save_res:
            try:
                dataset.save()
            except Exception as e:
                log.warning(e)
                pass

    log.info("Processing community resources.")

    community_resources = CommunityResource.objects().no_cache().timeout(False)
    for community_resource in community_resources:
        save_res = False
        if community_resource.url.startswith(storages.resources.base_url):
            parsed = urlparse(community_resource.url)
            fs_name = parsed.path.replace("/resources/", "")
            community_resource.fs_filename = fs_name
            save_res = True
        elif community_resource.fs_filename is not None:
            community_resource.fs_filename = None
            save_res = True
        if save_res:
            try:
                community_resource.save()
            except Exception as e:
                log.warning(e)
                pass

    log.info("Completed.")
