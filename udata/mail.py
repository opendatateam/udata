# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
from contextlib import contextmanager

from flask import current_app
from flask.ext.mail import Mail, Message

from udata import theme, i18n


log = logging.getLogger(__name__)

mail = Mail()


@contextmanager
def dummyconnection(*args, **kw):
    """Allow to test email templates rendering without actually send emails."""
    yield


def init_app(app):
    mail.init_app(app)


def send(subject, recipients, template_base, **kwargs):
    '''
    Send a given email to multiple recipients.

    User prefered language is taken in account.
    To translate the subject in the right language, you should ugettext_lazy
    '''
    sender = kwargs.pop('sender', None)
    if not isinstance(recipients, (list, tuple)):
        recipients = [recipients]

    debug = current_app.config.get('DEBUG')
    send_mail = current_app.config.get('SEND_MAIL', not debug)
    connection = send_mail and dummyconnection or mail.connect

    with connection() as conn:
        for recipient in recipients:
            lang = i18n._default_lang(recipient)
            with i18n.language(lang):
                log.debug(
                    'Sending mail "%s" to recipient "%s"', subject, recipient)
                msg = Message(subject, sender=sender,
                              recipients=[recipient.email])
                msg.body = theme.render(
                    'mail/{0}.txt'.format(template_base), subject=subject,
                    sender=sender, recipient=recipient, **kwargs)
                msg.html = theme.render(
                    'mail/{0}.html'.format(template_base), subject=subject,
                    sender=sender, recipient=recipient, **kwargs)
                if debug:
                    log.debug(msg.body)
                    log.debug(msg.html)
                else:
                    conn.send(msg)
