import bson
import datetime
import logging

from elasticsearch_dsl.serializer import AttrJSONSerializer
from speaklater import is_lazy_string


from . import analysis

log = logging.getLogger(__name__)

adapter_catalog = {}


class EsJSONSerializer(AttrJSONSerializer):
    # TODO: find a way to reuse UDataJsonEncoder?
    def default(self, data):
        if is_lazy_string(data):
            return str(data)
        elif isinstance(data, bson.objectid.ObjectId):
            return str(data)
        elif isinstance(data, datetime.datetime):
            return data.isoformat()
        elif hasattr(data, 'serialize'):
            return data.serialize()
        # Serialize Raw data for Document and EmbeddedDocument.
        elif hasattr(data, '_data'):
            return data._data
        else:
            return super(EsJSONSerializer, self).default(data)


# def reindex_model_on_save(sender, document, **kwargs):
#     '''(Re/Un)Index Mongo document on post_save'''
#     if current_app.config.get('AUTO_INDEX'):
#         reindex.delay(*as_task_param(document))
#
#
# def unindex_model_on_delete(sender, document, **kwargs):
#     '''Unindex Mongo document on post_delete'''
#     if current_app.config.get('AUTO_INDEX'):
#         unindex.delay(*as_task_param(document))


def register(adapter):
    '''Register a search adapter'''
    # register the class in the catalog
    if adapter.model and adapter.model not in adapter_catalog:
        adapter_catalog[adapter.model] = adapter
        # Automatically (re|un)index objects on save/delete
        # post_save.connect(reindex_model_on_save, sender=adapter.model)
        # post_delete.connect(unindex_model_on_delete, sender=adapter.model)
    return adapter


from .adapter import ModelSearchAdapter  # noqa
from .result import SearchResult  # noqa
from .fields import *  # noqa


def adapter_for(model_or_adapter):
    if issubclass(model_or_adapter, ModelSearchAdapter):
        return model_or_adapter
    else:
        return adapter_catalog[model_or_adapter]


def search_for(model_or_adapter, params):
    adapter = adapter_for(model_or_adapter)
    search_class = adapter.temp_search()
    return search_class(params)


def query(model, **params):
    search = search_for(model, params)
    return search.exsearch()


def init_app(app):
    # Register core adapters
    import udata.core.dataset.search  # noqa
    import udata.core.reuse.search  # noqa
    import udata.core.organization.search  # noqa
    import udata.core.spatial.search  # noqa
