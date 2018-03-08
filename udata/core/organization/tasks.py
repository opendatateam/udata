# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata import mail
from udata.i18n import lazy_gettext as _
from udata.models import Organization, Follow, Activity, Metrics, Dataset
from udata.search import reindex
from udata.tasks import job, task, get_logger

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
def notify_membership_request(org, request):
    recipients = [m.user for m in org.by_role('admin')]
    mail.send(
        _('New membership request'), recipients, 'membership_request',
        org=org, request=request)


@task(route='high.mail')
def notify_membership_response(org, request):
    if request.status == 'accepted':
        subject = _('You are now a member of the organization "%(org)s"',
                    org=org)
        template = 'new_member'
    else:
        subject, template = _('Membership refused'), 'membership_refused'
    mail.send(subject, request.user, template, org=org, request=request)


@task
def notify_new_member(org, member):
    subject = _('You are now a member of the organization "%(org)s"', org=org)
    mail.send(subject, member.user, 'new_member', org=org)
