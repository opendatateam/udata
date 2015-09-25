# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from importlib import import_module

import logging

log = logging.getLogger(__name__)


def init_app(app):
    # Load core notifications
    import udata.core.organization.notifications
    import udata.core.discussions.notifications
    import udata.core.issues.notifications

    # Load feature notifications
    import udata.features.transfer.notifications

    # Load all plugins views and blueprints
    for plugin in app.config['PLUGINS']:
        module = 'udata.ext.{0}.notifications'.format(plugin)
        try:
            import_module(module)
        except ImportError:
            pass
        except:
            log.exception('Error importing %s notifications', module)
