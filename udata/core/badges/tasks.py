from udata.tasks import get_logger, task

from .signals import on_badge_added

log = get_logger(__name__)


def notify_new_badge(cls, kind):
    def wrapper(func):
        t = task(func)

        def call_task(sender, **kwargs):
            if isinstance(sender, cls) and kwargs.get("kind") == kind:
                t.delay(str(sender.pk))

        on_badge_added.connect(call_task, weak=False)
        return t

    return wrapper
