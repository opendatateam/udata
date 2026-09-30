import logging
from collections.abc import Iterable

from udata.models import Organization, db
from udata.tasks import task

from .signals import new_activity

log = logging.getLogger(__name__)


@new_activity.connect
def delay_activity(cls, related_to, actor, organization=None, changes=None, extras=None, **kwargs):
    emit_activity.delay(
        cls.__name__,
        str(actor.id),
        actor_cls=actor.__class__.__name__,
        related_to_cls=related_to.__class__.__name__,
        related_to_id=str(related_to.id),
        organization_id=str(organization.id) if organization else None,
        changes=changes,
        extras=extras,
    )


@task
def emit_activity(
    classname,
    actor_id,
    related_to_cls,
    related_to_id,
    organization_id=None,
    changes=None,
    extras=None,
    # Defaulted, and last, so the tasks queued before this parameter existed still
    # resolve their actor once the workers restart.
    actor_cls="User",
):
    log.debug(
        "Emit new activity: %s %s %s %s %s %s %s %s",
        classname,
        actor_cls,
        actor_id,
        related_to_cls,
        related_to_id,
        organization_id,
        ", ".join(changes) if changes and isinstance(changes, Iterable) else "",
        extras,
    )
    cls = db.resolve_model(classname)
    actor = db.resolve_model(actor_cls).objects.get(pk=actor_id)
    related_to = db.resolve_model(related_to_cls).objects.get(pk=related_to_id)
    if organization_id:
        organization = Organization.objects.get(pk=organization_id)
    else:
        organization = None
    cls.objects.create(
        actor=actor,
        related_to=related_to,
        organization=organization,
        changes=changes,
        extras=extras,
    )
