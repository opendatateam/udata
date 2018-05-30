from blinker import Namespace

namespace = Namespace()

#: Trigerred when an issue is created
on_new_issue = namespace.signal('on-new-issue')

#: Trigerred when a new comment is posted on an issue
# (excluding creation and closing)
on_new_issue_comment = namespace.signal('on-new-issue-comment')

#: Trigerred when an issue is closed
on_issue_closed = namespace.signal('on-issue-closed')
