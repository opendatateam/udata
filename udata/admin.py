# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from flask.ext.superadmin import Admin, AdminIndexView, expose
from flask.ext.security import login_required, current_user

from udata.core import MODULES

log = logging.getLogger(__name__)


class AdminView(AdminIndexView):
    decorators = [login_required]

    @expose('/')
    def index(self):
        return self.render('admin/test.html')


admin = Admin(name='uData', index_view=AdminView())


def init_app(app):
    # Load all core admin modules
    for module in MODULES:
        try:
            __import__('udata.core.{0}.admin'.format(module))
        except ImportError as e:
            # log.error('Unable to import %s: %s', module, e)
            pass
        except Exception as e:
            log.error('Unable to import %s: %s', module, e)

    # Load all extensions admin
    for plugin in app.config['PLUGINS']:
        try:
            __import__('udata.ext.{0}.admin'.format(plugin))
        except ImportError as e:
            # log.error('Unable to import %s admin: %s', plugin, e)
            pass
        except Exception as e:
            log.error('Unable to import %s admin: %s', plugin, e)

    admin.init_app(app)
