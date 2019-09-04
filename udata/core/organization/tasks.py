import warnings

from udata import mail
from udata.i18n import lazy_gettext as _
from udata.models import Follow, Activity, Metrics, Dataset
from udata.search import reindex
from udata.tasks import job, task, get_logger

from udata.core.badges.tasks import notify_new_badge

from .models import Organization, Member, MembershipRequest, CERTIFIED, PUBLIC_SERVICE

log = get_logger(__name__)


@job('purge-organizations')
def purge_organizations(self):
    for organization in Organization.objects(deleted__ne=None):
        log.info('Purging organization "{0}"'.format(organization))
        # Remove followers
        Follow.objects(following=organization).delete()
        # Remove activity
        Activity.objects(related_to=organization).delete()
        Activity.objects(organization=organization).delete()
        # Remove metrics
        Metrics.objects(object_id=organization.id).delete()
        # Store datasets for later reindexation
        d_ids = [d.id for d in Dataset.objects(organization=organization)]
        # Remove
        organization.delete()
        # Reindex the datasets that were linked to the organization
        for dataset in Dataset.objects(id__in=d_ids):
            reindex(dataset)


@task(route='high.mail')
def notify_membership_request(org_id, request_id):
    if isinstance(org_id, Organization):  # TODO: Remove this branch in udata 2.0
        warnings.warn(
            'Using documents as task parameter is deprecated and '
            'will be removed in udata 2.0',
            DeprecationWarning
        )
        org = org_id
    else:
        org = Organization.objects.get(pk=org_id)

    if isinstance(request_id, MembershipRequest):  # TODO: Remove this branch in udata 2.0
        warnings.warn(
            'Using documents as task parameter is deprecated and '
            'will be removed in udata 2.0',
            DeprecationWarning
        )
        request = request_id
    else:
        request = next((r for r in org.requests if str(r.id) == request_id), None)

    recipients = [m.user for m in org.by_role('admin')]
    mail.send(
        _('New membership request'), recipients, 'membership_request',
        org=org, request=request)


@task(route='high.mail')
def notify_membership_response(org_id, request_id):
    if isinstance(org_id, Organization):  # TODO: Remove this branch in udata 2.0
        warnings.warn(
            'Using documents as task parameter is deprecated and '
            'will be removed in udata 2.0',
            DeprecationWarning
        )
        org = org_id
    else:
        org = Organization.objects.get(pk=org_id)

    if isinstance(request_id, MembershipRequest):  # TODO: Remove this branch in udata 2.0
        warnings.warn(
            'Using documents as task parameter is deprecated and '
            'will be removed in udata 2.0',
            DeprecationWarning
        )
        request = request_id
    else:
        request = next((r for r in org.requests if str(r.id) == request_id), None)

    if request.status == 'accepted':
        subject = _('You are now a member of the organization "%(org)s"',
                    org=org)
        template = 'new_member'
    else:
        subject, template = _('Membership refused'), 'membership_refused'
    mail.send(subject, request.user, template, org=org, request=request)


@task
def notify_new_member(org_id, email):
    if isinstance(org_id, Organization):  # TODO: Remove this branch in udata 2.0
        warnings.warn(
            'Using documents as task parameter is deprecated and '
            'will be removed in udata 2.0',
            DeprecationWarning
        )
        org = org_id
    else:
        org = Organization.objects.get(pk=org_id)

    if isinstance(email, Member):  # TODO: Remove this branch in udata 2.0
        warnings.warn(
            'Using documents as task parameter is deprecated and '
            'will be removed in udata 2.0',
            DeprecationWarning
        )
        member = email
    else:
        member = next((m for m in org.members if m.user.email == email), None)

    subject = _('You are now a member of the organization "%(org)s"', org=org)
    mail.send(subject, member.user, 'new_member', org=org)


@notify_new_badge(Organization, CERTIFIED)
def notify_badge_certified(org_id):
    '''
    Send an email when a `CERTIFIED` badge is added to an `Organization`
    '''
    org = Organization.objects.get(pk=org_id)
    recipients = [member.user for member in org.members]
    subject = _(
        'Your organization "%(name)s" has been certified',
        name=org.name
    )
    mail.send(
        subject,
        recipients,
        'badge_added_certified',
        organization=org,
        badge=org.get_badge(CERTIFIED)
    )


@notify_new_badge(Organization, PUBLIC_SERVICE)
def notify_badge_public_service(org_id):
    '''
    Send an email when a `PUBLIC_SERVICE` badge is added to an `Organization`
    '''
    org = Organization.objects.get(pk=org_id)
    recipients = [member.user for member in org.members]
    subject = _(
        'Your organization "%(name)s" has been identified as public service',
        name=org.name
    )
    mail.send(
        subject,
        recipients,
        'badge_added_public_service',
        organization=org,
        badge=org.get_badge(PUBLIC_SERVICE)
    )
