# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from blinker import Namespace

namespace = Namespace()

#: Trigerred when an discussion is created
on_new_discussion = namespace.signal('on-new-discussion')

#: Trigerred when a new comment is posted on an discussion
# (excluding creation and closing)
on_new_discussion_comment = namespace.signal('on-new-discussion-comment')

#: Trigerred when an discussion is closed
on_discussion_closed = namespace.signal('on-discussion-closed')

#: Trigerred when an discussion is deleted
on_discussion_deleted = namespace.signal('on-discussion-deleted')
