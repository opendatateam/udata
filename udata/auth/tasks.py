from udata import mail
from udata.core.user.models import datastore
from udata.tasks import task


@task
def sendmail(subject, email, template, **context):
    user = datastore.get_user(email)
    context['user'] = user
    tpl = 'security/{0}'.format(template)
    mail.send(subject, user, tpl, **context)


def sendmail_proxy(subject, email, template, **context):
    """Cast the lazy_gettext'ed subject to string before passing to Celery"""
    context.pop('user')  # Remove complex user object, fetched by mail in task
    sendmail.delay(subject.value, email, template, **context)
