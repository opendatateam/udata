'''
The purpose here is to fill every resource with a fs_filename string field.
The migration iterates on every file in the ressource storage.
It extracts the dataset's slug from the file path, retrieves the dataset,
and iterates on the dataset's resources to find the one owning the file.
If one is found the fs_filename field is filled.
If none is found the file is deleted.
'''
import logging
from urllib.parse import urlparse

from udata.core import storages
from udata.models import Dataset, CommunityResource, Organization, User, Reuse

log = logging.getLogger(__name__)


def migrate(db):
    log.info('Processing resources and community resources.')

    resource_deletion_count = 0
    avatar_deletion_count = 0
    image_deletion_count = 0

    # Parse every resources URL to make a list of it
    resource_parsed_url_list = list()
    datasets = Dataset.objects()
    for dataset in datasets:
        for resource in dataset.resources:
            # Takes only localy stored resources
            if resource.filetype == 'file':
                parsed = urlparse(resource.url)
                fs_name = parsed.path.strip('/resource/')
                resource_parsed_url_list.append(fs_name)

    # Add community resources URL to the list
    community_resources = CommunityResource.objects()
    for community_resource in community_resources:
        parsed = urlparse(community_resource.url)
        fs_name = parsed.path.strip('/resource/')
        resource_parsed_url_list.append(fs_name)

    # Diff between urls list and fs files list
    for fs_filename in storages.resources.list_files():
        if fs_filename in resource_parsed_url_list:
            continue
        else:
            resource_deletion_count += 1
            storages.resources.delete(fs_filename)

    log.info('Processing organizations logos and users avatars.')
    orgs = Organization.objects()
    users = User.objects()
    org_index = dict()
    for org in orgs:
        if org.logo.filename:
            split_filename = org.logo.filename.split('.')
            org_index[str(org.id)] = split_filename[0]

    user_index = dict()
    for user in users:
        if user.avatar.filename:
            split_filename = user.avatar.filename.split('.')
            user_index[str(user.id)] = split_filename[0]

    for fs_filename in storages.avatars.list_files():
        match_org = False
        match_user = False
        for key, value in org_index.items():
            if fs_filename.startswith(value):
                match_org = True
                break
        for key, value in user_index.items():
            if fs_filename.startswith(value):
                match_user = True
                break
        if not match_org and not match_user:
            avatar_deletion_count += 1
            storages.avatars.delete(fs_filename)

    log.info('Processing reuses logos.')
    reuses = Reuse.objects()
    reuses_index = dict()
    for reuse in reuses:
        if reuse.image.filename:
            split_filename = reuse.image.filename.split('.')
            reuses_index[str(reuse.id)] = split_filename[0]

    for fs_filename in storages.images.list_files():
        match_reuse = False
        for key, value in reuses_index.items():
            if fs_filename.startswith(value):
                match_reuse = True
                break
        if not match_reuse:
            image_deletion_count += 1
            storages.images.delete(fs_filename)

    log.info('Completed.')
    log.info(f'{resource_deletion_count} objects of the resources storage were deleted.')
    log.info(f'{avatar_deletion_count} objects of the avatars storage were deleted.')
    log.info(f'{image_deletion_count} objects of the images storage were deleted.')
