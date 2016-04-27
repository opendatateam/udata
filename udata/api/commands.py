# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import os

from flask import json

from udata.api import api
from udata.commands import submanager

log = logging.getLogger(__name__)


m = submanager(
    'api',
    help='API related operations',
    description='Handle all API related operations and maintenance'
)


def json_to_file(data, filename, pretty=False):
    '''Dump JSON data to a file'''
    kwargs = dict(indent=4) if pretty else {}
    dirname = os.path.dirname(filename)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    dump = json.dumps(api.__schema__, **kwargs)
    with open(filename, 'wb') as f:
        f.write(dump.encode('utf-8'))


@m.option('filename', help='The output filename')
@m.option('-p', '--pretty', action='store_true', default=False,
          help='Pretty print')
def swagger(filename, pretty):
    '''Dump the swagger specifications'''
    json_to_file(api.__schema__, filename, pretty)


@m.option('filename', help='The output filename')
@m.option('-p', '--pretty', action='store_true', default=False,
          help='Pretty print')
@m.option('-u', '--urlvars', action='store_true', default=False,
          help='Export query strings')
@m.option('-s', '--swagger', action='store_true', default=False,
          help='Export Swagger specifications')
def postman(filename, pretty, urlvars, swagger):
    '''Dump the API as a Postman collection'''
    data = api.as_postman(urlvars=urlvars, swagger=swagger)
    json_to_file(data, filename, pretty)
