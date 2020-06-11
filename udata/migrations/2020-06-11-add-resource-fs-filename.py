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
from udata.models import Dataset, Resource

log = logging.getLogger(__name__)


def migrate(db):
    for fs_filename in list(storages.resources.list_files()):
        split_str = fs_filename.split('/')
        dataset_slug = split_str[0]
        dataset = Dataset.objects(slug=dataset_slug).first()

        if dataset:
            match = False

            for resource in dataset.resources:
                if fs_filename in resource.url:
                    match = True
                    resource.fs_filename = fs_filename
                    resource.save()
                    break

            if not match:
                storages.resources.delete(fs_filename)
        else:
            storages.resources.delete(fs_filename)
