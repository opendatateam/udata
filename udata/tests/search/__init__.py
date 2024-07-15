import factory
from factory.mongoengine import MongoEngineFactory

from udata import search
from udata.mongo import db

#############################################################################
#                           Fake object for testing                         #
#############################################################################


class FakeSearchable(db.Document):
    title = db.StringField()
    description = db.StringField()
    tags = db.ListField(db.StringField())
    other = db.ListField(db.StringField())
    indexable = db.BooleanField(default=True)

    meta = {"allow_inheritance": True}

    def __unicode__(self):
        return self.title

    def __str__(self):
        return self.title

    def __html__(self):
        return "<span>{0}</span>".format(self.title)


class FakeFactory(MongoEngineFactory):
    title = factory.Faker("sentence")

    class Meta:
        model = FakeSearchable


@search.register
class FakeSearch(search.ModelSearchAdapter):
    model = FakeSearchable
    search_url = "mock://test.com/fakeable/"
    filters = {
        "tag": search.Filter(),
        "other": search.Filter(),
    }
    sorts = {
        "title": "title.raw",
        "description": "description.raw",
    }

    @classmethod
    def is_indexable(cls, document):
        return document.indexable

    @classmethod
    def serialize(cls, fake):
        return {
            "title": fake.title,
            "description": fake.description,
        }
