# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from flask import json

from udata.api import api
from udata.commands import submanager

from flask.ext.restplus.swagger import Swagger

log = logging.getLogger(__name__)


m = submanager('api',
    help='API related operations',
    description='Handle all API related operations and maintenance'
)


@m.option('-p', '--pretty', action='store_true', default=False, help='Pretty print (sort')
def swagger(pretty):
    '''Dump the swagger specifications'''
    data = Swagger(api).as_dict()
    kwargs = dict(indent=4) if pretty else {}
    print(json.dumps(data, **kwargs))
