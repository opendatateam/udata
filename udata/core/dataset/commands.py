# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import logging
import requests

from udata.commands import manager
from udata.models import License, DEFAULT_LICENSE
from .tasks import send_frequency_reminder

log = logging.getLogger(__name__)

FLAGS_MAP = {
    'domain_content': 'domain_content',
    'domain_data': 'domain_data',
    'domain_software': 'domain_software',
    'is_generic': 'generic',
    'is_okd_compliant': 'okd_compliant',
    'is_osi_compliant': 'osi_compliant',
}


@manager.command
def licenses(filename):
    '''Feed the licenses from a JSON file'''
    if filename.startswith('http'):
        json_licenses = requests.get(filename).json()
    else:
        with open(filename) as fp:
            json_licenses = json.load(fp)

    if len(json_licenses):
        log.info('Dropping existing licenses')
        License.drop_collection()

    for json_license in json_licenses:
        flags = []
        for field, flag in FLAGS_MAP.items():
            if json_license.get(field, False):
                flags.append(flag)

        license = License.objects.create(
            id=json_license['id'],
            title=json_license['title'],
            url=json_license['url'] or None,
            maintainer=json_license['maintainer'] or None,
            flags=flags,
            active=json_license.get('active', False),
        )
        log.info('Added license "%s"', license.title)
    try:
        License.objects.get(id=DEFAULT_LICENSE['id'])
    except License.DoesNotExist:
        License.objects.create(**DEFAULT_LICENSE)
        log.info('Added license "%s"', DEFAULT_LICENSE['title'])
    log.info('Done')


@manager.command
def frequency_reminder():
    """Send a unique email per organization to members

    to remind them they have outdated datasets on the website.
    """
    send_frequency_reminder()
