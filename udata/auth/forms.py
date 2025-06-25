import datetime

import requests
from flask import current_app
from flask_login import current_user
from flask_security.forms import (
    ForgotPasswordForm,
    Form,
    LoginForm,
    RegisterForm,
    ResetPasswordForm,
)

from udata.core.captchetat import bearer_token
from udata.forms import fields, validators
from udata.i18n import lazy_gettext as _


class WithCaptcha:
    captcha_code = fields.StringField(_("Captcha code"))
    captcha_uuid = fields.StringField(_("Captcha ID"))

    def validate_captcha(self):
        if check_captchetat(self.captcha_uuid.data, self.captcha_code.data):
            return True

        self.captcha_code.errors = [_("Invalid Captcha")]
        return False


class ExtendedRegisterForm(WithCaptcha, RegisterForm):
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

    def validate(self, **kwargs):
        # no register allowed when read only mode is on
        if not super().validate(**kwargs) or current_app.config.get("READ_ONLY_MODE"):
            return False

        if not self.validate_captcha():
            return False

        return True


class ExtendedLoginForm(LoginForm):
    def validate(self, **kwargs):
        if not super().validate(**kwargs):
            return False

        if self.user.password_rotation_demanded:
            self.password.errors.append(_("Password must be changed for security reasons"))
            return False

        return True


class ExtendedResetPasswordForm(WithCaptcha, ResetPasswordForm):
    def validate(self, **kwargs):
        if not super().validate(**kwargs):
            return False

        if self.user.password_rotation_demanded:
            self.user.password_rotation_demanded = None
            self.user.password_rotation_performed = datetime.datetime.utcnow()
            self.user.save()

        if not self.validate_captcha():
            return False

        return True


class ExtendedForgotPasswordForm(WithCaptcha, ForgotPasswordForm):
    def validate(self, **kwargs):
        if not super().validate(**kwargs):
            return False

        if not self.validate_captcha():
            return False

        return True


class ChangeEmailForm(Form):
    new_email = fields.StringField(_("New email"), [validators.DataRequired(), validators.Email()])
    new_email_confirm = fields.StringField(
        _("Retype email"),
        [validators.EqualTo("new_email", message=_("Email does not match")), validators.Email()],
    )
    submit = fields.SubmitField(_("Change email"))

    def validate(self, **kwargs):
        if not super().validate(**kwargs):
            return False

        self.user = current_user

        if self.user.email.strip() == self.new_email.data.strip():
            self.new_email.errors.append(
                "Your new email must be different than your previous email"
            )
            return False
        return True


def check_captchetat(id: str, code: str) -> bool:
    captchetat_url = current_app.config.get("CAPTCHETAT_BASE_URL")
    if not captchetat_url:
        return True

    print(id)
    print(code)
    if not id or not code:
        return False

    headers = {"Authorization": "Bearer " + bearer_token()}
    try:
        resp = requests.post(
            f"{captchetat_url}/valider-captcha",
            headers=headers,
            json={
                "uuid": id,
                "code": code,
            },
        )
        print(resp)
        return resp.text == "true"
    except requests.exceptions.RequestException as err:
        print(err)
        # Should not happen, log?
        return False
