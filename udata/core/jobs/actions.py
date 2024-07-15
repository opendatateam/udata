import logging

from udata.tasks import celery

log = logging.getLogger(__name__)


def run(name, args, kwargs):
    args = args or []
    kwargs = dict(k.split() for k in kwargs) if kwargs else {}
    if name not in celery.tasks:
        log.error('Job %s not found', name)
    job = celery.tasks[name]
    log.info('Running job %s', name)
    job.run(*args, **kwargs)
    log.info('Job %s done', name)


def delay(name, args, kwargs):
    '''Run a job asynchronously'''
    args = args or []
    kwargs = dict(k.split() for k in kwargs) if kwargs else {}
    if name not in celery.tasks:
        log.error('Job %s not found', name)
    job = celery.tasks[name]
    log.info('Sending job %s', name)
    async_result = job.delay(*args, **kwargs)
    log.info('Job %s sended to workers', async_result.id)
