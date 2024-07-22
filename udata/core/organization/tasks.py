from udata import mail
from udata.core import storages
from udata.core.badges.tasks import notify_new_badge
from udata.i18n import lazy_gettext as _
from udata.models import Activity, ContactPoint, Dataset, Follow, Transfer
from udata.search import reindex
from udata.tasks import get_logger, job, task

from .constants import ASSOCIATION, CERTIFIED, COMPANY, LOCAL_AUTHORITY, PUBLIC_SERVICE
from .models import Organization

log = get_logger(__name__)


@job("purge-organizations")
def purge_organizations(self):
    for organization in Organization.objects(deleted__ne=None):
        log.info(f"Purging organization {organization}")
        # Remove followers
        Follow.objects(following=organization).delete()
        # Remove activity
        Activity.objects(related_to=organization).delete()
        Activity.objects(organization=organization).delete()
        # Remove transfers
        Transfer.objects(recipient=organization).delete()
        Transfer.objects(owner=organization).delete()
        # Remove related contact points
        ContactPoint.objects(organization=organization).delete()
        # Store datasets for later reindexation
        d_ids = [d.id for d in Dataset.objects(organization=organization)]
        # Remove organization's logo in all sizes
        if organization.logo.filename is not None:
            storage = storages.avatars
            storage.delete(organization.logo.filename)
            storage.delete(organization.logo.original)
            for key, value in organization.logo.thumbnails.items():
                storage.delete(value)
        # Remove
        organization.delete()
        # Reindex the datasets that were linked to the organization
        for id in d_ids:
            reindex(Dataset.__name__, str(id))


@task(route="high.mail")
def notify_membership_request(org_id, request_id):
    org = Organization.objects.get(pk=org_id)
    request = next((r for r in org.requests if str(r.id) == request_id), None)

    recipients = [m.user for m in org.by_role("admin")]
    mail.send(
        _("New membership request"), recipients, "membership_request", org=org, request=request
    )


@task(route="high.mail")
def notify_membership_response(org_id, request_id):
    org = Organization.objects.get(pk=org_id)
    request = next((r for r in org.requests if str(r.id) == request_id), None)

    if request.status == "accepted":
        subject = _('You are now a member of the organization "%(org)s"', org=org)
        template = "new_member"
    else:
        subject, template = _("Membership refused"), "membership_refused"
    mail.send(subject, request.user, template, org=org, request=request)


@task
def notify_new_member(org_id, email):
    org = Organization.objects.get(pk=org_id)
    member = next((m for m in org.members if m.user.email == email), None)

    subject = _('You are now a member of the organization "%(org)s"', org=org)
    mail.send(subject, member.user, "new_member", org=org)


@notify_new_badge(Organization, CERTIFIED)
def notify_badge_certified(org_id):
    """
    Send an email when a `CERTIFIED` badge is added to an `Organization`
    """
    org = Organization.objects.get(pk=org_id)
    recipients = [member.user for member in org.members]
    subject = _('Your organization "%(name)s" has been certified', name=org.name)
    mail.send(
        subject,
        recipients,
        "badge_added_certified",
        organization=org,
        badge=org.get_badge(CERTIFIED),
    )


@notify_new_badge(Organization, PUBLIC_SERVICE)
def notify_badge_public_service(org_id):
    """
    Send an email when a `PUBLIC_SERVICE` badge is added to an `Organization`
    """
    org = Organization.objects.get(pk=org_id)
    recipients = [member.user for member in org.members]
    subject = _('Your organization "%(name)s" has been identified as public service', name=org.name)
    mail.send(
        subject,
        recipients,
        "badge_added_public_service",
        organization=org,
        badge=org.get_badge(PUBLIC_SERVICE),
    )


@notify_new_badge(Organization, COMPANY)
def notify_badge_company(org_id):
    """
    Send an email when a `COMPANY` badge is added to an `Organization`
    """
    org = Organization.objects.get(pk=org_id)
    recipients = [member.user for member in org.members]
    subject = _('Your organization "%(name)s" has been identified as a company', name=org.name)
    mail.send(
        subject, recipients, "badge_added_company", organization=org, badge=org.get_badge(COMPANY)
    )


@notify_new_badge(Organization, ASSOCIATION)
def notify_badge_association(org_id):
    """
    Send an email when a `ASSOCIATION` badge is added to an `Organization`
    """
    org = Organization.objects.get(pk=org_id)
    recipients = [member.user for member in org.members]
    subject = _('Your organization "%(name)s" has been identified as an association', name=org.name)
    mail.send(
        subject,
        recipients,
        "badge_added_association",
        organization=org,
        badge=org.get_badge(ASSOCIATION),
    )


@notify_new_badge(Organization, LOCAL_AUTHORITY)
def notify_badge_local_authority(org_id):
    """
    Send an email when a `LOCAL_AUTHORITY` badge is added to an `Organization`
    """
    org = Organization.objects.get(pk=org_id)
    recipients = [member.user for member in org.members]
    subject = _(
        'Your organization "%(name)s" has been identified as a local authority', name=org.name
    )
    mail.send(
        subject,
        recipients,
        "badge_added_local_authority",
        organization=org,
        badge=org.get_badge(LOCAL_AUTHORITY),
    )
