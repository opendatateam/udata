import logging

from udata.core.dataset.models import Dataset

from . import tasks  # noqa: F401 — registers Celery tasks
from .tasks import _set_extras

log = logging.getLogger(__name__)


def _should_push(resource):
    return (
        resource is not None
        and resource.format
        and resource.format.lower() == "gpkg"
        and not resource.extras.get("geopf_push_status")
    )


def _queue(document, resource_id):
    resource = next((r for r in document.resources if str(r.id) == str(resource_id)), None)
    if _should_push(resource):
        log.info("geopf: queuing push dataset=%s resource=%s", document.id, resource_id)
        result = tasks.push_resource_to_geopf.delay(str(document.id), str(resource_id))
        _set_extras(
            document, resource, {"geopf_push_status": "pending", "geopf_push_task_id": result.id}
        )


@Dataset.on_resource_added.connect
def on_resource_added(sender, document, **kwargs):
    _queue(document, str(kwargs["resource_id"]))


def init_app(app):
    log.info("geopf: plugin init_app called")
