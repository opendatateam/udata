# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import contextlib
import logging
import lzma
import os
import shutil
import tarfile
from datetime import date
from urllib import urlretrieve

from udata.models import Dataset, GeoZone, SpatialCoverage
from udata.commands import submanager
from udata.core.storages import logos, tmp


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
def migrate_zones_ids():
    """Migrate zones from old to new ids in datasets.

    Should only be run once with the new version of geozones w/ geohisto.
    """
    counter_datasets = 0
    counter_zones = 0
    counter_towns = 0
    counter_counties = 0
    counter_regions = 0
    counter_drom = 0
    counter_dromcom = 0
    counter_france = 0
    drom_zone = GeoZone.objects(id='country-subset:fr:drom').first()
    dromcom_zone = GeoZone.objects(id='country-subset:fr:dromcom').first()
    france_zone = GeoZone.objects(id='country:fr').first()
    for dataset in Dataset.objects.all():
        if dataset.spatial and dataset.spatial.zones:
            counter_datasets += 1
            new_zones = []
            for zone in dataset.spatial.zones:
                if zone.id.startswith('fr/'):
                    counter_zones += 1
                    country, kind, zone_id = zone.id.split('/')
                    zone_id = zone_id.upper()  # Corsica 2a/b case.
                    if kind == 'town':
                        counter_towns += 1
                        new_zones.append(
                            GeoZone
                            .objects(code=zone_id, level='fr:commune')
                            .valid_at(date.today())
                            .first())
                    elif kind == 'county':
                        counter_counties += 1
                        new_zones.append(
                            GeoZone
                            .objects(code=zone_id, level='fr:departement')
                            .valid_at(date.today())
                            .first())
                    elif kind == 'region':
                        counter_regions += 1
                        # Only link to pre-2016 regions which kept the same id.
                        new_zones.append(
                            GeoZone
                            .objects(code=zone_id, level='fr:region')
                            .first())
                    else:
                        new_zones.append(zone)
                elif zone.id.startswith('country-subset/fr'):
                    counter_zones += 1
                    subset, country, kind = zone.id.split('/')
                    if kind == 'dom':
                        counter_drom += 1
                        new_zones.append(drom_zone)
                    elif kind == 'domtom':
                        counter_dromcom += 1
                        new_zones.append(dromcom_zone)
                elif zone.id.startswith('country/fr'):
                    counter_zones += 1
                    counter_france += 1
                    new_zones.append(france_zone)
                else:
                    new_zones.append(zone)
            dataset.update(
                spatial=SpatialCoverage(zones=[z.id for z in new_zones if z]))
    print('{} datasets and {} zones affected.'.format(
        counter_datasets, counter_zones))
    print('{} town zones, {} county zones and {} region zones updated.'.format(
        counter_towns, counter_counties, counter_regions))
    print('{} France zones, {} DROM zones, {} DROM-COM zones updated.'.format(
        counter_france, counter_drom, counter_dromcom))
    log.info('Done')
