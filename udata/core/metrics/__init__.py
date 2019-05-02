# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata import entrypoints

from . import registry
from .specs import Metric, MetricMetaClass

__all__ = ('Metric', 'MetricMetaClass', 'registry')


def init_app(app):
    # Load all core metrics
    import udata.core.site.metrics  # noqa
    import udata.core.user.metrics  # noqa
    import udata.core.issues.metrics  # noqa
    import udata.core.discussions.metrics  # noqa
    import udata.core.dataset.metrics  # noqa
    import udata.core.reuse.metrics  # noqa
    import udata.core.organization.metrics  # noqa
    import udata.core.followers.metrics  # noqa

    # Load metrics from plugins
    entrypoints.get_enabled('udata.metrics', app)
