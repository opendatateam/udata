# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.core.metrics import Metric
from udata.core.site.metrics import SiteMetric
from udata.i18n import lazy_gettext as _

from .models import Discussion
from .signals import (
    on_new_discussion, on_discussion_closed, on_discussion_deleted
)


class DiscussionsMetric(Metric):
    name = 'discussions'
    display_name = _('Discussions')

    def get_value(self):
        return Discussion.objects(subject=self.target, closed=None).count()


class DiscussionsSiteMetric(SiteMetric):
    name = 'discussions'
    display_name = _('Discussions')

    def get_value(self):
        return Discussion.objects.count()

DiscussionsSiteMetric.connect(on_new_discussion)


@on_new_discussion.connect
@on_discussion_closed.connect
@on_discussion_deleted.connect
def update_discussions_metric(discussion, **kwargs):
    model = discussion.subject.__class__
    for name, cls in Metric.get_for(model).items():
        if issubclass(cls, DiscussionsMetric):
            cls(target=discussion.subject).trigger_update()
