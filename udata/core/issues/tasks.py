from udata import mail
from udata.i18n import lazy_gettext as _
from udata.models import Dataset, Reuse
from udata.tasks import connect, get_logger

from .models import Issue, Message
from .signals import on_new_issue, on_new_issue_comment, on_issue_closed

log = get_logger(__name__)


def owner_recipients(issue):
    if issue.subject.organization:
        return [m.user for m in issue.subject.organization.members]
    else:
        return [issue.subject.owner]


@connect(on_new_issue, by_id=True)
def notify_new_issue(issue_id):
    issue = Issue.objects.get(pk=issue_id)
    if isinstance(issue.subject, (Dataset, Reuse)):
        recipients = owner_recipients(issue)
        subject = _('Your %(type)s have a new issue',
                    type=issue.subject.verbose_name)
        mail.send(subject, recipients, 'new_issue', issue=issue,
                  message=issue.discussion[0])
    else:
        log.warning('Unrecognized issue subject type %s', type(issue.subject))


@connect(on_new_issue_comment, by_id=True)
def notify_new_issue_comment(issue_id, message=None):
    issue = Issue.objects.get(pk=issue_id)
    message = issue.discussion[message]
    if isinstance(issue.subject, (Dataset, Reuse)):
        recipients = owner_recipients(issue) + [
            m.posted_by for m in issue.discussion]
        recipients = [u for u in set(recipients) if u != message.posted_by]
        subject = _('%(user)s commented your issue',
                    user=message.posted_by.fullname)
        mail.send(subject, recipients, 'new_issue_comment',
                  issue=issue, message=message)
    else:
        log.warning('Unrecognized issue subject type %s', type(issue.subject))


@connect(on_issue_closed, by_id=True)
def notify_issue_closed(issue_id, message=None):
    issue = Issue.objects.get(pk=issue_id)
    message = issue.discussion[message]
    if isinstance(issue.subject, (Dataset, Reuse)):
        recipients = owner_recipients(issue) + [
            m.posted_by for m in issue.discussion]
        recipients = [u for u in set(recipients) if u != message.posted_by]
        subject = _('An issue has been closed')
        mail.send(subject, recipients, 'issue_closed',
                  issue=issue, message=message)
    else:
        log.warning('Unrecognized issue subject type %s', type(issue.subject))
