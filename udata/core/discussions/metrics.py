from .signals import (
    on_new_discussion, on_discussion_closed, on_discussion_deleted
)


# class DiscussionsSiteMetric(SiteMetric):
#     name = 'discussions'
#     display_name = _('Discussions')

#     def get_value(self):
#         return Discussion.objects.count()

# DiscussionsSiteMetric.connect(on_new_discussion)


# @on_new_discussion.connect
# @on_discussion_closed.connect
# @on_discussion_deleted.connect
# def update_discussions_metric(discussion, **kwargs):
#     model = discussion.subject.__class__
#     for name, cls in Metric.get_for(model).items():
#         if issubclass(cls, DiscussionsMetric):
#             cls(target=discussion.subject).trigger_update()


@on_new_discussion.connect
@on_discussion_closed.connect
@on_discussion_deleted.connect
def update_discussions_metric(discussion, **kwargs):
    print("----------------------------------------------------------------------")
    print("IN DISCUSSION METRIC UPDATE")
    print(discussion.subject)
    print("----------------------------------------------------------------------")
    obj = discussion.subject
    obj.discussions_count()
    obj.save()