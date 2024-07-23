from flask import current_app, flash, redirect, url_for
from flask_login import current_user, login_required
from flask_security.utils import (
    check_and_get_token_status,
    do_flash,
    get_message,
    get_within_delta,
    hash_data,
    login_user,
    logout_user,
    send_mail,
    verify_hash,
)
from flask_security.views import (
    change_password,
    confirm_email,
    forgot_password,
    login,
    logout,
    register,
    reset_password,
    send_confirmation,
    send_login,
    token_login,
)
from werkzeug.local import LocalProxy

from udata.i18n import lazy_gettext as _
from udata.uris import endpoint_for

from .forms import ChangeEmailForm

_security = LocalProxy(lambda: current_app.extensions["security"])
_datastore = LocalProxy(lambda: _security.datastore)


def slash_url_suffix(url, suffix):
    """Adds a slash either to the beginning or the end of a suffix
    (which is to be appended to a URL), depending on whether or not
    the URL ends with a slash.
    """

    return url.endswith("/") and ("%s/" % suffix) or ("/%s" % suffix)


def send_change_email_confirmation_instructions(user, new_email):
    data = [str(current_user.fs_uniquifier), hash_data(current_user.email), new_email]
    token = _security.confirm_serializer.dumps(data)
    confirmation_link = url_for("security.confirm_change_email", token=token, _external=True)

    subject = _("Confirm change of email instructions")
    send_mail(
        subject=subject,
        recipient=new_email,
        template="confirmation_instructions",
        user=current_user,
        confirmation_link=confirmation_link,
    )


def confirm_change_email_token_status(token):
    expired, invalid, token_data = check_and_get_token_status(
        token, "confirm", get_within_delta("CONFIRM_EMAIL_WITHIN")
    )
    new_email = None

    if not invalid and token_data:
        user, token_email_hash, new_email = token_data
        user = _datastore.find_user(fs_uniquifier=user)
        invalid = not verify_hash(token_email_hash, user.email)

    return expired, invalid, user, new_email


def confirm_change_email(token):
    expired, invalid, user, new_email = confirm_change_email_token_status(token)

    if not user or invalid:
        invalid = True
        do_flash(*get_message("INVALID_CONFIRMATION_TOKEN"))
    if expired:
        send_change_email_confirmation_instructions(user, new_email)
        do_flash(
            _(
                "You did not confirm your change of email within {email_within}. New instructions to confirm your change of email have been sent to {new_email}."
            ).format(email_within=_security.confirm_email_within, new_email=new_email),
            "error",
        )
    if invalid or expired:
        return redirect(endpoint_for("site.home", "admin.index"))

    if user != current_user:
        logout_user()
        login_user(user)

    user.email = new_email
    _datastore.put(user)
    msg = (_("Thank you. Your change of email has been confirmed."), "success")

    do_flash(*msg)
    return redirect(endpoint_for("site.home", "admin.index"))


@login_required
def change_email():
    """Change email page."""

    form = ChangeEmailForm()

    if form.validate_on_submit():
        new_email = form.new_email.data
        send_change_email_confirmation_instructions(current_user, new_email)
        flash(
            _(
                "Thank you. Confirmation instructions for changing your email have been sent to {new_email}."
            ).format(new_email=new_email),
            "success",
        )
        return redirect(endpoint_for("site.home", "admin.index"))

    return _security.render_template("security/change_email.html", change_email_form=form)


def create_security_blueprint(app, state, import_name):
    from udata.i18n import I18nBlueprint

    """
    Creates the security extension blueprint
    This creates an I18nBlueprint to use as a base.
    """
    bp = I18nBlueprint(
        state.blueprint_name,
        import_name,
        url_prefix=state.url_prefix,
        subdomain=state.subdomain,
        template_folder="templates",
    )

    bp.route(app.config["SECURITY_LOGOUT_URL"], endpoint="logout")(logout)

    if state.passwordless:
        bp.route(app.config["SECURITY_LOGIN_URL"], methods=["GET", "POST"], endpoint="login")(
            send_login
        )
        bp.route(
            app.config["SECURITY_LOGIN_URL"]
            + slash_url_suffix(app.config["SECURITY_LOGIN_URL"], "<token>"),
            endpoint="token_login",
        )(token_login)
    else:
        bp.route(app.config["SECURITY_LOGIN_URL"], methods=["GET", "POST"], endpoint="login")(login)

    if state.registerable:
        bp.route(app.config["SECURITY_REGISTER_URL"], methods=["GET", "POST"], endpoint="register")(
            register
        )

    if state.recoverable:
        bp.route(
            app.config["SECURITY_RESET_URL"], methods=["GET", "POST"], endpoint="forgot_password"
        )(forgot_password)
        bp.route(
            app.config["SECURITY_RESET_URL"]
            + slash_url_suffix(app.config["SECURITY_RESET_URL"], "<token>"),
            methods=["GET", "POST"],
            endpoint="reset_password",
        )(reset_password)

    if state.changeable:
        bp.route(
            app.config["SECURITY_CHANGE_URL"], methods=["GET", "POST"], endpoint="change_password"
        )(change_password)

    if state.confirmable:
        bp.route(
            app.config["SECURITY_CONFIRM_URL"],
            methods=["GET", "POST"],
            endpoint="send_confirmation",
        )(send_confirmation)
        bp.route(
            app.config["SECURITY_CONFIRM_URL"]
            + slash_url_suffix(app.config["SECURITY_CONFIRM_URL"], "<token>"),
            methods=["GET", "POST"],
            endpoint="confirm_email",
        )(confirm_email)

    bp.route(
        "/confirm-change-email/<token>", methods=["GET", "POST"], endpoint="confirm_change_email"
    )(confirm_change_email)

    bp.route("/change-email", methods=["GET", "POST"], endpoint="change_email")(change_email)

    return bp
