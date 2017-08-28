# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import contextlib
import logging
import lzma
import os
import shutil
import tarfile

from collections import Counter
from datetime import date
from string import Formatter
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
    counter = Counter()
    drom_zone = GeoZone.objects(id='country-subset:fr:drom').first()
    dromcom_zone = GeoZone.objects(id='country-subset:fr:dromcom').first()
    # Iter over datasets with zones
    for dataset in Dataset.objects(spatial__zones__gt=[]):
        counter['datasets'] += 1
        new_zones = []
        for zone in dataset.spatial.zones:
            if zone.id.startswith('fr/'):
                counter['zones'] += 1
                country, kind, zone_id = zone.id.split('/')
                zone_id = zone_id.upper()  # Corsica 2a/b case.
                if kind == 'town':
                    counter['towns'] += 1
                    new_zones.append(
                        GeoZone
                        .objects(code=zone_id, level='fr:commune')
                        .valid_at(date.today())
                        .first())
                elif kind == 'county':
                    counter['counties'] += 1
                    new_zones.append(
                        GeoZone
                        .objects(code=zone_id, level='fr:departement')
                        .valid_at(date.today())
                        .first())
                elif kind == 'region':
                    counter['regions'] += 1
                    # Only link to pre-2016 regions which kept the same id.
                    new_zones.append(
                        GeoZone
                        .objects(code=zone_id, level='fr:region')
                        .first())
                elif kind == 'epci':
                    counter['epcis'] += 1
                    new_zones.append(
                        GeoZone
                        .objects(code=zone_id, level='fr:epci')
                        .valid_at(dataset.created_at.date())
                        .first())
                else:
                    new_zones.append(zone)
            elif zone.id.startswith('country-subset/fr'):
                counter['zones'] += 1
                subset, country, kind = zone.id.split('/')
                if kind == 'dom':
                    counter['drom'] += 1
                    new_zones.append(drom_zone)
                elif kind == 'domtom':
                    counter['dromcom'] += 1
                    new_zones.append(dromcom_zone)
            elif zone.id.startswith('country/'):
                counter['zones'] += 1
                counter['countries'] += 1
                new_zones.append(zone.id.replace('/', ':'))
            elif zone.id.startswith('country-group/'):
                counter['zones'] += 1
                counter['countrygroups'] += 1
                new_zones.append(zone.id.replace('/', ':'))
            else:
                new_zones.append(zone)
        dataset.update(
            spatial=SpatialCoverage(
                granularity=dataset.spatial.granularity,
                zones=[getattr(z, 'id', z) for z in new_zones if z]
            )
        )
    log.info(Formatter().vformat('''Summary
    Processed {zones} zones in {datasets} datasets:
    - {countrygroups} country groups (World/UE)
    - {countries} countries
    - France:
        - {regions} regions
        - {counties} counties
        - {epcis} EPCIs
        - {towns} towns
        - {drom} DROM
        - {dromcom} DROM-COM
    ''', (), counter))
    log.info('Done')
