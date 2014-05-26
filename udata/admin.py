# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from flask.ext.superadmin import Admin, AdminIndexView, expose
from flask.ext.security import login_required, current_user

log = logging.getLogger(__name__)


class AdminView(AdminIndexView):
    decorators = [login_required]

    @expose('/')
    def index(self):
        return self.render('admin/test.html')


admin = Admin(name='uData', index_view=AdminView())


def init_app(app):
    # Load all core admin modules
    import udata.core.user.admin
    import udata.core.dataset.admin
    import udata.core.reuse.admin
    import udata.core.organization.admin
    import udata.core.topic.admin
    import udata.core.post.admin

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
