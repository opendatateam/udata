import logging
from copy import copy
from datetime import datetime, timedelta

from flask import current_app

from udata import mail
from udata.i18n import lazy_gettext as _
from udata.tasks import job, task

from .models import User, datastore

log = logging.getLogger(__name__)


@task(route="high.mail")
def send_test_mail(email):
    user = datastore.find_user(email=email)
    mail.send(_("Test mail"), user, "test")


# TODO: some questions to answer
# 1. how to make sure that we have the minimum time between notify and delete if for a reason
#    or another, the notify job is not working.
#    Should we store a notification_date?
#    Should it run only on the 1st of each month?
# 2. How to deactivate/delete account?
#    Should we set active=false instead of deleting account?
#    Can we keep comments?
#    What about other contents (Dataset, Org, etc.)?
#    Our confidentiality policy states : "Données relatives au Contributeur qui s’inscrit"
# 3. Should we add a link to contact us if they can't connect?
# 4. Can we deal with ooooold inactive users with this system? Or should we do a specific Brevo campaign?
# 5. How to make the + / - timedelta more readable?


@job("notify-inactive-users")
def notify_inactive_users(self):
    last_login_notification_date = (
        datetime.utcnow()
        - timedelta(days=current_app.config["YEARS_OF_INACTIVITY_BEFORE_DEACTIVATION"] * 365)
        + timedelta(days=current_app.config["DAYS_BEFORE_ACCOUNT_INACTIVITY_NOTIFY_DELAY"])
    )

    for user in User.objects(last_login_at__lte=last_login_notification_date):
        mail.send(_("Account inactivity"), user, "account_inactivity", user=user)


@job("delete-inactive-users")
def delete_inactive_users(self):
    last_login_deletion_date = datetime.utcnow() - timedelta(
        days=current_app.config["YEARS_OF_INACTIVITY_BEFORE_DEACTIVATION"] * 365
    )
    for user in User.objects(last_login_at__lte=last_login_deletion_date):
        copied_user = copy(user)
        user.mark_as_deleted(notify=False, delete_comments=False)
        mail.send(_("Inactive account deletion"), copied_user, "inactive_account_deleted")
