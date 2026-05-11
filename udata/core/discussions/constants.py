from udata.core.dataservices.models import Dataservice
from udata.core.dataset.models import Dataset
from udata.core.post.models import Post
from udata.core.reuse.models import Reuse
from udata.core.topic.models import Topic

COMMENT_SIZE_LIMIT = 50000

NOTIFY_DISCUSSION_SUBJECTS = (Dataset, Reuse, Post, Dataservice, Topic)

# Subjects with no canonical detail page on the udata frontend. For these,
# notifications are only sent when `extras.notification.external_url` is
# provided (e.g. a Topic shown on a third-party platform like Ecosphères).
NOTIFY_REQUIRES_EXTERNAL_URL = (Topic,)
