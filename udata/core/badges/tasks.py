from typing import Any

from mongoengine.base import TopLevelDocumentMetaclass

from udata.tasks import get_logger, job, task

from .signals import on_badge_added

log = get_logger(__name__)

_badge_jobs: dict[tuple[TopLevelDocumentMetaclass, str], Any] = {}


def notify_new_badge(cls, kind):
    def wrapper(func):
        t = task(func)

        def call_task(sender, **kwargs):
            if isinstance(sender, cls) and kwargs.get("kind") == kind:
                t.delay(str(sender.pk))

        on_badge_added.connect(call_task, weak=False)
        return t

    return wrapper


def register(model: TopLevelDocumentMetaclass, badge: str):
    """Register a job to update some badge"""

    def inner(func):
        _badge_jobs[(model, badge)] = func
        return func

    return inner


def get_badge_job(model, badge):
    return _badge_jobs.get((model, badge))


@job(name="update-badges")
def update_badges(self, badges: list[str] = []) -> None:
    from udata.core.dataservices.models import Dataservice
    from udata.models import Dataset, Organization, Reuse

    for model in [Dataset, Reuse, Organization, Dataservice]:
        for badge in model.__badges__:
            if badges and badge not in badges:
                continue
            if adapter := get_badge_job(model, badge):
                log.info(f"Running {model.__name__} {badge} job")
                adapter()
