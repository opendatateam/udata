from udata import mail
from udata.core.user.models import datastore
from udata.tasks import task


@task
def sendmail(subject, email, template, **context):
    user = datastore.get_user(email)
    tpl = 'security/{0}'.format(template)
    mail.send(subject, user, tpl, **context)
