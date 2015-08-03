# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import re

from udata.models import Dataset, License, Resource
from udata.ext.harvest import backends

log = logging.getLogger(__name__)


@backends.register
class OdsHarvester(backends.BaseBackend):
    name = 'ods'
    verify_ssl = False

    LICENSES = {
        "Open Database License (ODbL)": "odc-odbl",
        "Licence Ouverte (Etalab)": "fr-lo",
        "CC BY-SA": "cc-by-sa",
        "Public Domain": "other-pd"
    }

    @staticmethod
    def create_ods_base_url(url):
        p = r'(?P<scheme>https?)?(://)?(?P<domain>[^/]*)'
        pattern = re.compile(p, re.UNICODE)

        match = pattern.search(url)
        if match:
            groups = match.groupdict()
            scheme = groups["scheme"]
            if scheme is None:
                scheme = 'http'
            domain = groups["domain"]

            if scheme is not None and domain is not None:
                return "%s://%s" % (scheme, domain)

        raise Exception("Invalid OpenDataSoft url : %s" % url)

    def _get_api_url(self, url):
        return "%s/api/datasets/1.0/search/" % self.ods_base_url

    def _get_download_url(self, dataset_id, format):
        return ("%s/explore/dataset/%s/download/"
                "?format=%s&timezone=Europe/Berlin"
                "&use_labels_for_header=true") % (self.ods_base_url,
                                                  dataset_id,
                                                  format)

    def _get_explore_url(self, dataset_id):
        return "%s/explore/dataset/%s/" % (self.ods_base_url, dataset_id)

    def _get_export_url(self, dataset_id):
        return "%s/explore/dataset/%s/?tab=export" % (self.ods_base_url,
                                                      dataset_id)

    def initialize(self):
        self.ods_base_url = OdsHarvester.create_ods_base_url(self.source.url)
        count = 0
        nhits = None
        while nhits is None or count < nhits:
            response = self.get(self._get_api_url(self.source.url),
                                params={"start": count, "rows": 50})
            response.raise_for_status()
            data = response.json()
            nhits = data["nhits"]
            for dataset in data["datasets"]:
                count += 1
                remote_id = "%s@%s" % (dataset["datasetid"],
                                       dataset["metas"]["domain"])
                self.add_item(remote_id, dataset=dataset,
                              ods_base_url=self.ods_base_url)

    def process(self, item):
        self.ods_base_url = item.kwargs["ods_base_url"]
        ods_dataset = item.kwargs["dataset"]
        dataset_id = ods_dataset["datasetid"]
        ods_metadata = ods_dataset["metas"]
        remote_id = item.remote_id
        dataset, created = Dataset.objects.get_or_create(title=remote_id,
                                                         auto_save=False)

        dataset.title = ods_metadata['title']
        dataset.frequency = "unknown"
        if "description" in ods_metadata:
            dataset.description = ods_metadata["description"]
        dataset.private = False
        tags = set()
        if "keyword" in ods_metadata:
            if isinstance(ods_metadata['keyword'], list):
                tags = set(ods_metadata['keyword'])
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

        if self.source.owner:
            dataset.owner = self.source.owner

        if self.source.organization:
            dataset.organization = self.source.organization
            dataset.supplier = self.source.organization

        dataset.resources = []

        resource = Resource(
            title=ods_metadata["title"],
            description=ods_metadata.get("description"),
            type='remote',
            url=self._get_export_url(dataset_id),
            format="html")
        resource.modified = ods_metadata["modified"]
        dataset.resources.append(resource)

        dataset.extras["remote_id"] = remote_id
        dataset.extras["ods_url"] = self._get_explore_url(dataset_id)
        if "references" in ods_metadata:
            dataset.extras["references"] = ods_metadata["references"]
        dataset.extras["has_records"] = ods_dataset["has_records"]

        return dataset
