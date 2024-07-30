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

    for key, field in cls._fields.items():
        info = getattr(field, "__additional_field_info__", None)
        if info is None:
            continue

        searchable = info.get("searchable", False)

        if not searchable:
            continue

        attributes[key] = convert_db_field_to_elasticsearch(field, searchable)

    ElasticSearchModel = type(f"{cls.__name__}ElasticsearchModel", (Document,), attributes)

    def elasticsearch_index():
        pass

    cls.__elasticsearch_model__ = ElasticSearchModel
    cls.__elasticsearch_index__ = elasticsearch_index

    signals.post_save.connect(cls.__elasticsearch_index__, sender=cls)


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


# def ensure_index_exists(cls: type) -> None:
#     now = datetime.utcnow().strftime("%Y-%m-%d-%H-%M")
#     index_name_with_suffix = f"{alias}-{now}"
#     pattern = f"{alias}-*"

#     pass
