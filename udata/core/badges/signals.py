from blinker import Namespace

namespace = Namespace()

#: Trigerred when a badge is added
on_badge_added = namespace.signal('on-badge-added')

#: Trigerred when a badge is removed
on_badge_removed = namespace.signal('on-badge-removed')
