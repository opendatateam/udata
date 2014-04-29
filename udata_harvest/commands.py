# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from os.path import exists

from udata.commands import manager

from .models import Harvester
from .backends import get_backend_for


@manager.option('name', help='Ini file name or harvester name')
@manager.option('-o', '--organizations', action='store_true', default=False, help='Harvest organizations')
@manager.option('-d', '--datasets', action='store_true', default=False, help='Harvest datasets')
@manager.option('-r', '--reuses', action='store_true', default=False, help='Harvest reuses')
@manager.option('-u', '--users', action='store_true', default=False, help='Harvest users')
def harvest(name, organizations=False, users=False, datasets=False, reuses=False):
    '''Launch harvesters'''
    if exists(name):
        harvester = Harvester.from_file(name)
    else:
        harvester = Harvester.objects.get(name=name)

    backend = get_backend_for(harvester)
    backend.harvest(organizations=organizations, datasets=datasets, reuses=reuses, users=users)
