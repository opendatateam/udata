from datetime import datetime
from flask import current_app
import logging
import sys

import click
from udata_event_service.producer import produce

from udata.commands import cli
from udata.event.producer import get_topic
from udata.search import adapter_catalog, KafkaMessageType


log = logging.getLogger(__name__)


@cli.group('search')
def grp():
    '''Search/Indexation related operations'''
    pass


TIMESTAMP_FORMAT = '%Y-%m-%d-%H-%M'


def default_index_suffix_name(now):
    '''Build a time based index suffix name'''
    return now.strftime(TIMESTAMP_FORMAT)


def iter_adapters():
    '''Iter over adapter in predictable way'''
    adapters = adapter_catalog.values()
    return sorted(adapters, key=lambda a: a.model.__name__)


def iter_qs(qs, adapter):
    '''Safely iterate over a DB QuerySet yielding a tuple (indexability, serialized documents)'''
    for obj in qs.no_cache().timeout(False):
        indexable = adapter.is_indexable(obj)
        try:
            doc = adapter.serialize(obj)
            yield indexable, doc
        except Exception as e:
            model = adapter.model.__name__
            log.error('Unable to index %s "%s": %s', model, str(obj.id),
                      str(e), exc_info=True)


def index_model(adapter, start, reindex=False, from_datetime=None):
    '''Index or unindex all objects given a model'''
    model = adapter.model
    log.info('Indexing %s objects', model.__name__)
    qs = model.objects
    if from_datetime:
        qs = qs.filter(last_modified__gte=from_datetime)
    index_name = adapter.model.__name__.lower()
    if reindex:
        index_name += '-' + default_index_suffix_name(start)

    docs = iter_qs(qs, adapter)
    for indexable, doc in docs:
        try:
            if indexable:
                action = KafkaMessageType.REINDEX if reindex else KafkaMessageType.INDEX
            elif not indexable and not reindex:
                action = KafkaMessageType.UNINDEX
            else:
                continue
            message_type = f'{adapter.model.__name__.lower()}.{action.value}'
            produce(
                kafka_uri=current_app.config.get('KAFKA_URI'),
                topic=get_topic(message_type),
                service='udata',
                key_id=doc['id'],
                document=doc,
                meta={'message_type': message_type, 'index': index_name}
            )
        except Exception as e:
            log.error('Unable to index %s "%s": %s', model, str(doc['id']),
                      str(e), exc_info=True)


def finalize_reindex(models, start):
    models_str = " " + " ".join(models) if models else ""
    log.warning(
        f'In order to use the newly created index, you should set the alias '
        f'on the search service. Ex on `udata-search-service`, run:\n'
        f'`udata-search-service set-alias {default_index_suffix_name(start)}{models_str}`'
    )

    modified_since_reindex = 0
    for adapter in iter_adapters():
        if not models or adapter.model.__name__.lower() in models:
            modified_since_reindex += adapter.model.objects(last_modified__gte=start).count()

    log.warning(
        f'{modified_since_reindex} documents have been modified since reindexation start. '
        f'After having set the appropriate alias, you can index last changes since the '
        f'beginning of the indexation. Example, you can run:\n'
        f'`udata search index -f {default_index_suffix_name(start)}`'
    )


@grp.command()
@click.argument('models', nargs=-1, metavar='[<model> ...]')
@click.option('-r', '--reindex', default=False, type=bool)
@click.option('-f', '--from_datetime', type=str)
def index(models=None, reindex=True, from_datetime=None):
    '''
    Initialize or rebuild the search index

    Models to reindex can optionally be specified as arguments.
    If not, all models are reindexed.

    If reindex is true, indexation will be made on a new index and unindexable documents ignored.

    If from_datetime is specified, only models modified since this datetime will be indexed.
    '''

    start = datetime.now()
    if from_datetime:
        from_datetime = datetime.strptime(from_datetime, TIMESTAMP_FORMAT)

    doc_types_names = [m.__name__.lower() for m in adapter_catalog.keys()]
    models = [model.lower().rstrip('s') for model in (models or [])]
    for model in models:
        if model not in doc_types_names:
            log.error('Unknown model %s', model)
            sys.exit(-1)

    for adapter in iter_adapters():
        if not models or adapter.model.__name__.lower() in models:
            index_model(adapter, start, reindex, from_datetime)

    if reindex:
        finalize_reindex(models, start)
