"""
This migration sets Dataset/Dataservice.access_type to "open" for those that don't have an access type.
This is necessary because the default value is only applied to new documents,
not existing ones.
"""

import logging

from udata.core.access_type.constants import AccessType
from udata.core.dataservices.models import Dataservice
from udata.core.dataset.models import Dataset

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Processing datasets without access_type...")
    count = Dataset.objects(access_type__exists=False).update(access_type=AccessType.OPEN)
    log.info(f"\tSet access type 'open' for {count} datasets")

    log.info("Processing dataservices without access_type...")
    count = Dataservice.objects(access_type__exists=False).update(access_type=AccessType.OPEN)
    log.info(f"\tSet access type 'open' for {count} dataservices")
