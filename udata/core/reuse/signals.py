from blinker import Namespace

namespace = Namespace()

#: Trigerred when a reuse is published
on_reuse_published = namespace.signal("on-reuse-published")
