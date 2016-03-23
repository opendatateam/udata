# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from udata.commands import manager
from udata.models import GeoZone, Organization

log = logging.getLogger(__name__)


@manager.command
def attach_zone(insee_code, organization_id_or_slug, level='fr/town'):
    '''Attach a zone restricted to level for a given organization.'''
    organization = Organization.objects.get_by_id_or_slug(
        organization_id_or_slug)
    geozone = GeoZone.objects(code=insee_code, level=level).first()
    log.info('Attaching {organization} with {geozone.name}'.format(
             organization=organization, geozone=geozone))
    organization.zone = geozone.id
    organization.save()
    log.info('Done')
