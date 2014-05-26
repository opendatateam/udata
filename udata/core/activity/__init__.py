# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging


log = logging.getLogger(__name__)


def init_app(app):
    # Load all core actvitiess
    import udata.core.user.activities
    import udata.core.dataset.activities
    import udata.core.reuse.activities

    # Load plugins API
    for plugin in app.config['PLUGINS']:
        name = 'udata.ext.{0}.activities'.format(plugin)
        try:
            __import__(name)
        except ImportError:
            pass
        except Exception as e:
            log.error('Error importing %s: %s', name, e)
