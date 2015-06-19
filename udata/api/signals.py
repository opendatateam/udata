# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from blinker import Namespace

namespace = Namespace()

#: Trigerred when an HTTP request is issued against the API
on_api_call = namespace.signal('on-api-call')
