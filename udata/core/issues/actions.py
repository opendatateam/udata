from udata.models import Reuse, Dataset

from .models import Issue


def issues_for(user, only_open=True):
    '''
    Build a queryset to query issues for a given user's assets.

    It includes issues coming from the user's organizations

    :param bool only_open: whether to include closed issues or not.
    '''
    # Only fetch required fields for issues filtering (id and slug)
    # Greatly improve performances and memory usage
    datasets = Dataset.objects.owned_by(user.id, *user.organizations).only('id', 'slug')
    reuses = Reuse.objects.owned_by(user.id, *user.organizations).only('id', 'slug')

    qs = Issue.objects(subject__in=list(datasets) + list(reuses))
    if only_open:
        qs = qs(closed__exists=False)
    return qs
