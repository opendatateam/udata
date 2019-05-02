# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask.signals import Namespace

ns = Namespace()

#: Sent when a metric needs to be updated
metric_need_update = ns.signal('metric:need-update')

#: Sent when a metric has been updated
metric_updated = ns.signal('metric:updated')
