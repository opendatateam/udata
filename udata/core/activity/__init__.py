# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging


from udata.core import MODULES

log = logging.getLogger(__name__)


def init_app(app):
    # Load all core actvitiess
    for module in MODULES:
        try:
            __import__('udata.core.{0}.activities'.format(module))
        except ImportError:
            pass
        except Exception as e:
            log.error('Unable to import activities for %s: %s', module, e)

    # Load plugins API
    for plugin in app.config['PLUGINS']:
        name = 'udata.ext.{0}.activities'.format(plugin)
        try:
            __import__(name)
        except ImportError:
            pass
        except Exception as e:
            log.error('Error importing %s: %s', name, e)
