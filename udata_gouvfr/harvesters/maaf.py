# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import logging
import re

from collections import OrderedDict
from urlparse import urljoin

import chardet

from lxml import etree, html
from voluptuous import Schema, Optional, All, Any, Lower, In, Length

from udata.models import db, License, Resource, Checksum, SpatialCoverage
from udata.harvest import backends
from udata.harvest.filters import (
    boolean, email, to_date, taglist, force_list, normalize_string, is_url
)
from udata.utils import get_by


log = logging.getLogger(__name__)

GRANULARITIES = {
    'commune': 'fr/town',
    'france': 'country',
    'pays': 'country',
}

RE_NAME = re.compile(r'(\{(?P<url>.+)\})?(?P<name>.+)$')

ZONES = {
    'country/fr': 'country/fr',
    'country/monde': 'country-group/world',
}


FREQUENCIES = {
    'ponctuelle': 'punctual',
    'temps réel': 'continuous',
    'quotidienne': 'daily',
    'hebdomadaire': 'weekly',
    'bimensuelle': 'semimonthly',
    'mensuelle': 'monthly',
    'bimestrielle': 'bimonthly',
    'trimestrielle': 'quarterly',
    'semestrielle': 'semiannual',
    'annuelle': 'annual',
    'triennale': 'triennial',
    'quinquennale': 'quinquennial',
    'aucune': 'unknown',
}

XSD_PATH = os.path.join(os.path.dirname(__file__), 'maaf.xsd')

SSL_COMMENT = '''
Le site exposant les données est protégé par un certificat délivré par
l'IGC/A (IGC officielle de l'État).
Une exception de sécurité peut apparaître si votre navigateur ne reconnait
pas cette autorité :
vous trouverez  la procédure à suivre pour éviter une telle alerte
à l'adresse :
http://www.ssi.gouv.fr/fr/anssi/services-securises/igc-a/\
modalites-de-verification-du-certificat-de-l-igc-a-rsa-4096.html
'''

schema = Schema({
    Optional('digest'): All(basestring, Length(min=1)),
    'metadata': {
        'author': basestring,
        'author_email': Any(All(basestring, email), None),
        'extras': [{
            'key': basestring,
            'value': basestring
        }],
        'frequency': All(Lower, In(FREQUENCIES.keys())),
        'groups': Any(None, All(Lower, 'agriculture et alimentation')),
        'id': basestring,
        'license_id': Any('fr-lo'),
        'maintainer': Any(basestring, None),
        'maintainer_email': Any(All(basestring, email), None),
        'notes': All(basestring, normalize_string),
        'organization': basestring,
        'private': boolean,
        'resources': All(force_list, [{
            'name': basestring,
            'description': All(basestring, normalize_string),
            'format': All(basestring, Lower, Any('cle', 'csv', 'pdf', 'txt')),
            Optional('last_modified'): All(basestring, to_date),
            'url': All(basestring, is_url(full=True)),
        }]),
        'state': Any(basestring, None),
        'supplier': basestring,
        'tags': All(basestring, taglist),
        'temporal_coverage_from': None,
        'temporal_coverage_to': None,
        'territorial_coverage': {
            'territorial_coverage_code':
            All(basestring, Lower, In(ZONES.keys())),
            'territorial_coverage_granularity':
            All(basestring, Lower, In(GRANULARITIES.keys())),
        },
        'title': basestring,
    },
}, required=True, extra=True)


LIST_KEYS = 'extras', 'resources'


def extract(element):
    lst = filter(lambda r: isinstance(r[0], basestring), map(dictize, element))
    for key in LIST_KEYS:
        values = [v for k, v in filter(lambda r: r[0] == key, lst)]
        if values:
            lst = filter(lambda r: r[0] != key, lst) + [(key, values)]
    return lst


def dictize(element):
    return element.tag, OrderedDict(extract(element)) or element.text


@backends.register
class MaafBackend(backends.BaseBackend):
    name = 'maaf'
    display_name = 'MAAF'
    verify_ssl = False

    def initialize(self):
        '''Parse the index pages HTML to find link to dataset descriptors'''
        directories = [self.source.url]
        while directories:
            directory = directories.pop(0)
            response = self.get(directory)
            root = html.fromstring(response.text)
            for link in root.xpath('//ul/li/a')[1:]:  # Skip parent directory.
                href = link.get('href')
                if href.endswith('/'):
                    directories.append(urljoin(directory, href))
                elif href.lower().endswith('.xml'):
                    self.add_item(urljoin(directory, href))
                else:
                    log.debug('Skip %s', href)

    def process(self, item):
        response = self.get(item.remote_id)
        encoding = chardet.detect(response.content)['encoding']
        xml = self.parse_xml(response.content.decode(encoding))
        metadata = xml['metadata']

        # Resolve and remote id from metadata
        item.remote_id = metadata['id']
        dataset = self.get_dataset(metadata['id'])

        dataset.title = metadata['title']
        dataset.frequency = FREQUENCIES.get(metadata['frequency'], 'unknown')
        dataset.description = metadata['notes']
        dataset.private = metadata['private']
        dataset.tags = sorted(set(metadata['tags']))

        if metadata.get('license_id'):
            dataset.license = License.objects.get(id=metadata['license_id'])

        if (metadata.get('temporal_coverage_from') and
                metadata.get('temporal_coverage_to')):
            dataset.temporal_coverage = db.DateRange(
                start=metadata['temporal_coverage_from'],
                end=metadata['temporal_coverage_to']
            )

        if (metadata.get('territorial_coverage_code') or
                metadata.get('territorial_coverage_granularity')):
            dataset.spatial = SpatialCoverage()

            if metadata.get('territorial_coverage_granularity'):
                dataset.spatial.granularity = GRANULARITIES.get(
                    metadata['territorial_coverage_granularity'])

            if metadata.get('territorial_coverage_code'):
                dataset.spatial.zones = [
                    ZONES[metadata['territorial_coverage_code']]]

        dataset.resources = []
        cle = get_by(metadata['resources'], 'format', 'cle')
        for row in metadata['resources']:
            if row['format'] == 'cle':
                continue
            else:
                resource = Resource(
                    title=row['name'],
                    description=(
                        row['description'] + '\n\n' + SSL_COMMENT).strip(),
                    filetype='remote',
                    url=row['url'],
                    format=row['format']
                )
                if resource.format == 'csv' and cle:
                    resource.checksum = Checksum(
                        type='sha256', value=self.get(cle['url']).text)
                if row.get('last_modified'):
                    resource.modified = row['last_modified']
                dataset.resources.append(resource)

        if metadata.get('author'):
            dataset.extras['author'] = metadata['author']
        if metadata.get('author_email'):
            dataset.extras['author_email'] = metadata['author_email']
        if metadata.get('maintainer'):
            dataset.extras['maintainer'] = metadata['maintainer']
        if metadata.get('maintainer_email'):
            dataset.extras['maintainer_email'] = metadata['maintainer_email']
        for extra in metadata['extras']:
            dataset.extras[extra['key']] = extra['value']

        return dataset

    def parse_xml(self, xml):
        root = etree.fromstring(xml.encode('utf8'))
        self.xsd.validate(root)
        _, tree = dictize(root)
        return self.validate(tree, schema)

    @property
    def xsd(self):
        if not getattr(self, '_xsd', None):
            with open(XSD_PATH) as f:
                doc = etree.parse(f)
            self._xsd = etree.XMLSchema(doc)
        return self._xsd
