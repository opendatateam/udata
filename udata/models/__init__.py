from mongoengine.errors import ValidationError  # noqa

from udata import entrypoints  # noqa
from udata.mongo import *  # noqa

# Load all core models and mixins
from udata.core.spatial.models import *  # noqa
from udata.core.metrics.models import *  # noqa
from udata.core.badges.models import *  # noqa
from udata.core.discussions.models import *  # noqa
from udata.core.followers.models import *  # noqa
from udata.core.user.models import *  # noqa
from udata.core.organization.models import *  # noqa
from udata.core.contact_point.models import *  # noqa
from udata.core.site.models import *  # noqa
from udata.core.dataset.models import *  # noqa
from udata.core.reuse.models import *  # noqa
from udata.core.activity.models import *  # noqa
from udata.core.topic.models import *  # noqa
from udata.core.post.models import *  # noqa
from udata.core.jobs.models import *  # noqa
from udata.core.tags.models import *  # noqa
from udata.core.spam.models import *  # noqa
from udata.core.reports.models import *  # noqa
from udata.core.dataservices.models import *  # noqa

from udata.features.transfer.models import *  # noqa
from udata.features.territories.models import *  # noqa

# Load HarvestSource model as harvest for catalog
from udata.harvest.models import HarvestSource as Harvest  # noqa

import udata.linkchecker.models  # noqa


def init_app(app):
    entrypoints.get_enabled("udata.models", app)
