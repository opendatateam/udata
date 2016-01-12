# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from udata.commands import submanager

log = logging.getLogger(__name__)


m = submanager(
    'gouvfr',
    help='Data.gouv.fr specifics operations',
    description='Handle all Data.gouv.fr related operations and maintenance'
)
