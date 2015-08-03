# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from udata.models import License, Resource
from . import BaseBackend, register
from ..exceptions import HarvestException

log = logging.getLogger(__name__)


@register
class OdsHarvester(BaseBackend):
    name = 'ods'
    verify_ssl = False

    LICENSES = {
        "Open Database License (ODbL)": "odc-odbl",
        "Licence Ouverte (Etalab)": "fr-lo",
        "CC BY-SA": "cc-by-sa",
        "Public Domain": "other-pd"
    }

    FORMATS = {
        'csv': ('CSV', 'csv', 'text/csv'),
        'geojson': ('GeoJSON', 'json', 'application/vnd.geo+json'),
        'json': ('JSON', 'json', 'application/json'),
        'shp': ('Shapefile', 'shp', None),
    }

    @property
    def api_url(self):
        return "{0}/api/datasets/1.0/search/".format(self.source.url)

    def _get_download_url(self, dataset_id, format):
        return ("%s/explore/dataset/%s/download"
                "?format=%s&timezone=Europe/Berlin"
                "&use_labels_for_header=true") % (self.source.url,
                                                  dataset_id,
                                                  format)

    def _get_explore_url(self, dataset_id):
        return "%s/explore/dataset/%s/" % (self.source.url, dataset_id)

    def _get_export_url(self, dataset_id):
        return "%s/explore/dataset/%s/?tab=export" % (self.source.url,
                                                      dataset_id)

    def initialize(self):
        count = 0
        nhits = None
        while nhits is None or count < nhits:
            response = self.get(self.api_url,
                                params={"start": count, "rows": 50})
            response.raise_for_status()
            data = response.json()
            nhits = data["nhits"]
            for dataset in data["datasets"]:
                count += 1
                self.add_item(dataset["datasetid"], dataset=dataset)

    def process(self, item):
        ods_dataset = item.kwargs["dataset"]
        dataset_id = ods_dataset["datasetid"]
        ods_metadata = ods_dataset["metas"]

        if not ods_dataset.get('has_records'):
            msg = 'Dataset {datasetid} has no record'.format(**ods_dataset)
            raise HarvestException(msg)

        dataset = self.get_dataset(item.remote_id)

        dataset.title = ods_metadata['title']
        dataset.frequency = "unknown"
        dataset.description = ods_metadata.get("description", '')
        dataset.private = False

        tags = set()
        if "keyword" in ods_metadata:
            if isinstance(ods_metadata['keyword'], list):
                tags |= set(ods_metadata['keyword'])
            else:
                tags.add(ods_metadata['keyword'])

        if "theme" in ods_metadata:
            if isinstance(ods_metadata["theme"], list):
                for theme in ods_metadata["theme"]:
                    tags.update([t.strip().lower() for t in theme.split(",")])
            else:
                themes = ods_metadata["theme"].split(",")
                tags.update([t.strip().lower() for t in themes])

        dataset.tags = list(tags)

        ods_license_id = ods_metadata.get('license')
        if ods_license_id and ods_license_id in self.LICENSES:
            license_id = self.LICENSES[ods_license_id]
            dataset.license = License.objects.get(id=license_id)

        dataset.resources = []

        self.process_resources(dataset, ods_dataset, ('csv', 'json'))

        if 'geo' in ods_dataset['features']:
            self.process_resources(dataset, ods_dataset, ('geojson', 'shp'))

        dataset.extras["ods:url"] = self._get_explore_url(dataset_id)
        if "references" in ods_metadata:
            dataset.extras["ods:references"] = ods_metadata["references"]
        dataset.extras["ods:has_records"] = ods_dataset["has_records"]

        return dataset

    def process_resources(self, dataset, data, formats):
        dataset_id = data["datasetid"]
        ods_metadata = data["metas"]
        for format in formats:
            label, udata_format, mime = self.FORMATS[format]
            resource = Resource(
                title='Export au format {0}'.format(label),
                type='remote',
                url=self._get_download_url(dataset_id, format),
                format=udata_format,
                mime=mime)
            resource.modified = ods_metadata["modified"]
            dataset.resources.append(resource)
