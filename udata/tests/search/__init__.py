import factory

from factory.mongoengine import MongoEngineFactory

from udata import search
from udata.models import db
from udata.utils import faker


#############################################################################
#                           Fake object for testing                         #
#############################################################################

class FakeSearchable(db.Document):
    title = db.StringField()
    description = db.StringField()
    tags = db.ListField(db.StringField())
    other = db.ListField(db.StringField())
    indexable = db.BooleanField(default=True)

    meta = {'allow_inheritance': True}

    def __unicode__(self):
        return self.title

    def __str__(self):
        return self.title

    def __html__(self):
        return '<span>{0}</span>'.format(self.title)


class FakeFactory(MongoEngineFactory):
    title = factory.Faker('sentence')

    class Meta:
        model = FakeSearchable


@search.register
class FakeSearch(search.ModelSearchAdapter):
    class Meta:
        doc_type = 'FakeSearchable'

    model = FakeSearchable
    facets = {
        'tag': search.TermsFacet(field='tags'),
        'other': search.TermsFacet(field='other'),
    }
    sorts = {
        'title': 'title.raw',
        'description': 'description.raw',
    }

    @classmethod
    def is_indexable(cls, document):
        return document.indexable

    @classmethod
    def serialize(cls, fake):
        return {
            'title': fake.title,
            'description': fake.description,
        }


#############################################################################
#                                  Helpers                                  #
#############################################################################

def hit_factory():
    return {
        "_score": float(faker.random_number(2)),
        "_type": "fakesearchable",
        "_id": faker.md5(),
        "_source": {
            "title": faker.sentence(),
            "tags": [faker.word() for _ in range(faker.random_digit())]
        },
        "_index": "udata-test"
    }


def response_factory(nb=20, total=42, **kwargs):
    '''
    Build a fake Elasticsearch DSL FacetedResponse
    and extract the facet form it
    '''
    hits = sorted(
        (hit_factory() for _ in range(nb)),
        key=lambda h: h['_score']
    )
    max_score = hits[-1]['_score']
    data = {
        "hits": {
            "hits": hits,
            "total": total,
            "max_score": max_score
        },
        "_shards": {
            "successful": 5,
            "failed": 0,
            "total": 5
        },
        "took": 52,
        "timed_out": False
    }
    data.update(kwargs)

    return data
