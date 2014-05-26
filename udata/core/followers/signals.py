# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from blinker import Namespace

namespace = Namespace()

#: Trigerred when an user follow someone or something
on_follow = namespace.signal('on-follow')

#: Trigerred when an user unfollow someone or something
on_unfollow = namespace.signal('on-unfollow')
