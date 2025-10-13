from flask import current_app, jsonify, redirect, request, url_for
from flask_login import current_user, login_required
from flask_security.utils import (
    check_and_get_token_status,
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
from flask_wtf.csrf import generate_csrf
from werkzeug.local import LocalProxy

from udata.auth.proconnect import get_logout_url
from udata.i18n import lazy_gettext as _
from udata.uris import homepage_url
from udata.utils import wants_json

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

    flash = None
    flash_data = None
    if expired:
        send_change_email_confirmation_instructions(user, new_email)
        flash = "change_email_expired"
        flash_data = {
            "email_within": _security.confirm_email_within,
            "new_email": new_email,
        }
    elif not user or invalid:
        flash = "change_email_invalid"

    if flash:
        return redirect(homepage_url(flash=flash, flash_data=flash_data))

    if user != current_user:
        logout_user()
        login_user(user)

    user.email = new_email
    _datastore.put(user)

    return redirect(homepage_url(flash="change_email_confirmed"))


def get_csrf():
    # We need to have a public endpoint for getting a CSRF token.
    # In Flask, we can query the form with an Accept:application/json,
    # for example: GET `/login` to get a JSON with the CSRF token.
    # It's not working in our implementation because GET `/login` is routed to
    # cdata and not udata. So we need to have an endpoint existing only on udata
    # so we can fetch a valid CSRF token.
    return jsonify({"response": {"csrf_token": generate_csrf()}})


@login_required
def change_email():
    """Change email page."""

    form = ChangeEmailForm()

    if form.validate_on_submit():
        new_email = form.new_email.data
        send_change_email_confirmation_instructions(current_user, new_email)

        if wants_json():
            return jsonify({})

        return redirect(
            homepage_url(
                flash="change_email",
                flash_data={
                    "email": new_email,
                },
            )
        )

    if wants_json():
        return jsonify({"response": {"csrf_token": generate_csrf()}})

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

    bp.route(app.config["SECURITY_LOGOUT_URL"], methods=["GET", "POST"], endpoint="logout")(
        logout_with_proconnect_url
    )

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
    bp.route("/get-csrf", methods=["GET"], endpoint="get_csrf")(get_csrf)

    return bp


def logout_with_proconnect_url():
    """
    Extends the flask-security `logout` by returning the ProConnect logout URL (if any)
    so `cdata` can redirect to it if the user was connected via ProConnect.
    """
    # after the redirection to ProConnect logout, the user will be redirected
    # to our logout again with ProconnectLogoutAPI.
    if request.method == "POST" and wants_json():
        proconnect_logout_url = get_logout_url()

        if proconnect_logout_url:
            return jsonify(
                {
                    "proconnect_logout_url": get_logout_url(),
                }
            )

    # Calling the flask-security logout endpoint
    logout()

    # But rewriting the response since we want to redirect with a flash
    # query param for cdata. Flask-Security redirects to the homepage without
    # any information.
    # PS: in a normal logout it's a JSON request, but after logout from ProConnect
    # the user is redirected to this endpoint as a normal HTTP request, so we must
    # manage the basic redirection in this case.
    if request.method == "POST" and wants_json():
        return jsonify({})

    return redirect(homepage_url(flash="logout"))
