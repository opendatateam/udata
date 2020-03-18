from .signals import (
    on_new_discussion, on_discussion_closed, on_discussion_deleted
)


@on_new_discussion.connect
@on_discussion_closed.connect
@on_discussion_deleted.connect
def update_discussions_metric(discussion, **kwargs):
    model = discussion.subject.__class__
    obj = model.objects(id=discussion.subject.id).first()
    obj.count_discussions()
