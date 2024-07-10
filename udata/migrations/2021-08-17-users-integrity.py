"""
Remove User db integrity problems, and Discussion.subject in the process
"""

import logging

import mongoengine

from udata.models import Discussion, Organization

log = logging.getLogger(__name__)


def migrate(db):
    log.info("Processing Discussion user references.")

    discussions = Discussion.objects(user__ne=None).no_cache().all()
    remove_count = 0
    modif_count = 0
    for discussion in discussions:
        try:
            discussion.user.id
            discussion.subject.id
        except mongoengine.errors.DoesNotExist:
            discussion.delete()
            remove_count += 1
            continue
        valid_messages = []
        messages = discussion.discussion
        for message in messages:
            try:
                message.posted_by.id
                valid_messages.append(message)
            except mongoengine.errors.DoesNotExist:
                pass
        if len(valid_messages) != len(messages):
            discussion.discussion = valid_messages
            discussion.save()
            modif_count += 1

    log.info(f"Modified {modif_count} Discussion objects, deleted {remove_count}")

    log.info("Processing Badges user references.")

    organizations = Organization.objects.filter(badges__0__exists=True)
    count = 0
    for org in organizations:
        for badge in org.badges:
            try:
                badge.created_by and badge.created_by.id
            except mongoengine.errors.DoesNotExist:
                count += 1
                badge.created_by = None
                org.save()

    log.info(f"Modified {count} badges")

    log.info("Processing Request user references.")

    organizations = Organization.objects.filter(requests__0__exists=True)
    count = 0
    for org in organizations:
        for request in org.requests:
            try:
                request.handled_by and request.handled_by.id
            except mongoengine.errors.DoesNotExist:
                count += 1
                request.handled_by = None
                org.save()

    log.info(f"Modified {count} requests")
