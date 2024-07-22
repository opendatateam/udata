import datetime

from flask import current_app
from flask_login import current_user
from flask_security.forms import Form, LoginForm, RegisterForm, ResetPasswordForm

from udata.forms import fields, validators
from udata.i18n import lazy_gettext as _


class ExtendedRegisterForm(RegisterForm):
    first_name = fields.StringField(
        _("First name"),
        [
            validators.DataRequired(_("First name is required")),
            validators.NoURLs(_("URLs not allowed in this field")),
        ],
    )
    last_name = fields.StringField(
        _("Last name"),
        [
            validators.DataRequired(_("Last name is required")),
            validators.NoURLs(_("URLs not allowed in this field")),
        ],
    )

    def validate(self):
        # no register allowed when read only mode is on
        if not super().validate() or current_app.config.get("READ_ONLY_MODE"):
            return False

        return True


class ExtendedLoginForm(LoginForm):
    def validate(self):
        if not super().validate():
            return False

        if self.user.password_rotation_demanded:
            self.password.errors.append(_("Password must be changed for security reasons"))
            return False

        return True


class ExtendedResetPasswordForm(ResetPasswordForm):
    def validate(self):
        if not super().validate():
            return False

        if self.user.password_rotation_demanded:
            self.user.password_rotation_demanded = None
            self.user.password_rotation_performed = datetime.datetime.utcnow()
            self.user.save()

        return True


class ChangeEmailForm(Form):
    new_email = fields.StringField(_("New email"), [validators.DataRequired(), validators.Email()])
    new_email_confirm = fields.StringField(
        _("Retype email"),
        [validators.EqualTo("new_email", message=_("Email does not match")), validators.Email()],
    )
    submit = fields.SubmitField(_("Change email"))

    def validate(self):
        if not super().validate():
            return False

        self.user = current_user

        if self.user.email.strip() == self.new_email.data.strip():
            self.new_email.errors.append(
                "Your new email must be different than your " "previous email"
            )
            return False
        return True
