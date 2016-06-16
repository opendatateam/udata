# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import codecs
import contextlib
import logging
import lzma
import os
import shutil
import tarfile
from urllib import urlretrieve

import requests

from flask import current_app

from udata.models import (
    Dataset, ResourceBasedTerritoryDataset, TERRITORY_DATASETS
)
from udata.commands import submanager
from udata.core.storages import logos, references, tmp


log = logging.getLogger(__name__)


m = submanager(
    'territories',
    help='Territories specifics operations',
    description='Handle all territories related operations and maintenance'
)


@m.command
def load_logos(filename):
    """Load logos from geologos archive file."""
    if filename.startswith('http'):
        log.info('Downloading GeoLogos bundle: %s', filename)
        filename, _ = urlretrieve(filename, tmp.path('geologos.tar.xz'))

    log.info('Extracting GeoLogos bundle')
    with contextlib.closing(lzma.LZMAFile(filename)) as xz:
        with tarfile.open(fileobj=xz) as f:
            f.extractall(tmp.root)

    log.info('Moving to the final location and cleaning up')
    if os.path.exists(logos.root):
        shutil.rmtree(logos.root)
    shutil.move(tmp.path('logos'), logos.root)
    log.info('Done')


@m.command
def collect_references_files():
    """Retrieve locally CSV files in use for dynamic territories' resources."""
    REFERENCES_PATH = references.root
    if not os.path.exists(REFERENCES_PATH):
        os.makedirs(REFERENCES_PATH)
    if current_app.config.get('ACTIVATE_TERRITORIES'):
        # TERRITORY_DATASETS is a dict of dicts and we want all values
        # that are resource based to collect related files.
        territory_classes = [
            territory_class
            for territory_dict in TERRITORY_DATASETS.values()
            for territory_class in territory_dict.values()
            if issubclass(territory_class, ResourceBasedTerritoryDataset)]
        for territory_class in territory_classes:
            dataset = Dataset.objects.get(id=territory_class.dataset_id)
            for resource in dataset.resources:
                if str(resource.id) != str(territory_class.resource_id):
                    continue
                filename = resource.url.split('/')[-1]
                reference_path = references.path(filename)
                log.info('Found reference: %s', reference_path)
                if os.path.exists(reference_path):
                    log.info('Reference already downloaded')
                    continue
                log.info('Downloading from: %s', resource.url)
                with codecs.open(reference_path, 'w', encoding='utf8') as fd:
                    r = requests.get(resource.url, stream=True)
                    for chunk in r.iter_content(chunk_size=1024):
                        fd.write(chunk.decode('latin-1'))  # TODO: detect?

    log.info('Done')
