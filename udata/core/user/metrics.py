from udata.models import Dataset, Reuse


@Dataset.on_create.connect
@Dataset.on_update.connect
@Dataset.on_delete.connect
def update_datasets_metrics(document, **kwargs):
    print("----------------------------------------------------------------------")
    print("IN DATASET FOR USER METRIC UPDATE")
    print(document)
    if document.owner:
        document.owner.count_datasets()
        print(document.owner.get_metrics)
    print("----------------------------------------------------------------------")


@Reuse.on_create.connect
@Reuse.on_update.connect
@Reuse.on_delete.connect
def update_reuses_metrics(document, **kwargs):
    if document.owner:
        document.owner.count_reuses()


# @db.Owned.on_owner_change.connect
# def update_downer_metrics(document, previous):
#     if not isinstance(previous, User):
#         return
#     if isinstance(document, Dataset):
#         DatasetsMetric(previous).trigger_update()
#     elif isinstance(document, Reuse):
#         ReusesMetric(previous).trigger_update()


# class UserFollowersMetric(FollowersMetric):
#     model = User


# class UserFollowingMetric(UserMetric):
#     name = 'following'
#     display_name = _('Following')

#     def get_value(self):
#         return Follow.objects.following(self.user).count()


# @on_follow.connect
# @on_unfollow.connect
# def update_user_following_metric(follow):
#     UserFollowingMetric(follow.follower).trigger_update()
