# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from blinker import Namespace

ns = Namespace()

#: Trigerred on new activity/action
new_activity = ns.signal("new-activity")
