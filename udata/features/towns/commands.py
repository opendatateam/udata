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

from udata.models import Dataset, ResourceBasedTownDataset
from udata.commands import submanager
from udata.core.storages import logos, references, tmp


log = logging.getLogger(__name__)


m = submanager(
    'towns',
    help='Towns specifics operations',
    description='Handle all towns related operations and maintenance'
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
    """Retrieve locally CSV files in use for dynamic towns' resources."""
    REFERENCES_PATH = references.root
    if not os.path.exists(REFERENCES_PATH):
        os.makedirs(REFERENCES_PATH)
    if current_app.config.get('ACTIVATE_TOWNS'):
        from udata.models import TOWN_DATASETS
        for town_class in TOWN_DATASETS.values():
            if not issubclass(town_class, ResourceBasedTownDataset):
                continue
            dataset = Dataset.objects.get(id=town_class.dataset_id)
            for resource in dataset.resources:
                if resource.id == town_class.resource_id:
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
