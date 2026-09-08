from udata.core import storages
from udata.core.badges.tasks import notify_new_badge
from udata.features.notifications.models import Notification
from udata.models import Activity, ContactPoint, Dataset, Follow, GeoZone, Transfer
from udata.search import reindex
from udata.tasks import get_logger, job, task

from . import mails
from .api_entreprise import fetch_company_info, parse_zone_match
from .assignment import Assignment
from .constants import ASSOCIATION, CERTIFIED, COMPANY, LOCAL_AUTHORITY, PUBLIC_SERVICE
from .models import Organization
from .notifications import (
    MembershipAcceptedNotificationDetails,
    MembershipRefusedNotificationDetails,
    NewBadgeNotificationDetails,
)

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
        try:
            notification = Notification(
                user=request.user,
                details=MembershipAcceptedNotificationDetails(
                    organization=org,
                ),
            )
            notification.save()
        except Exception as e:
            log.error(
                f"Failed to create membership accepted notification for user {request.user}: {e}"
            )
    else:
        mails.membership_refused(org).send(request.user)
        try:
            notification = Notification(
                user=request.user,
                details=MembershipRefusedNotificationDetails(
                    organization=org,
                ),
            )
            notification.save()
        except Exception as e:
            log.error(
                f"Failed to create membership refused notification for user {request.user}: {e}"
            )


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
        try:
            notification = Notification(
                user=member.user,
                details=NewBadgeNotificationDetails(organization=org, kind=CERTIFIED),
            )
            notification.save()
        except Exception as e:
            log.error(
                f"Failed to create new badge notification for kind {CERTIFIED} and user {member.user}: {e}"
            )


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
        try:
            notification = Notification(
                user=member.user,
                details=NewBadgeNotificationDetails(organization=org, kind=PUBLIC_SERVICE),
            )
            notification.save()
        except Exception as e:
            log.error(
                f"Failed to create new badge notification for kind {PUBLIC_SERVICE} and user {member.user}: {e}"
            )


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
        try:
            notification = Notification(
                user=member.user,
                details=NewBadgeNotificationDetails(organization=org, kind=COMPANY),
            )
            notification.save()
        except Exception as e:
            log.error(
                f"Failed to create new badge notification for kind {COMPANY} and user {member.user}: {e}"
            )


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
        try:
            notification = Notification(
                user=member.user,
                details=NewBadgeNotificationDetails(organization=org, kind=ASSOCIATION),
            )
            notification.save()
        except Exception as e:
            log.error(
                f"Failed to create new badge notification for kind {ASSOCIATION} and user {member.user}: {e}"
            )


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
        try:
            notification = Notification(
                user=member.user,
                details=NewBadgeNotificationDetails(organization=org, kind=LOCAL_AUTHORITY),
            )
            notification.save()
        except Exception as e:
            log.error(
                f"Failed to create new badge notification for kind {LOCAL_AUTHORITY} and user {member.user}: {e}"
            )


@task
def lookup_organization_zone(org_id):
    """Resolve and persist `Organization.zone` + `extras.code_insee` from the SIRET.

    Sets the zone when the API positively identifies a local-authority entity
    (commune, département, région or EPCI). Clears it when the SIRET is removed
    or the entity stops being a local authority. Preserves derived data on
    inconclusive lookups (transient outage, malformed payload, GeoZone missing
    from the local referential) so a temporary failure never wipes a correct
    enrichment.
    """
    org = Organization.objects(pk=org_id).first()
    if org is None:
        return

    target_geoid = None
    target_code_insee = None
    if org.business_number_id:
        info = fetch_company_info(org.business_number_id)
        if info is None:
            return  # inconclusive — preserve existing enrichment
        candidate, code_insee, decisive = parse_zone_match(info)
        if not decisive:
            return  # malformed payload — preserve
        if candidate:
            resolved = GeoZone.objects.resolve(candidate, id_only=True)
            if not resolved:
                log.warning("GeoZone %s not found for organization %s", candidate, org_id)
                return  # missing referential — preserve
            target_geoid = resolved
            target_code_insee = code_insee
        # else: positively non-collectivité — fall through with None/None to clear.

    if org.zone == target_geoid and org.extras.get("code_insee") == target_code_insee:
        return
    org.zone = target_geoid
    if target_code_insee is None:
        org.extras.pop("code_insee", None)
    else:
        org.extras["code_insee"] = target_code_insee
    # Ignore post_save to avoid re-triggering the on_update signal that scheduled us.
    org.save(signal_kwargs={"ignores": ["post_save"]})


@Organization.on_create.connect
def _lookup_zone_on_org_create(organization, **kwargs):
    if organization.business_number_id:
        lookup_organization_zone.delay(str(organization.id))


@Organization.on_update.connect
def _lookup_zone_on_siret_update(organization, **kwargs):
    if "business_number_id" not in kwargs.get("changed_fields", []):
        return
    # Schedule even when the SIRET was removed so a previously-set zone is cleared.
    lookup_organization_zone.delay(str(organization.id))
