import json
import requests

from flask import current_app

from udata.tasks import get_logger, task
from udata.features.webhooks.utils import sign

log = get_logger(__name__)

# number of time we should retry
DEFAULT_RETRIES = 5
# exponentional backoff factor (in seconds)
# https://docs.celeryproject.org/en/v4.3.0/userguide/tasks.html#Task.retry_backoff
DEFAULT_BACKOFF = 30
# timeout for a single request
DEFAULT_TIMEOUT = 30


def dispatch(event, payload):
    webhooks = current_app.config['WEBHOOKS']
    for wh in webhooks:
        _dispatch.delay(event, payload, wh)


@task(
    autoretry_for=(requests.exceptions.HTTPError,), retry_backoff=DEFAULT_BACKOFF,
    retry_kwargs={'max_retries': DEFAULT_RETRIES}
)
def _dispatch(event, event_payload, wh):
    url = wh['url']
    log.debug(f'Dispatching {event} to {url}')

    event_payload = event_payload if not type(event_payload) is str else json.loads(event_payload)
    payload = {
        'event': event,
        'payload': event_payload,
    }

    r = requests.post(url, json=payload, headers={
        'x-hook-signature': sign(payload, wh.get('secret'))
    }, timeout=DEFAULT_TIMEOUT)

    if not r.ok:
        log.error(f'Failed dispatching webhook {event} to {url}')

    r.raise_for_status()
