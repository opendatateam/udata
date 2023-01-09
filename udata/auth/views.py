from flask import flash, redirect, url_for, current_app
from flask_login import current_user, login_required
from flask_security.views import change_password
from flask_security.views import confirm_email
from flask_security.views import forgot_password
from flask_security.views import login
from flask_security.views import logout
from flask_security.views import register
from flask_security.views import reset_password
from flask_security.views import send_confirmation
from flask_security.views import send_login
from flask_security.views import token_login
from flask_security.utils import (
    send_mail, do_flash, get_message, get_token_status, hash_data,
    login_user, logout_user, verify_hash)
from werkzeug.local import LocalProxy
from udata.i18n import lazy_gettext as _

from .forms import ChangeEmailForm


_security = LocalProxy(lambda: current_app.extensions['security'])
_datastore = LocalProxy(lambda: _security.datastore)


def slash_url_suffix(url, suffix):
    """Adds a slash either to the beginning or the end of a suffix
       (which is to be appended to a URL), depending on whether or not
       the URL ends with a slash.
    """

    return url.endswith('/') and ('%s/' % suffix) or ('/%s' % suffix)


def send_change_email_confirmation_instructions(user, new_email):
    data = [str(current_user.fs_uniquifier), hash_data(current_user.email), new_email]
    token = _security.confirm_serializer.dumps(data)
    confirmation_link = url_for('security.confirm_change_email', token=token, _external=True)

    subject = _('Confirm change of email instructions')
    send_mail(
        subject=subject,
        recipient=new_email,
        template='confirmation_instructions',
        user=current_user,
        confirmation_link=confirmation_link
    )


def confirm_change_email_token_status(token):
    expired, invalid, user, token_data = get_token_status(
        token, 'confirm', 'CONFIRM_EMAIL', return_data=True)
    new_email = None

    if not invalid and user:
        _, token_email_hash, new_email = token_data
        invalid = not verify_hash(token_email_hash, user.email)

    return expired, invalid, user, new_email


def confirm_change_email(token):
    expired, invalid, user, new_email = (
        confirm_change_email_token_status(token))

    if not user or invalid:
        invalid = True
        do_flash(*get_message('INVALID_CONFIRMATION_TOKEN'))
    if expired:
        send_change_email_confirmation_instructions(user, new_email)
        do_flash(*(
            (
                'You did not confirm your change of email within {0}. '
                'New instructions to confirm your change of email have '
                'been sent to {1}.').format(
                    _security.confirm_email_within, new_email),
            'error'))
    if invalid or expired:
        return redirect(url_for('site.home'))

    if user != current_user:
        logout_user()
        login_user(user)

    if user.email == new_email:
        msg = (
            'Your change of email has already been confirmed.',
            'info')
    else:
        user.email = new_email
        _datastore.put(user)
        msg = (
            'Thank you. Your change of email has been confirmed.',
            'success')

    do_flash(*msg)
    return redirect(url_for('site.home'))


@login_required
def change_email():
    """Change email page."""

    form = ChangeEmailForm()

    if form.validate_on_submit():
        new_email = form.new_email.data
        send_change_email_confirmation_instructions(current_user, new_email)

        flash(
            (
                'Thank you. Confirmation instructions for changing '
                'your email have been sent to {0}.').format(new_email),
            'success')
        return redirect(url_for('site.home'))

    return _security.render_template('security/change_email.html', form=form)


def create_security_blueprint(state, import_name):
    from udata.i18n import I18nBlueprint

    """
    Creates the security extension blueprint
    This creates an I18nBlueprint to use as a base.
    """

    bp = I18nBlueprint(state.blueprint_name, import_name,
                       url_prefix=state.url_prefix,
                       subdomain=state.subdomain,
                       template_folder='templates')

    bp.route(state.logout_url, endpoint='logout')(logout)

    if state.passwordless:
        bp.route(state.login_url,
                 methods=['GET', 'POST'],
                 endpoint='login')(send_login)
        bp.route(
            state.login_url + slash_url_suffix(state.login_url, '<token>'),
            endpoint='token_login'
        )(token_login)
    else:
        bp.route(state.login_url,
                 methods=['GET', 'POST'],
                 endpoint='login')(login)

    if state.registerable:
        bp.route(state.register_url,
                 methods=['GET', 'POST'],
                 endpoint='register')(register)

    if state.recoverable:
        bp.route(state.reset_url,
                 methods=['GET', 'POST'],
                 endpoint='forgot_password')(forgot_password)
        bp.route(
            state.reset_url + slash_url_suffix(state.reset_url, '<token>'),
            methods=['GET', 'POST'],
            endpoint='reset_password'
        )(reset_password)

    if state.changeable:
        bp.route(state.change_url,
                 methods=['GET', 'POST'],
                 endpoint='change_password')(change_password)

    if state.confirmable:
        bp.route(state.confirm_url,
                 methods=['GET', 'POST'],
                 endpoint='send_confirmation')(send_confirmation)
        bp.route(
            state.confirm_url + slash_url_suffix(state.confirm_url, '<token>'),
            methods=['GET', 'POST'],
            endpoint='confirm_email'
        )(confirm_email)

    bp.route('/confirm-change-email/<token>',
             methods=['GET', 'POST'],
             endpoint='confirm_change_email')(confirm_change_email)

    bp.route('/change-email', methods=['GET', 'POST'], endpoint='change_email')(change_email)

    return bp
