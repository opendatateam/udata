# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
from datetime import datetime

log = logging.getLogger(__name__)


def archive(dataset):
    """Archive a dataset"""
    if dataset.archived:
        log.warning('Dataset %s already archived, bumping date', dataset)
    dataset.archived = datetime.now()
    dataset.save()
    log.info('Archived dataset %s', dataset)
