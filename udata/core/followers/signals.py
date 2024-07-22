from blinker import Namespace

namespace = Namespace()

#: Trigerred when an user follow someone or something
on_follow = namespace.signal("on-follow")

#: Trigerred when an user follow someone or something (again)
# We cannot reuse the `on_follow` one because we need to trigger it
# from the view to pass user information for tracking
# (vs `db.post_save.connect` signal).
on_new_follow = namespace.signal("on-new-follow")

#: Trigerred when an user unfollow someone or something
on_unfollow = namespace.signal("on-unfollow")
