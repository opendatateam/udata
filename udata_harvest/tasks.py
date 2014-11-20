# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.tasks import job, get_logger, chord

from . import actions

log = get_logger(__name__)


@job('harvest')
def initialize_harvest(self, source_id):
    log.info('Launching harvest job for source "%s"', source_id)
    actions.launch(source_id)

    items = []
    finalize = harvest_finalize.subtask(source_id)
    items = [harvest_item.subtask(source_id, item_id) for item_id in items]
    flow = chord(items)(finalize)


@job('harvest-item')
def harvest_item(self, source_id, item_id):
    pass


@job('harvest-finalize')
def harvest_finalize(self, source_id):
    pass
