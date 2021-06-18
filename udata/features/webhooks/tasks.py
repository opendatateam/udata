import json
import requests

from flask import current_app

from udata.tasks import get_logger, task
from udata.features.webhooks.utils import sign

log = get_logger(__name__)

DEFAULT_RETRIES = 3
DEFAULT_BACKOFF = 10
DEFAULT_TIMEOUT = 30


def dispatch(event, payload):
    webhooks = current_app.config['WEBHOOKS']
    for wh in webhooks:
        _dispatch.delay(event, payload, wh)


@task(
    autoretry_for=(requests.exceptions.HTTPError,), exponential_backoff=DEFAULT_BACKOFF,
    retry_kwargs={'max_retries': DEFAULT_RETRIES}, retry_jitter=True,
)
def _dispatch(event, payload, wh):
    url = wh['url']
    log.debug(f'Dispatching {event} to {url}')

    payload = payload if not type(payload) is str else json.loads(payload)
    print('payload ----> ', payload)
    payload = {
        'event': event,
        'payload': payload,
    }

    print('_dispatch', url)
    r = requests.post(url, json=payload, headers={
        'x-hook-signature': sign(payload, wh.get('secret'))
    }, timeout=DEFAULT_TIMEOUT)

    if not r.ok:
        log.error(f'Failed dispatching webhook {event} to {url}')

    r.raise_for_status()
