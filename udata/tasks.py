import logging
from importlib import import_module
from importlib.metadata import entry_points

from celery import Celery, Task
from celery.utils.log import get_task_logger

log = logging.getLogger(__name__)


class ContextTask(Task):
    abstract = True
    schedulable = None
    current_app = None
    route = None
    default_queue = None
    default_routing_key = None

    def __call__(self, *args, **kwargs):
        with self.current_app.app_context():
            return super().__call__(*args, **kwargs)


class JobTask(ContextTask):
    abstract = True
    default_queue = "low"

    @property
    def log(self):
        return get_task_logger(self.name)


celery = Celery(task_cls=ContextTask)


def router(name, args, kwargs, options, task=None, **kw):
    """
    A celery router using the predeclared :class:`ContextTask`
    attributes (`router` or `default_queue` and/or `default routing_key`).
    """
    # Fetch task by name if necessary
    task = task or celery.tasks.get(name)
    if not task:
        return
    # Single route param override everything
    if task.route:
        queue = task.route.split(".", 1)[0]
        return {"queue": queue, "routing_key": task.route}
    # queue parameter, routing_key computed if not present
    if task.default_queue:
        key = task.default_routing_key
        key = key or f"{task.default_queue}.{task.name}"
        return {"queue": task.default_queue, "routing_key": key}
    # only routing_key, queue should not be returned to fallback on default
    elif task.default_routing_key:
        return {"routing_key": task.default_routing_key}


def task(*args, **kwargs):
    for arg in "queue", "routing_key":
        if arg in kwargs:
            kwargs[f"default_{arg}"] = kwargs.pop(arg)
    return celery.task(*args, **kwargs)


def job(name, **kwargs):
    """A shortcut decorator for declaring jobs"""
    return task(name=name, schedulable=True, base=JobTask, bind=True, **kwargs)


def as_task_param(obj):
    """Pass a document as task parameter"""
    return obj.__class__.__name__, (obj.pk if isinstance(obj.pk, str) else str(obj.pk))


def get_logger(name):
    logger = get_task_logger(name)
    return logger


def connect(signal, *args, **kwargs):
    by_id = kwargs.pop("by_id", False)

    def wrapper(func):
        t = task(func, *args, **kwargs)

        def call_task(item, **kwargs):
            t.delay(str(item.pk) if by_id else item, **kwargs)

        signal.connect(call_task, weak=False)
        return t

    return wrapper


@job("test-log")
def log_test(self):
    self.log.debug("This is a DEBUG message")
    self.log.info("This is an INFO message")
    self.log.warning("This is a WARNING message")
    self.log.error("This is a ERROR message")


@job("test-low-queue", queue="low")
@job("test-default-queue", queue="default")
@job("test-high-queue", queue="high")
def queue_test(self, raises=False):
    """
    An empty task to test the queues.
    Set raise to True if you want a notification (ie. Sentry)
    """
    self.log.info("Just a test task")
    if raises:
        raise RuntimeError("Test task processing")


@job("test-error")
def error_test(self):
    self.log.info("There should be an error soon")
    raise RuntimeError("There is an error")


def schedulables():
    return [task for task in celery.tasks.values() if task.schedulable]


def init_app(app):
    celery.main = app.import_name

    celery.conf.update(
        **{
            k.replace("CELERY_", "").lower(): v
            for k, v in app.config.items()
            if k.startswith("CELERY_")
        }
    )

    ContextTask.current_app = app

    # Load core tasks: importing a module registers its tasks
    for module in (
        "udata.core.metrics.tasks",
        "udata.core.tags.tasks",
        "udata.core.activity.tasks",
        "udata.core.dataservices.tasks",
        "udata.core.dataset.doi",
        "udata.core.dataset.tasks",
        "udata.core.dataset.transport",
        "udata.core.dataset.recommendations",
        "udata.core.spatial.tasks",
        "udata.core.topic.tasks",
        "udata.core.reuse.tasks",
        "udata.core.user.tasks",
        "udata.core.organization.tasks",
        "udata.core.discussions.tasks",
        "udata.core.badges.tasks",
        "udata.core.storages.tasks",
        "udata.core.sitemap.tasks",
        "udata.core.visualizations.tasks",
        "udata.features.notifications.tasks",
        "udata.notifications.tchap",
        "udata.harvest.tasks",
        "udata.db.tasks",
    ):
        import_module(module)

    for ep in entry_points(group="udata.tasks"):
        ep.load()

    return celery
