import logging

from flask import current_app
from flask import render_template

from flask_principal import identity_loaded  # noqa: facade pattern
from flask_principal import Permission as BasePermission
from flask_principal import PermissionDenied  # noqa: facade pattern
from flask_principal import RoleNeed
from flask_principal import UserNeed  # noqa: facade pattern

from flask_security import ( # noqa
    Security, current_user, login_required, login_user # noqa
)
from werkzeug.utils import import_string

log = logging.getLogger(__name__)


class UDataSecurity(Security):
    def render_template(self, *args, **kwargs):
        try:
            render = import_string(current_app.config.get('SECURITY_RENDER'))
        except Exception:
            render = render_template
        return render(*args, **kwargs)


security = UDataSecurity()


class Permission(BasePermission):
    def __init__(self, *needs):
        '''Let administrator bypass all permissions'''
        super(Permission, self).__init__(RoleNeed('admin'), *needs)


admin_permission = Permission()


def init_app(app):
    from .forms import ExtendedRegisterForm, ExtendedLoginForm, ExtendedResetPasswordForm
    from .tasks import sendmail_proxy
    from .views import create_security_blueprint
    from .password_validation import password_validator
    from udata.models import datastore
    state = security.init_app(app, datastore,
                              register_blueprint=False,
                              login_form=ExtendedLoginForm,
                              confirm_register_form=ExtendedRegisterForm,
                              register_form=ExtendedRegisterForm,
                              reset_password_form=ExtendedResetPasswordForm,
                              send_mail=sendmail_proxy
                            )
    state.password_validator(password_validator)

    security_bp = create_security_blueprint(state, 'security_blueprint')

    app.register_blueprint(security_bp)
