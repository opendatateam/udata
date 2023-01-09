import logging
import requests
import udata.event  # noqa
# Import udata event in order for datasets event hooks to be executed

from flask import current_app
from mongoengine.signals import post_save, post_delete

from udata.models import db
from udata.tasks import task, as_task_param

log = logging.getLogger(__name__)

adapter_catalog = {}


@task(route='high.search')
def reindex(classname, id):
    model = db.resolve_model(classname)
    obj = model.objects.get(pk=id)
    adapter_class = adapter_catalog.get(model)
    document = adapter_class.serialize(obj)
    if adapter_class.is_indexable(obj):
        log.info('Indexing %s (%s)', model.__name__, obj.id)
        url = f"{current_app.config['SEARCH_SERVICE_API_URL']}{adapter_class.search_url}/index"
        try:
            payload = {
                'document': document
            }
            r = requests.post(url, json=payload)
            r.raise_for_status()
        except Exception:
            log.exception('Unable to index/unindex %s "%s"', model.__name__, str(obj.id))
    else:
        log.info('Unindexing %s (%s)', model.__name__, obj.id)
        url = f"{current_app.config['SEARCH_SERVICE_API_URL']}{adapter_class.search_url}/{str(obj.id)}/unindex"
        try:
            r = requests.delete(url)
            if r.status_code == 404:
                # Unindexed already, we don't want to raise
                return
            r.raise_for_status()
        except Exception:
            log.exception('Unable to index/unindex %s "%s"', model.__name__, str(obj.id))


@task(route='high.search')
def unindex(classname, id):
    model = db.resolve_model(classname)
    adapter_class = adapter_catalog.get(model)
    log.info('Unindexing %s (%s)', model.__name__, id)
    try:
        url = f"{current_app.config['SEARCH_SERVICE_API_URL']}{adapter_class.search_url}/{str(id)}/unindex"
        r = requests.delete(url)
        if r.status_code == 404:
            # Unindexed already, we don't want to raise
            return
        r.raise_for_status()
    except Exception:
        log.exception('Unable to unindex %s "%s"', model.__name__, id)


def reindex_model_on_save(sender, document, **kwargs):
    '''(Re/Un)Index Mongo document on post_save'''
    if current_app.config.get('AUTO_INDEX') and current_app.config['SEARCH_SERVICE_API_URL']:
        reindex.delay(*as_task_param(document))


def unindex_model_on_delete(sender, document, **kwargs):
    '''Unindex Mongo document on post_delete'''
    if current_app.config.get('AUTO_INDEX') and current_app.config['SEARCH_SERVICE_API_URL']:
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
