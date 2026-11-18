import logging
from datetime import UTC, datetime

import requests
from flask import current_app, session
from flask_login import current_user
from flask_security.forms import (
    ChangePasswordForm,
    ForgotPasswordForm,
    Form,
    LoginForm,
    RegisterFormV2,
    ResetPasswordForm,
    TwoFactorSetupForm,
    VerifyForm,
)

from udata.auth.proconnect import LOGIN_KEY, PENDING_LOGIN_KEY, session_login
from udata.core.captchetat import bearer_token
from udata.forms import fields, validators
from udata.i18n import lazy_gettext as _

log = logging.getLogger(__name__)


class WithCaptcha:
    captcha_code = fields.StringField(_("Captcha code"))
    captcha_uuid = fields.StringField(_("Captcha ID"))

    def validate_captcha(self):
        if check_captchetat(self.captcha_uuid.data, self.captcha_code.data):
            return True

        self.captcha_code.errors = [_("Invalid Captcha")]
        return False


class ExtendedRegisterForm(WithCaptcha, RegisterFormV2):
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
    accept_conditions = fields.BooleanField(
        _("J'accepte les conditions générales d'utilisation"),
        validators=[
            validators.DataRequired(message=_("You must accept the terms of use to continue."))
        ],
    )

    def validate(self, **kwargs):
        if current_app.config.get("READ_ONLY_MODE"):
            return False

        if not self.validate_captcha():
            return False

        return super().validate(**kwargs)


# Giving a password to an account that signs in with ProConnect only, through a reset that only
# takes reading the mailbox, would open a second way in without its ProConnect second factor.
PROCONNECT_ONLY = _("This account signs in with ProConnect only.")


class ExtendedLoginForm(LoginForm):
    def validate(self, **kwargs):
        # A password login: a ProConnect login left in this browser, waiting for its udata
        # 2FA or not, says nothing of this one.
        session.pop(PENDING_LOGIN_KEY, None)
        session.pop(LOGIN_KEY, None)
        if not super().validate(**kwargs):
            return False

        if self.user.password_rotation_demanded:
            self.password.errors.append(_("Password must be changed for security reasons"))
            return False

        return True


class ExtendedResetPasswordForm(ResetPasswordForm):
    def validate(self, **kwargs):
        if not super().validate(**kwargs):
            return False

        if self.user.signs_in_with_proconnect_only:
            self.password.errors.append(PROCONNECT_ONLY)
            return False

        if self.user.password_rotation_demanded:
            self.user.password_rotation_demanded = None
            self.user.password_rotation_performed = datetime.now(UTC)
            self.user.save()

        return True


class ExtendedChangePasswordForm(ChangePasswordForm):
    def validate(self, **kwargs):
        # flask-security lets an account without a password set one with a fresh session.
        if current_user.signs_in_with_proconnect_only:
            self.new_password.errors = [PROCONNECT_ONLY]
            return False

        return super().validate(**kwargs)


class ExtendedForgotPasswordForm(WithCaptcha, ForgotPasswordForm):
    def validate(self, **kwargs):
        if not self.validate_captcha():
            return False

        return super().validate(**kwargs)


class ExtendedTwoFactorSetupForm(TwoFactorSetupForm):
    def validate(self, **kwargs):
        if not super().validate(**kwargs):
            return False
        if self.setup.data == "disable" or not self.user.second_factor_at_proconnect_only:
            return True
        # The ProConnect identity is the account's second factor: whoever sets up the
        # udata one must present it, or a stolen password would take the account over.
        login = session_login(LOGIN_KEY)
        if login is not None and login.presents_trusted_second_factor(self.user):
            return True
        self.setup.errors.append(
            _(
                "Your account is protected by the two-factor authentication of ProConnect: "
                "sign in with ProConnect to set up another one."
            )
        )
        return False


class ExtendedVerifyForm(VerifyForm):
    def validate(self, **kwargs):
        if not self.user.password:
            # passlib raises on a null hash: answer before flask-security compares to it.
            self.password.errors = [_("This account has no password.")]
            return False

        return super().validate(**kwargs)


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
        return resp.text == "true"
    except requests.exceptions.RequestException as err:
        log.error(f"Failed to query CaptchEtat: {err}")
        return True
