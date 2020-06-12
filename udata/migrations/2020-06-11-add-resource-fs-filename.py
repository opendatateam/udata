'''
The purpose here is to fill every resource with a fs_filename string field.
The migration iterates on every file in the ressource storage.
It extracts the dataset's slug from the file path, retrieves the dataset,
and iterates on the dataset's resources to find the one owning the file.
If one is found the fs_filename field is filled.
If none is found the file is deleted.
'''
import logging

from udata.core import storages
from udata.models import Dataset, Resource, CommunityResource

log = logging.getLogger(__name__)


def migrate(db):
    log.info('Processing resources and community resources')
    for fs_filename in list(storages.resources.list_files()):
        split_str = fs_filename.split('/')
        dataset_slug = split_str[0]
        dataset = Dataset.objects(slug=dataset_slug).first()

        if dataset:
            match_resource = False
            match_community_resource = False

            for resource in dataset.resources:
                if fs_filename in resource.url:
                    match_resource = True
                    resource.fs_filename = fs_filename
                    resource.save()
                    break

            if not match_resource:
                community_resources = CommunityResource.objects(dataset=dataset)
                for community_resource in community_resources:
                    if fs_filename in community_resource.url:
                        match_community_resource = True
                        community_resource.fs_filename = fs_filename
                        community_resource.save()
                        break

            if not match_resource and not match_community_resource:
                storages.resources.delete(fs_filename)
        else:
            storages.resources.delete(fs_filename)
    log.info('Processing organizations logos')
    log.info('Processing reuses logos')
    log.info('Processing users avatars')
