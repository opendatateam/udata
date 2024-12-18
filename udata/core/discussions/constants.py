from udata.core.dataservices.models import Dataservice
from udata.core.dataset.models import Dataset
from udata.core.post.models import Post
from udata.core.reuse.models import Reuse

COMMENT_SIZE_LIMIT = 50000

NOTIFY_DISCUSSION_SUBJECTS = (Dataset, Reuse, Post, Dataservice)
