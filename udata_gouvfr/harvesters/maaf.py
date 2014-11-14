# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import logging
import re

from collections import OrderedDict
from urlparse import urljoin

import dateutil.parser
import slugify

# from bson import ObjectId
from lxml import etree, html
from biryani import baseconv as conv
from voluptuous import Schema, Required, Optional, All, Any, Lower, In, Length, Invalid, MultipleInvalid

from udata.models import db, Dataset, License, Resource, Checksum, SpatialCoverage, Territory
from udata.ext.harvest import backends
from udata.utils import get_by


log = logging.getLogger(__name__)


GRANULARITIES = {
    'commune': 'town',
    'france': 'country',
    'pays': 'country',
}

RE_NAME = re.compile(r'(\{(?P<url>.+)\})?(?P<name>.+)$')

TERRITORIES = {
    'country/fr': '54031e551efbbe1e260b5b53',
    'country/monde': '54031fce1efbbe1e260b5d88',
}


FREQUENCIES = {
    'ponctuelle': 'punctual',
    'temps réel': 'realtime',
    'quotidienne': 'daily',
    'hebdomadaire': 'weekly',
    'bimensuelle': 'fortnighly',
    'mensuelle': 'monthly',
    'bimestrielle': 'bimonthly',
    'trimestrielle': 'quarterly',
    'semestrielle': 'biannual',
    'annuelle': 'annual',
    'triennale': 'triennial',
    'quinquennale': 'quinquennial',
    'aucune': 'unknown',
}

XSD_PATH = os.path.join(os.path.dirname(__file__), 'maaf.xsd')

SSL_COMMENT = '''
Le site exposant les données est protégé par un certificat délivré par l'IGC/A (IGC officielle de l'État).
Une exception de sécurité peut apparaître si votre navigateur ne reconnait pas cette autorité :
vous trouverez  la procédure à suivre pour éviter une telle alerte à l'adresse :
http://www.ssi.gouv.fr/fr/anssi/services-securises/igc-a/modalites-de-verification-du-certificat-de-l-igc-a-rsa-4096.html
'''


def to_date(value):
    return dateutil.parser.parse(value).date()


def email(value):
    if not '@' in value:
        raise Invalid('This email is invalid.')
    return value


def slug(value):
    return slugify.slugify(value, separator='-')


def taglist(value):
    return [slugify.slugify(t, separator='-') for t in value.split(',')]


def force_list(value):
    if not isinstance(value, (list, tuple)):
        return [value]
    return value


def wrap_conv(func):
    def wrapper(value):
        value, errors = func(value)
        if errors:
            raise Invalid(errors)
        return value
    return wrapper


boolean = wrap_conv(conv.guess_bool)
cleanup_text = wrap_conv(conv.cleanup_text)
to_url = wrap_conv(conv.clean_str_to_url(full=True))


schema = Schema({
    Optional('digest'): All(basestring, Length(min=1)),
    'metadata': {
        'author': int,
        'author_email': Any(All(int, email), None),
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
        'notes': All(basestring, cleanup_text),
        'organization': basestring,
        'private': boolean,
        'resources': All(force_list, [{
            'name': basestring,
            'description': All(basestring, cleanup_text),
            'format': All(basestring, Lower, Any('cle', 'csv', 'pdf', 'txt')),
            Optional('last_modified'): All(basestring, to_date),
            'url': All(basestring, to_url),
        }]),
        'state': Any(basestring, None),
        'supplier': basestring,
        'tags': All(basestring, taglist),
        'temporal_coverage_from': None,
        'temporal_coverage_to': None,
        'territorial_coverage': {
            'territorial_coverage_code': All(basestring, Lower, In(TERRITORIES.keys())),
            'territorial_coverage_granularity': All(basestring, Lower, In(GRANULARITIES.keys())),
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
                    self.enqueue(urljoin(directory, href))
                else:
                    log.debug('Skip %s', href)

    def process(self, url, *args, **kwargs):
        log.debug('Processing URL: %s', url)
        response = self.get(url)
        xml = self.parse_xml(response.text)
        metadata = xml['metadata']

        dataset, created = Dataset.objects.get_or_create(extras__remote_id=metadata['id'], auto_save=False)

        dataset.title = metadata['title']
        dataset.frequency = FREQUENCIES.get(metadata['frequency'], 'unknown')
        dataset.description = metadata['notes']
        dataset.private = metadata['private']
        dataset.tags = sorted(set(metadata['tags']))

        if metadata.get('license_id'):
            dataset.license = License.objects.get(id=metadata['license_id'])

        if self.source.owner:
            dataset.owner = self.source.owner

        if self.source.organization:
            dataset.organization = self.source.organization
            dataset.supplier = self.source.organization

        if metadata.get('temporal_coverage_from') and metadata.get('temporal_coverage_to'):
            dataset.temporal_coverage = db.DateRange(
                start=metadata['temporal_coverage_from'],
                end=metadata['temporal_coverage_to']
            )

        if metadata.get('territorial_coverage_code') or metadata.get('territorial_coverage_granularity'):
            dataset.spatial = SpatialCoverage()

            if metadata.get('territorial_coverage_granularity'):
                dataset.spatial.granularity = GRANULARITIES.get(metadata['territorial_coverage_granularity'])

            if metadata.get('territorial_coverage_code'):
                territory_id = TERRITORIES[metadata['territorial_coverage_code']]
                territory = Territory.objects.get(id=territory_id)
                dataset.spatial.territories = [territory.reference()]

        dataset.resources = []
        cle = get_by(metadata['resources'], 'format', 'cle')
        for row in metadata['resources']:
            if row['format'] == 'cle':
                continue
            else:
                resource = Resource(
                    title=row['name'],
                    description=row['description'] + '\n' + SSL_COMMENT,
                    type='remote',
                    url=row['url'],
                    format=row['format']
                )
                if resource.format == 'csv' and cle:
                    resource.checksum = Checksum(type='sha256', value=self.get(cle['url']).text)
                if row.get('last_modified'):
                    resource.modified = row['last_modified']
                dataset.resources.append(resource)

        dataset.extras.update((r['key'], r['value']) for r in metadata['extras'])
        if metadata.get('author'):
            dataset.extras['author'] = metadata['author']
        if metadata.get('author_email'):
            dataset.extras['author_email'] = metadata['author_email']
        if metadata.get('maintainer'):
            dataset.extras['maintainer'] = metadata['maintainer']
        if metadata.get('maintainer_email'):
            dataset.extras['maintainer_email'] = metadata['maintainer_email']

        return dataset

    def parse_xml(self, xml):
        root = etree.fromstring(xml.encode('utf8'))
        self.xsd.validate(root)
        _, tree = dictize(root)
        try:
            return schema(tree)
        except MultipleInvalid as e:
            for error in e.errors:
                field = '.'.join(str(p) for p in e.path)
                path = e.path
                data = tree
                while path:
                    attr = path.pop(0)
                    try:
                        data = data[attr]
                    except:
                        data = None
                try:
                    data = str(data)
                except:
                    pass
                log.error('[%s] %s: %s', field, str(e), data)
            raise

    @property
    def xsd(self):
        if not getattr(self, '_xsd', None):
            with open(XSD_PATH) as f:
                doc = etree.parse(f)
            self._xsd = etree.XMLSchema(doc)
        return self._xsd
