from flask_security import (
    changeable, confirmable, passwordless, recoverable, registerable
)

from . import mail
from .tasks import task

from udata.models import datastore


@task(route='high.mail')
def sendmail(subject, email, template, **context):
    user = datastore.get_user(email)
    tpl = 'security/{0}'.format(template)
    mail.send(subject, user, tpl, **context)


def sendmail_proxy(subject, email, template, **context):
    """Cast the lazy_gettext'ed subject to string before passing to Celery"""
    sendmail.delay(subject.value, email, template, **context)


changeable.send_mail = sendmail_proxy
confirmable.send_mail = sendmail_proxy
passwordless.send_mail = sendmail_proxy
recoverable.send_mail = sendmail_proxy
registerable.send_mail = sendmail_proxy
