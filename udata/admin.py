# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from flask import redirect, url_for

from udata.core.user.permissions import sysadmin
from udata.frontend import nav
from udata.i18n import I18nBlueprint

log = logging.getLogger(__name__)

blueprint = I18nBlueprint('admin', __name__, url_prefix='/admin')

navbar = nav.Bar('admin', [])


@blueprint.route('/', endpoint='root')
def redirect_to_first_admin_tab():
    endpoint = navbar.items[0].endpoint
    return redirect(url_for(endpoint))


class AdminView(object):
    require = sysadmin

    def get_context(self):
        context = super(AdminView, self).get_context()
        current_item = None
        for item in navbar:
            if item.is_active:
                current_item = item
        context['current_item'] = current_item
        return context


def register(endpoint, label=None):
    '''A class decorator for registering admin views'''
    def wrapper(cls):
        blueprint.add_url_rule('/{0}/'.format(endpoint), view_func=cls.as_view(str(endpoint)))
        navbar.items.append(nav.Item(label or endpoint.title(), 'admin.{0}'.format(endpoint)))
        return cls
    return wrapper


def init_app(app):
    # Import admin views
    import udata.core.site.admin
    import udata.core.topic.admin
    import udata.core.post.admin
    import udata.core.issues.admin
    import udata.core.jobs.admin

    # Import plugins admin views
    for plugin in app.config['PLUGINS']:
        try:
            __import__('udata.ext.{0}.admin'.format(plugin))
        except ImportError as e:
            # log.error('Unable to import %s admin: %s', plugin, e)
            pass
        except Exception as e:
            log.error('Unable to import %s admin: %s', plugin, e)

    app.register_blueprint(blueprint)
