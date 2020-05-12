from .signals import on_follow, on_unfollow


@on_follow.connect
@on_unfollow.connect
def update_followers_metric(document, **kwargs):
    doc = document.following
    doc.count_followers()
