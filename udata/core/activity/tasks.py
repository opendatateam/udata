import logging

from udata.models import db, User, Organization
from udata.tasks import task, celery

from .signals import new_activity

log = logging.getLogger(__name__)


@new_activity.connect
def delay_activity(cls, related_to, actor, organization=None):
    emit_activity.delay(
        cls.__name__,
        str(actor.id),
        related_to_cls=related_to.__class__.__name__,
        related_to_id=str(related_to.id),
        organization_id=str(organization.id) if organization else None,
    )


@task
def emit_activity(classname, actor_id, related_to_cls, related_to_id,
                  organization_id=None):
    log.debug('Emit new activity: %s %s %s %s %s',
              classname, actor_id, related_to_cls,
              related_to_id, organization_id)
    cls = db.resolve_model(classname)
    actor = User.objects.get(pk=actor_id)
    related_to = db.resolve_model(related_to_cls).objects.get(pk=related_to_id)
    if organization_id:
        organization = Organization.objects.get(pk=organization_id)
    else:
        organization = None
    cls.objects.create(actor=actor, related_to=related_to,
                       organization=organization)
