from factory.fuzzy import FuzzyChoice

from udata.factories import ModelFactory

from .models import get_badge


def badge_factory(model_):
    class BadgeFactory(ModelFactory):
        class Meta:
            model = get_badge(model_.__badges__)

        kind = FuzzyChoice(model_.__badges__)

    return BadgeFactory
