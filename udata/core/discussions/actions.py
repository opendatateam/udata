from udata.models import Dataset, Reuse

from .models import Discussion


def discussions_for(user, only_open=True):
    """
    Build a queryset to query discussions related to a given user's assets.

    It includes discussions coming from the user's organizations

    :param bool only_open: whether to include closed discussions or not.
    """
    # Only fetch required fields for discussion filtering (id and slug)
    # Greatly improve performances and memory usage
    datasets = Dataset.objects.owned_by(user.id, *user.organizations).only("id", "slug")
    reuses = Reuse.objects.owned_by(user.id, *user.organizations).only("id", "slug")

    qs = Discussion.objects(subject__in=list(datasets) + list(reuses))
    if only_open:
        qs = qs(closed__exists=False)
    return qs
