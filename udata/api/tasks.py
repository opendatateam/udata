# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import udata_piwik
from udata.tasks import get_logger, task

log = get_logger(__name__)


@task
def send_to_piwik(url, **params):
    log.debug('Sending to piwik: {url}'.format(url=url))
    udata_piwik.track(url, **params)
