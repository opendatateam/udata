# -*- coding: utf-8 -*-


import sys
import re
from datetime import datetime
from urllib.parse import urlparse

from owslib.csw import CatalogueServiceWeb

from .base import BaseBackend
from udata.models import Resource, License


def normalize_url(url):
    url_obj = urlparse(url.replace('\n', ''))
    if not url_obj.scheme:
        return 'http://%s' % url
    return url


class RGZBackend(BaseBackend):
    '''
    Republicki geodetski zavod
    CSW URL = http://metakatalog.geosrbija.rs/geonetwork/srv/srp/csw-opendata
    '''

    display_name = 'Harvester RGZ'

    def initialize(self):

        csw = CatalogueServiceWeb(self.source.url)
        csw.getrecords2(
            esn='full',
            maxrecords=300,
            typenames='gmd:MD_Metadata',
            format='application/xml',
            outputschema='http://www.isotc211.org/2005/gmd'
        )
        for identifier, record in list(csw.records.items()):

            item = {
                'remote_id': identifier,
                'title': record.identification.title,
                'description': record.identification.abstract,
                'last_modified': datetime.strptime(record.datestamp.split('T')[0], '%Y-%m-%d'),
                'resources': [],
                'keywords': []
            }
            for ci_date in record.identification.date:
                if 'creation' == ci_date.type:
                    item['created_at'] = datetime.strptime(ci_date.date.split('T')[0], '%Y-%m-%d')
                if 'revision' == ci_date.type:
                    item['last_modified'] = datetime.strptime(ci_date.date.split('T')[0], '%Y-%m-%d')

            for element in record.distribution.online:
                element_dict = element.__dict__
                element_dict['format'] = re.search(r'\((.*?)\)', record.distribution.format).group(1)
                item['resources'].append(element_dict)

            for element in record.identification.keywords:
                item['keywords'] += element['keywords']

            self.add_item(identifier, item=item)

    def process(self, item):
        dataset = self.get_dataset(item.remote_id)

        kwargs = item.kwargs
        item = kwargs['item']

        dataset.title = item['title']
        dataset.license = License.guess('cc-by')
        dataset.tags = ['rgz', ] + item['keywords']
        dataset.description = item['description']
        dataset.created_at = item['created_at']
        dataset.resources = []

        for element in item['resources']:
            dataset.resources.append(Resource(
                title=element['name'] or item['title'],
                description=element['description'],
                url=normalize_url(element['url']),
                filetype='remote',
                format=element['format']
            ))

        dataset.extras['harvest:name'] = self.source.name

        return dataset

