COMMENT_SIZE_LIMIT = 50000

# Models a discussion can be opened on, used as `choices` of `Discussion.subject`.
# Each one is `Linkable` (the discussion web URL is built from its subject page)
# and implements `count_discussions()` (called when a discussion is created,
# closed or deleted). A model missing the former breaks every listing of the
# discussions, one missing the latter breaks those three signals.
# Class names rather than classes (unlike `REPORTABLE_MODELS`): `discussions.models`
# imports this module and `user.models` already imports `discussions.models`, so
# importing the models here would be circular.
DISCUSSION_SUBJECTS = ("Dataset", "Reuse", "Post", "Dataservice", "Topic")
