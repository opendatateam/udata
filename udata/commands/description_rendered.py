# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import logging
from flask import current_app

from udata.commands import manager
from udata.core.reuse.models import Reuse
from udata.frontend.markdown import mdstrip

log = logging.getLogger(__name__)

@manager.command
def add_description_rendered():
    objects = Reuse.objects(description_rendered__exists=False)
    log.info('Will update %s reuses' % len(objects))
    for reuse in objects:
        reuse.description_rendered = mdstrip(reuse.description)
        reuse.save()
    log.info('Done.')
