from factory.fuzzy import FuzzyChoice

from udata.factories import ModelFactory


def badge_factory(model_):
    class BadgeFactory(ModelFactory):
        class Meta:
            model = model_._fields["badges"].field.document_type

        kind = FuzzyChoice(model_.__badges__)

    return BadgeFactory
