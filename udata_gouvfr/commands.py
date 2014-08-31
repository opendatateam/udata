# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from os.path import exists

from udata.commands import manager
from udata.models import Organization

from .tasks import geocode_territorial_coverage


def certify_org(id_or_slug):
    organization = Organization.objects(slug=id_or_slug).first()
    if not organization:
        try:
            organization = Organization.objects(id=id_or_slug).first()
        except:
            print 'No organization found for {0}'.format(id_or_slug)
            return
    print 'Certifying {0}'.format(organization.name)
    organization.public_service = True
    organization.save()


@manager.command
def certify(path_or_id):
    '''Certify an organization as a public service'''
    if exists(path_or_id):
        with open(path_or_id) as open_file:
            for id_or_slug in open_file.readlines():
                certify_org(id_or_slug.strip())
    else:
        certify_org(path_or_id)


@manager.command
def comarquage_to_geo():
    geocode_territorial_coverage()
