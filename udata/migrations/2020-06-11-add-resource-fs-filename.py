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
from udata.core.dataset.models import get_resource

log = logging.getLogger(__name__)


def migrate(db):
    print('Processing resources and community resources.')

    resource_deletion_count = 0
    avatar_deletion_count = 0
    image_deletion_count = 0

    # Parse every resources URL to make an index out of it
    resource_index = dict()
    datasets = Dataset.objects()
    for dataset in datasets:
        for resource in dataset.resources:
            if resource.url.startswith('https://static.data.gouv.fr'):
                parsed = urlparse(resource.url)
                fs_name = parsed.path.strip('/resource/')
                resource_index[fs_name] = resource.id

    # Add community resources URL to the index
    community_resources = CommunityResource.objects()
    for community_resource in community_resources:
        parsed = urlparse(community_resource.url)
        fs_name = parsed.path.strip('/resource/')
        resource_index[fs_name] = community_resource.id

    print(f'Length of resources index: {len(resource_index)}')

    for fs_filename in storages.resources.list_files():
        if fs_filename in resource_index.keys():
            resource = get_resource(resource_index[fs_filename])
            resource.fs_filename = fs_filename
            try:
                resource.save()
            except Exception as e:
                print(e)
                pass
        else:
            resource_deletion_count += 1
            storages.resources.delete(fs_filename)

    print('Processing organizations logos and users avatars.')
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

    print('Processing reuses logos.')
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

    print('Completed.')
    print(f'{resource_deletion_count} objects of the resources storage were deleted.')
    print(f'{avatar_deletion_count} objects of the avatars storage were deleted.')
    print(f'{image_deletion_count} objects of the images storage were deleted.')
