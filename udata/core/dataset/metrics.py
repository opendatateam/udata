from udata.core.metrics import Metric
from udata.i18n import lazy_gettext as _
from udata.models import Dataset, Reuse

from udata.core.issues.metrics import IssuesMetric
from udata.core.discussions.metrics import DiscussionsMetric
from udata.core.followers.metrics import FollowersMetric


@Reuse.on_create.connect
def update_dataset_reuses_metric(reuse, **kwargs):
    for dataset in reuse.datasets:
        dataset.reuses_count()
        dataset.save()


# class DatasetIssuesMetric(IssuesMetric):
#     model = Dataset


# class DatasetDiscussionsMetric(DiscussionsMetric):
#     model = Dataset


# class DatasetFollowers(FollowersMetric):
#     model = Dataset
