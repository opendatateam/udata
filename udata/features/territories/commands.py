# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import codecs
import logging
import os

import requests

from udata.models import (
    Dataset, GeoZone, TERRITORY_DATASETS, ResourceBasedTerritoryDataset
)
from udata.commands import submanager
from udata.core.storages import logos, references

log = logging.getLogger(__name__)


m = submanager(
    'territories',
    help='Territories specifics operations',
    description='Handle all territories related operations and maintenance'
)


@m.command
def fetch_territories_logos():
    """Retrieves images of logos from wikimedia."""
    log.info('As of February 2016, the download is about 1GB. Time to relax.')
    # A bit tricky but otherwise you cannot guess the final file URL.
    DBPEDIA_MEDIA_URL = 'http://commons.wikimedia.org/wiki/Special:FilePath/'
    LOGOS_FOLDER_PATH = logos.root
    if not os.path.exists(LOGOS_FOLDER_PATH):
        os.makedirs(LOGOS_FOLDER_PATH)

    geozones = GeoZone.objects.filter(level='fr/town')
    for geozone in geozones.only('logo'):
        if geozone.logo:
            filepath = logos.path(geozone.logo.filename)
            if os.path.exists(filepath):
                continue
            r = requests.get(DBPEDIA_MEDIA_URL + geozone.logo.filename,
                             stream=True)
            if r.status_code == 404:
                continue
            with open(filepath, 'wb') as file_destination:
                for chunk in r.iter_content(chunk_size=1024):
                    file_destination.write(chunk)

    log.info('Done')


@m.command
def collect_references_files():
    """Retrieve locally CSV files in use for dynamic territories' resources."""
    REFERENCES_PATH = references.root
    if not os.path.exists(REFERENCES_PATH):
        os.makedirs(REFERENCES_PATH)
    for territory_class in TERRITORY_DATASETS.values():
        if not issubclass(territory_class, ResourceBasedTerritoryDataset):
            continue
        dataset = Dataset.objects.get(id=territory_class.dataset_id)
        for resource in dataset.resources:
            if resource.id == territory_class.resource_id:
                break
            filename = resource.url.split('/')[-1]
            reference_path = references.path(filename)
            if os.path.exists(reference_path):
                continue
            with codecs.open(reference_path, 'w', encoding='utf8') as fd:
                r = requests.get(resource.url, stream=True)
                for chunk in r.iter_content(chunk_size=1024):
                    fd.write(chunk.decode('latin-1'))  # TODO: detect?

    log.info('Done')
