from enum import Enum
import json
import logging

from flask import current_app
from kafka import KafkaProducer
from mongoengine.signals import post_save, post_delete

from udata.models import db, Dataset, Organization, Reuse
from udata.tasks import task, as_task_param


log = logging.getLogger(__name__)

adapter_catalog = {}


class KafkaMessageType(Enum):
    INDEX = 'index'
    REINDEX = 'reindex'
    UNINDEX = 'unindex'


class KafkaProducerSingleton:
    __instance = None

    @staticmethod
    def get_instance() -> KafkaProducer:
        if KafkaProducerSingleton.__instance is None:
            KafkaProducerSingleton.__instance = KafkaProducer(
                bootstrap_servers=current_app.config.get('KAFKA_URI'),
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
        return KafkaProducerSingleton.__instance


def produce(model, id, message_type, document=None, index=None):
    '''Produce message with marshalled document'''
    producer = KafkaProducerSingleton.get_instance()
    key = id.encode("utf-8")
    if model == Dataset:
        topic = 'dataset'
    if model == Organization:
        topic = 'organization'
    if model == Reuse:
        topic = 'reuse'
    if not topic:
        return

    if not index:
        index = topic
    value = {
        'service': 'udata',
        'data': document,
        'meta': {
            'message_type': message_type.value,
            'index': index
        }
    }

    producer.send(topic, value=value, key=key)
    producer.flush()


@task(route='high.search')
def reindex(classname, id):
    model = db.resolve_model(classname)
    obj = model.objects.get(pk=id)
    adapter_class = adapter_catalog.get(model)
    document = adapter_class.serialize(obj)
    if adapter_class.is_indexable(obj):
        log.info('Indexing %s (%s)', model.__name__, obj.id)
        try:
            produce(model, str(obj.id), KafkaMessageType.INDEX, document)
        except Exception:
            log.exception('Unable to index %s "%s"', model.__name__, str(obj.id))
    else:
        log.info('Unindexing %s (%s)', model.__name__, obj.id)
        try:
            produce(model, str(obj.id), KafkaMessageType.UNINDEX, document)
        except Exception:
            log.exception('Unable to desindex %s "%s"', model.__name__, str(obj.id))


@task(route='high.search')
def unindex(classname, id):
    model = db.resolve_model(classname)
    log.info('Unindexing %s (%s)', model.__name__, id)
    try:
        produce(model, id, message=KafkaMessageType.UNINDEX)
    except Exception:
        log.exception('Unable to unindex %s "%s"', model.__name__, id)


def reindex_model_on_save(sender, document, **kwargs):
    '''(Re/Un)Index Mongo document on post_save'''
    if current_app.config.get('AUTO_INDEX'):
        reindex.delay(*as_task_param(document))


def unindex_model_on_delete(sender, document, **kwargs):
    '''Unindex Mongo document on post_delete'''
    if current_app.config.get('AUTO_INDEX'):
        unindex.delay(*as_task_param(document))


def register(adapter):
    '''Register a search adapter'''
    # register the class in the catalog
    if adapter.model and adapter.model not in adapter_catalog:
        adapter_catalog[adapter.model] = adapter
        # Automatically (re|un)index objects on save/delete
        post_save.connect(reindex_model_on_save, sender=adapter.model)
        post_delete.connect(unindex_model_on_delete, sender=adapter.model)
    return adapter


from .adapter import ModelSearchAdapter  # noqa
from .result import SearchResult  # noqa
from .fields import *  # noqa


def adapter_for(model_or_adapter):
    if issubclass(model_or_adapter, ModelSearchAdapter):
        return model_or_adapter
    else:
        return adapter_catalog[model_or_adapter]


def search_for(model_or_adapter, **params):
    adapter = adapter_for(model_or_adapter)
    search_class = adapter.temp_search()
    return search_class(params)


def query(model, **params):
    search = search_for(model, **params)
    return search.execute_search()


def init_app(app):
    # Register core adapters
    import udata.core.dataset.search  # noqa
    import udata.core.reuse.search  # noqa
    import udata.core.organization.search  # noqa