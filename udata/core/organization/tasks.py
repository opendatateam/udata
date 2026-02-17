from udata.core import storages
from udata.core.badges.tasks import notify_new_badge
from udata.features.notifications.models import Notification
from udata.models import Activity, ContactPoint, Dataset, Follow, Transfer
from udata.search import reindex
from udata.tasks import get_logger, job, task

from . import mails
from .assignment import Assignment
from .constants import ASSOCIATION, CERTIFIED, COMPANY, LOCAL_AUTHORITY, PUBLIC_SERVICE
from .models import Organization
from .notifications import NewBadgeNotificationDetails

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
        # Remove related notifications
        Notification.objects.with_organization_in_details(organization).delete()
        # Remove assignments
        Assignment.objects(organization=organization).delete()
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

    if request is None:
        return

    recipients = [m.user for m in org.by_role("admin")]
    mails.new_membership_request(org, request).send(recipients)


@task(route="high.mail")
def notify_membership_response(org_id, request_id):
    org = Organization.objects.get(pk=org_id)
    request = next((r for r in org.requests if str(r.id) == request_id), None)

    if request is None:
        return

    if request.status == "accepted":
        mails.membership_accepted(org).send(request.user)
    else:
        mails.membership_refused(org).send(request.user)


@task(route="high.mail")
def notify_membership_invitation(org_id, invitation_id):
    org = Organization.objects.get(pk=org_id)
    invitation = next((r for r in org.requests if str(r.id) == invitation_id), None)

    if invitation is None:
        return

    if invitation.user:
        mails.membership_invitation(org, invitation, user_exists=True).send(invitation.user)
    elif invitation.email:
        mails.membership_invitation(org, invitation, user_exists=False).send(invitation.email)


@task(route="high.mail")
def notify_membership_invitation_response(org_id, invitation_id):
    org = Organization.objects.get(pk=org_id)
    invitation = next((r for r in org.requests if str(r.id) == invitation_id), None)

    if invitation is None or invitation.created_by is None:
        return

    if invitation.status == "accepted":
        mails.membership_invitation_accepted(org, invitation).send(invitation.created_by)
    elif invitation.status == "refused":
        mails.membership_invitation_refused(org, invitation).send(invitation.created_by)


@task(route="high.mail")
def notify_membership_invitation_canceled(org_id, invitation_id):
    org = Organization.objects.get(pk=org_id)
    invitation = next((r for r in org.requests if str(r.id) == invitation_id), None)

    if invitation is None:
        return

    if invitation.user:
        mails.membership_invitation_canceled(org).send(invitation.user)
    elif invitation.email:
        mails.membership_invitation_canceled(org).send(invitation.email)


@notify_new_badge(Organization, CERTIFIED)
def notify_badge_certified(org_id):
    """
    Send an email and create notifications when a `CERTIFIED` badge is added to an `Organization`
    """
    org = Organization.objects.get(pk=org_id)
    recipients = [member.user for member in org.members]

    # Send email notifications
    mails.badge_added_certified(org).send(recipients)

    # Create in-app notifications
    for member in org.members:
        notification = Notification(
            user=member.user,
            details=NewBadgeNotificationDetails(organization=org, kind=CERTIFIED),
        )
        notification.save()


@notify_new_badge(Organization, PUBLIC_SERVICE)
def notify_badge_public_service(org_id):
    """
    Send an email and create notifications when a `PUBLIC_SERVICE` badge is added to an `Organization`
    """
    org = Organization.objects.get(pk=org_id)
    recipients = [member.user for member in org.members]

    # Send email notifications
    mails.badge_added_public_service(org).send(recipients)

    # Create in-app notifications
    for member in org.members:
        notification = Notification(
            user=member.user,
            details=NewBadgeNotificationDetails(organization=org, kind=PUBLIC_SERVICE),
        )
        notification.save()


@notify_new_badge(Organization, COMPANY)
def notify_badge_company(org_id):
    """
    Send an email when a `COMPANY` badge is added to an `Organization`
    """
    org = Organization.objects.get(pk=org_id)
    recipients = [member.user for member in org.members]
    mails.badge_added_company(org).send(recipients)

    # Create in-app notifications
    for member in org.members:
        notification = Notification(
            user=member.user,
            details=NewBadgeNotificationDetails(organization=org, kind=COMPANY),
        )
        notification.save()


@notify_new_badge(Organization, ASSOCIATION)
def notify_badge_association(org_id):
    """
    Send an email when a `ASSOCIATION` badge is added to an `Organization`
    """
    org = Organization.objects.get(pk=org_id)
    recipients = [member.user for member in org.members]
    mails.badge_added_association(org).send(recipients)

    # Create in-app notifications
    for member in org.members:
        notification = Notification(
            user=member.user,
            details=NewBadgeNotificationDetails(organization=org, kind=ASSOCIATION),
        )
        notification.save()


@notify_new_badge(Organization, LOCAL_AUTHORITY)
def notify_badge_local_authority(org_id):
    """
    Send an email when a `LOCAL_AUTHORITY` badge is added to an `Organization`
    """
    org = Organization.objects.get(pk=org_id)
    recipients = [member.user for member in org.members]
    mails.badge_added_local_authority(org).send(recipients)

    # Create in-app notifications
    for member in org.members:
        notification = Notification(
            user=member.user,
            details=NewBadgeNotificationDetails(organization=org, kind=LOCAL_AUTHORITY),
        )
        notification.save()
