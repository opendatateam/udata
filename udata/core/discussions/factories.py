import factory

from udata.core.dataset.factories import DatasetFactory
from udata.factories import ModelFactory

from .models import Discussion, Message


class DiscussionFactory(ModelFactory):
    class Meta:
        model = Discussion

    title = factory.Faker("sentence")
    # `subject` is required and restricted to `DISCUSSION_SUBJECTS`: a dataset is
    # the most common one, tests only override it when the subject matters.
    subject = factory.SubFactory(DatasetFactory)


class MessageDiscussionFactory(ModelFactory):
    class Meta:
        model = Message

    content = factory.Faker("sentence")
