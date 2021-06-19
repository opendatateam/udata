import json

from udata.core.discussions.signals import (
    on_new_discussion, on_new_discussion_comment, on_discussion_closed,
)

from udata.features.webhooks.tasks import dispatch
from udata.models import Dataset, Organization, Reuse

# TODO: (mvp)
# - organisation
# - community resource
# - reuse


@Dataset.on_create.connect
def on_dataset_create(dataset):
    # TODO: emit a private signal somehow (or just rename it to draft)
    dispatch('datagouvfr.dataset.created', dataset.to_json())


@Dataset.on_delete.connect
def on_dataset_delete(dataset):
    dispatch('datagouvfr.dataset.deleted', dataset.to_json())


@Dataset.on_update.connect
def on_dataset_update(dataset):
    dispatch('datagouvfr.dataset.updated', dataset.to_json())


@on_new_discussion.connect
def on_new_discussion(discussion):
    dispatch('datagouvfr.discussion.created', discussion.to_json())


@on_new_discussion_comment.connect
def on_new_discussion_comment(discussion, message=None):
    dispatch('datagouvfr.discussion.commented', {
        'message_id': message,
        'discussion': json.loads(discussion.to_json()),
    })


@on_discussion_closed.connect
def on_discussion_closed(discussion, message=None):
    dispatch('datagouvfr.discussion.closed', {
        'message_id': message,
        'discussion': json.loads(discussion.to_json()),
    })


@Organization.on_create.connect
def on_organization_created(organization):
    dispatch('datagouvfr.organization.created', organization.to_json())


@Organization.on_update.connect
def on_organization_updated(organization):
    dispatch('datagouvfr.organization.updated', organization.to_json())


@Reuse.on_create.connect
def on_reuse_created(reuse):
    dispatch('datagouvfr.reuse.created', reuse.to_json())


@Reuse.on_update.connect
def on_reuse_updated(reuse):
    dispatch('datagouvfr.reuse.updated', reuse.to_json())
