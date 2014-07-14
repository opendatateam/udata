# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from flask.ext.script import Command

from udata.commands import manager
from udata.search import es, adapter_catalog

log = logging.getLogger(__name__)


class Reindex(Command):
    '''Reindex all models'''

    def run(self):
        print('Deleting index {0}'.format(es.index_name))
        if es.indices.exists(es.index_name):
            es.indices.delete(index=es.index_name)
        es.initialize()
        for model, adapter in adapter_catalog.items():
            print 'Reindexing {0} objects'.format(model.__name__)
            qs = model.objects.visible() if hasattr(model.objects, 'visible') else model.objects
            for obj in qs:
                es.index(index=es.index_name, doc_type=adapter.doc_type(), id=obj.id, body=adapter.serialize(obj))
        es.indices.refresh(index=es.index_name)


manager.add_command('reindex', Reindex())
