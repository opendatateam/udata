# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from flask import render_template, current_app, Blueprint, request, redirect
from flask.ext.principal import (
    Permission as BasePermission, PermissionDenied, identity_loaded, RoleNeed,
    UserNeed
)
from flask.ext.security import (
    Security, current_user, login_required, login_user
)
from werkzeug.utils import import_string


bp = Blueprint('auth', __name__)

log = logging.getLogger(__name__)


class UDataSecurity(Security):
    def render_template(self, *args, **kwargs):
        try:
            render = import_string(current_app.config.get('SECURITY_RENDER'))
        except:
            render = render_template
        return render(*args, **kwargs)


security = UDataSecurity()


class Permission(BasePermission):
    def __init__(self, *needs):
        '''Let administrator bypass all permissions'''
        super(Permission, self).__init__(RoleNeed('admin'), *needs)

admin_permission = Permission()


@bp.before_app_request
def ensure_https_authenticated_users():
    # Force authenticated users to use https
    if (not current_app.config.get('TESTING', False)
            and current_app.config.get('USE_SSL', False)
            and current_user.is_authenticated()
            and not request.is_secure):
        return redirect(request.url.replace('http://', 'https://'))


def init_app(app):
    from udata.models import datastore
    security.init_app(app, datastore)

    app.register_blueprint(bp)
