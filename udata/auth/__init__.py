import logging

from flask import current_app, render_template
from flask_principal import Permission as BasePermission
from flask_principal import PermissionDenied as PermissionDenied
from flask_principal import RoleNeed as RoleNeed
from flask_principal import UserNeed as UserNeed
from flask_principal import identity_loaded as identity_loaded
from flask_security import Security as Security
from flask_security import current_user as current_user
from flask_security import login_required as login_required
from flask_security import login_user as login_user

from . import mails

log = logging.getLogger(__name__)


def render_security_template(template_name_or_list, **kwargs):
    result = mails.render_mail_template(template_name_or_list, **kwargs)
    if result is not None:
        return result

    return render_template(template_name_or_list, **kwargs)


security = Security()


class Permission(BasePermission):
    def __init__(self, *needs):
        """Let administrator bypass all permissions"""
        super(Permission, self).__init__(RoleNeed("admin"), *needs)


admin_permission = Permission()


def init_app(app):
    from udata.models import datastore

    from .forms import (
        ExtendedForgotPasswordForm,
        ExtendedLoginForm,
        ExtendedRegisterForm,
        ExtendedResetPasswordForm,
    )
    from .password_validation import UdataPasswordUtil
    from .views import create_security_blueprint

    # We want to alias SECURITY_POST_CONFIRM_VIEW to the CDATA_BASE_URL (the homepage)
    # but can't do it in `settings.py` because it's not defined yet (`CDATA_BASE_URL` is set
    # in the env)
    # :SecurityPostConfirmViewAtRuntime
    if app.config["CDATA_BASE_URL"]:
        app.config.setdefault(
            "SECURITY_POST_CONFIRM_VIEW", app.config["CDATA_BASE_URL"] + "?flash=post_confirm"
        )

    security.init_app(
        app,
        datastore,
        register_blueprint=False,
        render_template=render_security_template,
        login_form=ExtendedLoginForm,
        confirm_register_form=ExtendedRegisterForm,
        register_form=ExtendedRegisterForm,
        reset_password_form=ExtendedResetPasswordForm,
        forgot_password_form=ExtendedForgotPasswordForm,
        password_util_cls=UdataPasswordUtil,
    )

    security_bp = create_security_blueprint(app, app.extensions["security"], "security_blueprint")

    app.register_blueprint(security_bp)
