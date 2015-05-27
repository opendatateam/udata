# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.core.metrics import Metric
from udata.i18n import lazy_gettext as _

from .models import Issue
from .signals import on_new_issue, on_issue_closed


class IssuesMetric(Metric):
    name = 'issues'
    display_name = _('Issues')

    def get_value(self):
        return Issue.objects(subject=self.target, closed=None).count()


@on_new_issue.connect
@on_issue_closed.connect
def update_issues_metric(issue, **kwargs):
    model = issue.subject.__class__
    for name, cls in Metric.get_for(model).items():
        if issubclass(cls, IssuesMetric):
            cls(target=issue.subject).trigger_update()
