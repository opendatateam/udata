from .signals import on_follow, on_unfollow

# __all__ = ('FollowersMetric', )


# class FollowersMetricMetaclass(MetricMetaClass):
#     def __new__(cls, name, bases, attrs):
#         # Ensure any child class compute itself on follow/unfollow
#         new_class = super(FollowersMetricMetaclass, cls).__new__(
#             cls, name, bases, attrs)
#         if new_class.model:
#             def callback(follow):
#                 if isinstance(follow.following, new_class.model):
#                     new_class(follow.following).trigger_update()
#             on_follow.connect(callback, weak=False)
#             on_unfollow.connect(callback, weak=False)
#         return new_class


# class FollowersMetric(Metric, metaclass=FollowersMetricMetaclass):
#     name = 'followers'
#     display_name = _('Followers')

#     def get_value(self):
#         return Follow.objects.followers(self.target).count()


@on_follow.connect
@on_unfollow.connect
def update_followers_metric(document, **kwargs):
    print("----------------------------------------------------------------------")
    print("IN FOLLOWERS METRIC UPDATE")
    print(document)
    print(document.following)
    print(document.following.id)
    print("#########################################")
    doc = document.following
    doc.count_followers()
    print(doc.get_metrics)
    print("----------------------------------------------------------------------")