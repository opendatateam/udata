import logging
import sys
from datetime import datetime

import click
from flask import current_app

from udata.commands import cli
from udata.search import adapter_catalog, get_elastic_client

log = logging.getLogger(__name__)


@cli.group("search")
def grp():
    """Search/Indexation related operations"""
    pass


TIMESTAMP_FORMAT = "%Y-%m-%d-%H-%M"


def default_index_suffix_name(now):
    """Build a time based index suffix name"""
    return now.strftime(TIMESTAMP_FORMAT)


def iter_adapters():
    """Iter over adapter in predictable way"""
    adapters = adapter_catalog.values()
    return sorted(adapters, key=lambda a: a.model.__name__)


def get_date_property(model_name: str) -> str:
    """Get the date property used for filtering modified objects by model name."""
    date_properties = {
        "dataset": "last_modified_internal",
        "discussion": "created",
        "dataservice": "metadata_modified_at",
    }
    return date_properties.get(model_name, "last_modified")


def iter_qs(qs, adapter):
    """Safely iterate over a DB QuerySet yielding a tuple (indexability, serialized documents)"""
    for obj in qs.no_cache().timeout(False):
        indexable = adapter.is_indexable(obj)
        try:
            doc = adapter.serialize(obj)
            yield indexable, doc
        except Exception as e:
            model = adapter.model.__name__
            log.error('Unable to index %s "%s": %s', model, str(obj.id), str(e), exc_info=True)


def index_model(adapter, start, reindex=False, from_datetime=None):
    """Index or unindex all objects given a model"""
    model = adapter.model
    log.info("Indexing %s objects", model.__name__)
    model_name = adapter.model.__name__.lower()
    qs = model.objects
    if from_datetime:
        date_property = get_date_property(model_name)
        qs = qs.filter(**{f"{date_property}__gte": from_datetime})

    es_client = get_elastic_client()
    service = adapter.service_class(es_client)

    index_name = None
    if reindex:
        suffix = default_index_suffix_name(start)
        alias = f"{current_app.config['ELASTICSEARCH_INDEX_BASENAME']}-{model_name}"
        index_name = f"{alias}-{suffix}"
        es_client.es.indices.create(index=index_name)

    count = qs.count()
    label = f"Indexing {model.__name__}"
    with click.progressbar(iter_qs(qs, adapter), length=count, label=label) as docs:
        for indexable, doc in docs:
            try:
                if indexable:
                    entity = adapter.consumer_class.load_from_dict(doc)
                    service.feed(entity, index=index_name)
                elif not reindex:
                    service.delete_one(doc["id"])
            except Exception as e:
                log.error(
                    'Unable to index %s "%s": %s', model, str(doc["id"]), str(e), exc_info=True
                )


def finalize_reindex(models, start):
    try:
        es = get_elastic_client().es
        suffix = default_index_suffix_name(start)
        instance = current_app.config["ELASTICSEARCH_INDEX_BASENAME"]

        for adapter in iter_adapters():
            model_name = adapter.model.__name__.lower()
            if models and model_name not in models:
                continue
            alias = f"{instance}-{model_name}"
            new_index = f"{alias}-{suffix}"

            actions = []
            try:
                current_indices = list(es.indices.get_alias(name=alias).keys())
                for old_index in current_indices:
                    actions.append({"remove": {"index": old_index, "alias": alias}})
            except Exception:
                pass
            actions.append({"add": {"index": new_index, "alias": alias}})
            es.indices.update_aliases(body={"actions": actions})
    except Exception:
        log.exception("Unable to set alias for index")

    modified_since_reindex = 0
    for adapter in iter_adapters():
        if not models or adapter.model.__name__.lower() in models:
            model_name = adapter.model.__name__.lower()
            date_property = get_date_property(model_name)
            modified_since_reindex += adapter.model.objects(
                **{f"{date_property}__gte": start}
            ).count()

    log.warning(
        f"{modified_since_reindex} documents have been modified since reindexation start. "
        f"After having set the appropriate alias, you can index last changes since the "
        f"beginning of the indexation. Example, you can run:\n"
        f"`udata search index -f {default_index_suffix_name(start)}`"
    )


@grp.command("init-es")
def init_es():
    """Create Elasticsearch index templates and indices."""
    if not current_app.config["ELASTICSEARCH_URL"]:
        log.error("Missing ELASTICSEARCH_URL configuration")
        sys.exit(-1)

    es_client = get_elastic_client()
    es_client.init_indices()
    log.info("Elasticsearch indices initialized")


@grp.command()
@click.argument("models", nargs=-1, metavar="[<model> ...]")
@click.option("-r", "--reindex", default=False, type=bool)
@click.option("-f", "--from_datetime", type=str)
def index(models=None, reindex=True, from_datetime=None):
    """
    Initialize or rebuild the search index

    Models to reindex can optionally be specified as arguments.
    If not, all models are reindexed.

    If reindex is true, indexation will be made on a new index and unindexable documents ignored.

    If from_datetime is specified, only models modified since this datetime will be indexed.
    """
    if not current_app.config["ELASTICSEARCH_URL"]:
        log.error("Missing ELASTICSEARCH_URL configuration")
        sys.exit(-1)

    start = datetime.utcnow()
    if from_datetime:
        from_datetime = datetime.strptime(from_datetime, TIMESTAMP_FORMAT)

    doc_types_names = [m.__name__.lower() for m in adapter_catalog.keys()]
    models = [model.lower().rstrip("s") for model in (models or [])]
    for model in models:
        if model not in doc_types_names:
            log.error("Unknown model %s", model)
            sys.exit(-1)

    for adapter in iter_adapters():
        if not models or adapter.model.__name__.lower() in models:
            index_model(adapter, start, reindex, from_datetime)

    if reindex:
        finalize_reindex(models, start)
