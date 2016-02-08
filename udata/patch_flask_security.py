from flask_security import (
    changeable, confirmable, passwordless, recoverable, registerable
)

from . import mail
from .tasks import task

from udata.models import datastore


@task
def sendmail(subject, email, template, **context):
    user = datastore.get_user(email)
    tpl = 'security/{0}'.format(template)
    mail.send(subject, user, tpl, **context)


changeable.send_mail = sendmail.delay
confirmable.send_mail = sendmail.delay
passwordless.send_mail = sendmail.delay
recoverable.send_mail = sendmail.delay
registerable.send_mail = sendmail.delay
