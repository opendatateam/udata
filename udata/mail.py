# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging


from flask import render_template
from flask.ext.mail import Mail, Message


log = logging.getLogger(__name__)

mail = Mail()


def init_app(app):
    mail.init_app(app)


def send(subject, recipients, template_base, context, sender=None):
    '''
    Send a given email to multiple recipients.

    User prefered language is taken in account.
    To translate the subject in the right language, you should ugettext_lazy
    '''
    #sort user by prefered languages

    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = render_template('{0}.txt'.format(template_base), **context)
    msg.html = render_template('{0}.html'.format(template_base), **context)
    mail.send(msg)
