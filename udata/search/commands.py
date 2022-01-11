import logging
import sys

import click

from udata.commands import cli
from udata.search import adapter_catalog, produce


log = logging.getLogger(__name__)


@cli.group('search')
def grp():
    '''Search/Indexation related operations'''
    pass


def iter_adapters():
    '''Iter over adapter in predictable way'''
    adapters = adapter_catalog.values()
    return sorted(adapters, key=lambda a: a.model.__name__)


def iter_qs(qs, adapter):
    '''Safely iterate over a DB QuerySet yielding ES documents'''
    for obj in qs.no_cache().timeout(False):
        if adapter.is_indexable(obj):
            try:
                doc = adapter.serialize(obj)
                yield doc
            except Exception as e:
                model = adapter.model.__name__
                log.error('Unable to index %s "%s": %s', model, str(obj.id),
                          str(e), exc_info=True)


def index_model(adapter):
    ''' Indel all objects given a model'''
    model = adapter.model
    log.info('Indexing %s objects', model.__name__)
    qs = model.objects
    if hasattr(model.objects, 'visible'):
        qs = qs.visible()
    if adapter.exclude_fields:
        qs = qs.exclude(*adapter.exclude_fields)

    docs = iter_qs(qs, adapter)

    for doc in docs:
        try:
            produce(model, doc)
        except Exception as e:
            log.error('Unable to index %s "%s": %s', model, str(doc.id),
                      str(e), exc_info=True)


@grp.command()
@click.argument('models', nargs=-1, metavar='[<model> ...]')
def index(models=None):
    '''
    Initialize or rebuild the search index

    Models to reindex can optionally be specified as arguments.
    If not, all models are reindexed.
    '''
    doc_types_names = [m.__name__.lower() for m in adapter_catalog.keys()]
    models = [model.lower().rstrip('s') for model in (models or [])]
    for model in models:
        if model not in doc_types_names:
            log.error('Unknown model %s', model)
            sys.exit(-1)

    for adapter in iter_adapters():
        if not models or adapter.doc_type().lower() in models:
            index_model(adapter)
