# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from flask import json

from udata.api import api
from udata.commands import submanager

# from flask.ext.restplus.swagger import Swagger

log = logging.getLogger(__name__)


m = submanager(
    'api',
    help='API related operations',
    description='Handle all API related operations and maintenance'
)


@m.option('-p', '--pretty', action='store_true', default=False,
          help='Pretty print')
def swagger(pretty):
    '''Dump the swagger specifications'''
    # data = Swagger(api).as_dict()
    kwargs = dict(indent=4) if pretty else {}
    print(json.dumps(api.__schema__, **kwargs))


@m.option('-p', '--pretty', action='store_true', default=False,
          help='Pretty print')
@m.option('-u', '--urlvars', action='store_true', default=False,
          help='Export query strings')
@m.option('-s', '--swagger', action='store_true', default=False,
          help='Export Swagger specifications')
def postman(pretty, urlvars, swagger):
    '''Dump the API as a Postman collection'''
    kwargs = dict(indent=4) if pretty else {}
    data = api.as_postman(urlvars=urlvars, swagger=swagger)
    print(json.dumps(data, **kwargs))
