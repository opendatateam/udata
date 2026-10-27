from udata.mongo import *  # noqa

# Load all core models and mixins
from udata.core.spatial.models import *
from udata.core.metrics.models import *
from udata.core.badges.models import *
from udata.core.discussions.models import *
from udata.core.followers.models import *
from udata.core.user.models import *
from udata.core.api_token.models import *
from udata.core.organization.models import *
from udata.core.contact_point.models import *
from udata.core.dataset.models import *
from udata.core.dataservices.models import *
from udata.core.reuse.models import *
from udata.core.site.models import *
from udata.core.activity.models import *
from udata.core.topic.models import *
from udata.core.post.models import *
from udata.core.jobs.models import *
from udata.core.tags.models import *
from udata.core.spam.models import *
from udata.core.reports.models import *
from udata.core.visualizations.models import *
from udata.features.transfer.models import *

# Load HarvestSource model as harvest for catalog
from udata.harvest.models import HarvestSource as Harvest  # noqa
