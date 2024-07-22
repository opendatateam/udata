"""
The purpose here is to update every community resource's metadata 'schema'
with a new format (string to object)
"""

import logging

from udata.models import CommunityResource

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Processing community resources.")

    community_resources = CommunityResource.objects().no_cache().timeout(False)
    for resource in community_resources:
        save_res = False
        if hasattr(resource, "schema"):
            schema = resource.schema
            resource.schema = {}
            if schema is not None and isinstance(schema, str):
                resource.schema = {"name": schema}
            save_res = True
        if save_res:
            try:
                resource.save()
            except Exception as e:
                log.warning(e)
                pass

    log.info("Completed.")
