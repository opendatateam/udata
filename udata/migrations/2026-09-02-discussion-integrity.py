"""
Remove Discussion integrity problems
"""

import logging

import mongoengine

from udata.models import Discussion

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Processing Discussion references.")

    # Delete discussions for orgs with reference errors
    discussion_count = 0
    discussions = Discussion.objects(organization__ne=None).no_cache().all()
    for discussion in discussions:
        try:
            discussion.organization.id
        except mongoengine.errors.DoesNotExist:
            discussion_count += 1
            discussion.delete()

    # Unset posted_by_organization in messages for orgs with reference errors
    message_count = 0
    discussions = Discussion.objects(discussion__posted_by_organization__ne=None).no_cache().all()
    for discussion in discussions:
        modified = False
        for message in discussion.discussion:
            try:
                message.posted_by_organization.id
            except mongoengine.errors.DoesNotExist:
                message_count += 1
                message.posted_by_organization = None
                modified = True
        if modified:
            discussion.save()

    # Unset closed_by_organization for orgs with reference errors
    closed_count = 0
    discussions = Discussion.objects(closed_by_organization__ne=None).no_cache().all()
    for discussion in discussions:
        try:
            discussion.closed_by_organization.id
        except mongoengine.errors.DoesNotExist:
            closed_count += 1
            discussion.closed_by_organization = None
            discussion.save()

    log.info(f"Deleted {discussion_count} Discussion objects")
    log.info(f"Unset {message_count} posted_by_organization in Discussion messages")
    log.info(f"Unset {closed_count} closed_by_organization in Discussion objects")
