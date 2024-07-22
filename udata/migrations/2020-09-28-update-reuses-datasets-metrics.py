"""
The purpose here is to update every reuse's datasets metrics
after the PR https://github.com/opendatateam/udata/pull/2531
"""

import logging

from udata.models import Reuse

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Processing reuses.")

    reuses = Reuse.objects().no_cache().timeout(False)
    for reuse in reuses:
        reuse.count_datasets()

    log.info("Completed.")
