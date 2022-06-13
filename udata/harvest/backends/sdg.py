# -*- coding: utf-8 -*-


import os
import uuid
import re
from datetime import datetime

from udata.models import Resource
from .base import BaseBackend
from udata.utils import get_by

URL = 'https://opendata.stat.gov.rs/data/WcfJsonRestService.Service1.svc/datasetsdg/%s/1/'
RESOURCE_FILE_TYPE = ['json', 'csv']
TAG_RE = re.compile('<.*?>')
DATETIME_FORMAT = '%m/%d/%Y %I:%M:%S %p'
FREQ_LIST = ['unknown', 'punctual', 'continuous', 'hourly', 'fourTimesADay', 'threeTimesADay', 'semidaily',
             'daily', 'fourTimesAWeek', 'threeTimesAWeek', 'semiweekly', 'weekly', 'biweekly',
             'threeTimesAMonth', 'semimonthly', 'monthly', 'bimonthly', 'quarterly', 'threeTimesAYear',
             'semiannual', 'annual', 'biennial', 'triennial', 'quinquennial', 'irregular']


def remove_html_tags(text):
    text = text.replace('<br>', ' - ')
    return re.sub(TAG_RE, '', text)


class SDGBackend(BaseBackend):
    display_name = 'SDG'
    verify_ssl = False

    def initialize(self):
        response = self.get(self.source.url)

        if response.status_code == 200:

            data = response.json()
            for item in data:

                frequency = item.get('frequency').strip()
                if not frequency:
                    frequency = 'unknown'

                self.add_item(
                    item['IDAgregant'],
                    title=remove_html_tags(item['agregant']),
                    description=item['ToolTipI'],
                    tags=['statistika', 'sdg', item.get('kategorija').lower().strip(), ],
                    created_at=item.get('VOD'),
                    last_modified=item.get('DatPoslProm'),
                    frequency=frequency,
                    link=item.get('link').strip(),
                    remote_id=item['IDAgregant'],
                )

    def process(self, item):
        kwargs = item.kwargs
        dataset = self.get_dataset(item.remote_id)

        dataset.title = kwargs['title']
        dataset.description = kwargs['description'] + ' ' + kwargs['link']if kwargs['link'] else kwargs['description']
        dataset.tags = kwargs.get('tags')
        created_at = datetime.strptime(
            kwargs.get('created_at'),
            DATETIME_FORMAT) if kwargs.get('created_at') else dataset.created_at
        dataset.created_at = created_at
        last_modified = datetime.strptime(
            kwargs.get('last_modified'),
            DATETIME_FORMAT) if kwargs.get('last_modified') else dataset.last_modified
        dataset.last_modified = last_modified
        dataset.frequency = kwargs['frequency']
        dataset.private = False

        resource_url = URL % item.remote_id

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

            resource.title = kwargs['title']
            resource.created_at = created_at
            resource.modified = last_modified
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

