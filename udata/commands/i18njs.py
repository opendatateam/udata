# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import logging
import os
import re

import itertools

from glob import iglob
from os.path import join, exists

from udata.commands import manager

log = logging.getLogger(__name__)


@manager.command
def i18njs(path, domain='udata'):
    '''
    Extract translatables javascripts strings

    String are extracted from:

    * Javascript files (*.js) from ``i18n._()`` calls
    * Handlebars templates (*.hbs) {_ ""} helper calls
    '''
    catalog = {}
    path = path or join(os.getcwd(), 'js')
    catalog_filename = join(path, 'locales', '{}.en.json'.format(domain))
    if exists(catalog_filename):
        with open(catalog_filename) as f:
            catalog = json.load(f)

    specs = {
        '*.js': (
            re.compile(r'i18n\._\(\s*"(.*?)"\s*\)'),
            re.compile(r'i18n\._\(\s*\'(.*?)\'\s*\)'),
        ),
        '*.hbs': (
            re.compile(r'{{_\s*"(.*?)"\s*}}'),
            re.compile(r'{{_\s*\'(.*?)\'\s*}}'),
        ),
    }
    dirs = ('js', 'templates')

    roots = (join(path or os.getcwd(), d) for d in dirs)
    walks = itertools.chain(*(os.walk(root) for root in roots))
    dirnames = (d for d, _, _ in walks)
    for dirname, (pattern, regexps) in itertools.product(dirnames, specs.items()):
        for filename in iglob(join(dirname, pattern)):
            print 'Extracting messages from {0}'.format(filename)
            content = open(filename, 'r').read()
            for regexp in regexps:
                for match in regexp.finditer(content):
                    key = match.group(1)
                    if not key in catalog:
                        catalog[key] = key

    with open(catalog_filename, 'wb') as f:
        json.dump(catalog, f, sort_keys=True, indent=4)
