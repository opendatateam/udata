# -*- coding: utf-8 -*-


import os
import uuid

from udata.models import Resource
from .base import BaseBackend
from udata.utils import get_by

URL = 'https://opendata.stat.gov.rs/data/WcfJsonRestService.Service1.svc/dataset/%s/1/'
RESOURCE_FILE_TYPE = ['json', 'csv']


class StatistikaBackend(BaseBackend):
    display_name = 'Statistika'
    verify_ssl = False

    def initialize(self):
        response = self.get(self.source.url)

        if response.status_code == 200:

            data = response.json()

            self.job.data = {
                'response_data': data,
                'remote_categories': {i['IDkategorija']: i['kategorija'] for i in data}
            }

            for item in list(self.job.data['remote_categories'].keys()):
                self.add_item(item)

    def process(self, item):
        dataset = self.get_dataset(item.remote_id)

        category_resources = [x for x in self.job.data['response_data'] if x['IDkategorija'] == item.remote_id]

        catregory_name = self.job.data['remote_categories'][item.remote_id]

        dataset.title = catregory_name
        dataset.tags = ['statistika', catregory_name.lower().strip(), ]

        for res in category_resources:
            resource_url = URL % res['IDAgregant']

            for filetype in RESOURCE_FILE_TYPE:
                resource_url_file_type = os.path.join(resource_url, filetype)

                resource_id = uuid.uuid3(
                    uuid.NAMESPACE_DNS, resource_url_file_type)

                try:
                    resource = get_by(dataset.resources, 'id', resource_id)
                except Exception:
                    resource = Resource(id=resource_id)
                    dataset.resources.append(resource)

                if not resource:
                    resource = Resource(id=resource_id)
                    dataset.resources.append(resource)

                resource.title = res.get('agregant', '') or ''
                resource.url = resource_url_file_type
                resource.filetype = 'remote'
                resource.type = 'api'
                if filetype == 'json':
                    resource.format = 'json'
                    resource.mime = 'application/json'
                elif filetype:
                    resource.format = 'csv'
                    resource.mime = 'text/csv'

        return dataset

