import logging

from udata import mail
from udata.i18n import lazy_gettext as _
from udata.tasks import task

from .models import datastore

log = logging.getLogger(__name__)


@task(route='high.mail')
def send_test_mail(email):
    user = datastore.find_user(email=email)
    mail.send(_('Test mail'), user, 'test')
