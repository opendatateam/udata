# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from blinker import Namespace

namespace = Namespace()

#: Trigerred when a reuse is published
on_reuse_published = namespace.signal('on-reuse-published')
