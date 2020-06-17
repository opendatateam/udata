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
from udata.models import Dataset, CommunityResource, Organization, User, Reuse

log = logging.getLogger(__name__)


def migrate(db):
    log.info('Processing resources and community resources.')

    resource_deletion_count = 0
    avatar_deletion_count = 0
    image_deletion_count = 0

    for fs_filename in storages.resources.list_files():
        split_str = fs_filename.split('/')
        dataset_slug = split_str[0]
        dataset = Dataset.objects(slug=dataset_slug).first()

        if dataset:
            match_resource = False
            match_community_resource = False

            for resource in dataset.resources:
                if resource.url.endwith(fs_filename):
                    match_resource = True
                    resource.fs_filename = fs_filename
                    resource.save()
                    break

            if not match_resource:
                community_resources = CommunityResource.objects(dataset=dataset)
                for community_resource in community_resources:
                    if community_resource.url.endwith(fs_filename):
                        match_community_resource = True
                        community_resource.fs_filename = fs_filename
                        community_resource.save()
                        break

            if not match_resource and not match_community_resource:
                resource_deletion_count += 1
                storages.resources.delete(fs_filename)
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
