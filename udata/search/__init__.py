import logging

from flask import current_app
from mongoengine.signals import post_delete, post_save

from udata.mongo import db
from udata.tasks import as_task_param, task

log = logging.getLogger(__name__)

adapter_catalog = {}

_elastic_client = None


def get_elastic_client():
    global _elastic_client
    if _elastic_client is None:
        from udata_search_service.search_clients import ElasticClient

        _elastic_client = ElasticClient(
            current_app.config["ELASTICSEARCH_URL"],
            current_app.config["UDATA_INSTANCE_NAME"],
        )
    return _elastic_client


@task(route="high.search")
def reindex(classname, id):
    if not current_app.config["ELASTICSEARCH_URL"]:
        return
    model = db.resolve_model(classname)
    obj = model.objects.get(pk=id)
    adapter_class = adapter_catalog.get(model)
    document = adapter_class.serialize(obj)
    if adapter_class.is_indexable(obj):
        log.info("Indexing %s (%s)", model.__name__, obj.id)
        try:
            entity = adapter_class.consumer_class.load_from_dict(document)
            service = adapter_class.service_class(get_elastic_client())
            service.feed(entity)
        except Exception:
            log.exception('Unable to index %s "%s"', model.__name__, str(obj.id))
    else:
        log.info("Unindexing %s (%s)", model.__name__, obj.id)
        try:
            service = adapter_class.service_class(get_elastic_client())
            service.delete_one(str(obj.id))
        except Exception:
            log.exception('Unable to unindex %s "%s"', model.__name__, str(obj.id))


@task(route="high.search")
def unindex(classname, id):
    if not current_app.config["ELASTICSEARCH_URL"]:
        return
    model = db.resolve_model(classname)
    adapter_class = adapter_catalog.get(model)
    log.info("Unindexing %s (%s)", model.__name__, id)
    try:
        service = adapter_class.service_class(get_elastic_client())
        service.delete_one(str(id))
    except Exception:
        log.exception('Unable to unindex %s "%s"', model.__name__, id)


# Placed after reindex/unindex definitions to avoid circular import:
# udata.search → udata.event → udata.models → udata.core.topic.models → udata.search.reindex
import udata.event  # noqa: E402, F401


def reindex_model_on_save(sender, document, **kwargs):
    """(Re/Un)Index Mongo document on post_save"""
    if current_app.config.get("AUTO_INDEX") and current_app.config["ELASTICSEARCH_URL"]:
        reindex.delay(*as_task_param(document))


def unindex_model_on_delete(sender, document, **kwargs):
    """Unindex Mongo document on post_delete"""
    if current_app.config.get("AUTO_INDEX") and current_app.config["ELASTICSEARCH_URL"]:
        unindex.delay(*as_task_param(document))


def register(adapter):
    """Register a search adapter"""
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
    import udata.core.topic.search  # noqa
    import udata.core.discussions.search  # noqa
    import udata.core.post.search  # noqa
