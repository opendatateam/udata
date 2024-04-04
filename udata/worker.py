from udata.app import create_app, standalone

_app = standalone(create_app())

from udata.tasks import celery  # noqa
