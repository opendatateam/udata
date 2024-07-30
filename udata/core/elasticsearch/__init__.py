import logging
import random
import string
from datetime import datetime

import mongoengine.fields as mongo_fields
from elasticsearch import Elasticsearch
from elasticsearch_dsl import (
    Boolean,
    Date,
    Document,
    Field,
    Float,
    Index,
    Integer,
    Keyword,
    Nested,
    Search,
    Text,
    analyzer,
    connections,
    token_filter,
    tokenizer,
)
from mongoengine import Document as MongoDocument
from mongoengine import signals

log = logging.getLogger(__name__)

french_elision = token_filter(
    "french_elision",
    type="elision",
    articles_case=True,
    articles=[
        "l",
        "m",
        "t",
        "qu",
        "n",
        "s",
        "j",
        "d",
        "c",
        "jusqu",
        "quoiqu",
        "lorsqu",
        "puisqu",
    ],
)
SEARCH_SYNONYMS = [
    "AMD, administrateur ministériel des données, AMDAC",
    "lolf, loi de finance",
    "waldec, RNA, répertoire national des associations",
    "ovq, baromètre des résultats",
    "contour, découpage",
    "rp, recensement de la population",
]
french_stop = token_filter("french_stop", type="stop", stopwords="_french_")
french_stemmer = token_filter("french_stemmer", type="stemmer", language="light_french")
french_synonym = token_filter(
    "french_synonym",
    type="synonym",
    ignore_case=True,
    expand=True,
    synonyms=SEARCH_SYNONYMS,
)

dgv_analyzer = analyzer(
    "french_dgv",
    tokenizer=tokenizer("standard"),
    filter=[french_elision, french_synonym, french_stemmer, french_stop],
)

client = connections.create_connection(hosts=["localhost"])


def elasticsearch(**kwargs):
    def wrapper(cls):
        cls.elasticsearch = generate_elasticsearch_model(cls)
        return cls

    return wrapper


def generate_elasticsearch_model(cls: type) -> type:
    index_name = cls._get_collection_name()
    index_name = "".join(random.choices(string.ascii_lowercase, k=10))

    class Index:
        name = index_name

    attributes = {"Index": Index}

    for key, field, searchable in get_searchable_fields(cls):
        attributes[key] = convert_db_field_to_elasticsearch(field, searchable)

    ElasticSearchModel = type(f"{cls.__name__}ElasticsearchModel", (Document,), attributes)

    ensure_index_exists(ElasticSearchModel._index, index_name)

    def elasticsearch_index(cls, document, **kwargs):
        print("calling it!")
        print(document.id)
        print(document.title)
        convert_mongo_document_to_elasticsearch_document(document).save()

    def elasticsearch_search(query_text):
        s = Search(using=client, index=index_name).query("match", title=query_text)
        response = s.execute()
        print(response)

        # Get all the models from MongoDB to fetch all the correct fields.
        models = {
            str(model.id): model for model in cls.objects(id__in=[hit.id for hit in response])
        }

        # Map these object to the response array in order to preserve the sort order
        # returned by Elasticsearch
        return [models[hit.id] for hit in response]

    cls.__elasticsearch_model__ = ElasticSearchModel
    cls.__elasticsearch_index__ = elasticsearch_index
    cls.__elasticsearch_search__ = elasticsearch_search

    signals.post_save.connect(cls.__elasticsearch_index__, sender=cls)


def get_searchable_fields(cls):
    for key, field in cls._fields.items():
        info = getattr(field, "__additional_field_info__", None)
        if info is None:
            continue

        searchable = info.get("searchable", False)

        if not searchable:
            continue

        yield key, field, searchable


def convert_db_field_to_elasticsearch(field, searchable: bool | str) -> Field:
    if isinstance(searchable, str):
        return {
            "keyword": Keyword(),
        }[searchable]
    elif isinstance(field, mongo_fields.StringField):
        return Text(analyzer=dgv_analyzer)
    elif isinstance(field, mongo_fields.FloatField):
        return Float()
    elif isinstance(field, mongo_fields.BooleanField):
        return Boolean()
    elif isinstance(field, mongo_fields.DateTimeField):
        return Date()
    elif isinstance(field, mongo_fields.ReferenceField):
        return Nested(field.document_type_obj.__elasticsearch_model__)
    else:
        raise ValueError(f"Unsupported MongoEngine field type {field.__class__.__name__}")


def convert_mongo_document_to_elasticsearch_document(document: MongoDocument) -> Document:
    attributes = {}
    attributes["id"] = str(document.id)

    for key, field, searchable in get_searchable_fields(document.__class__):
        attributes[key] = getattr(document, key)

    return document.__elasticsearch_model__(**attributes)


def ensure_index_exists(index: Index, index_name: str) -> None:
    now = datetime.utcnow().strftime("%Y-%m-%d-%H-%M")
    index_name_with_suffix = f"{index_name}-{now}"
    pattern = f"{index_name}-*"

    print("exporting template")
    index_template = index.as_template(index_name, pattern)
    index_template.save()

    print("creating index")
    client.indices.create(index=index_name_with_suffix)
    print("creating alias")
    client.indices.put_alias(index=index_name_with_suffix, name=index_name)
    print("done")
