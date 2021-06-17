import requests

from flask import current_app
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from udata.tasks import get_logger, task
from udata.features.webhooks.utils import sign

log = get_logger(__name__)

DEFAULT_RETRIES = 3
DEFAULT_BACKOFF = 10
DEFAULT_TIMEOUT = 30


def dispatch(event, payload):
    webhooks = current_app.config['WEBHOOKS']
    if not webhooks:
        return
    for wh in webhooks:
        _dispatch.delay(event, payload, wh)


@task
def _dispatch(event, payload, wh):
    url = wh['url']
    log.debug(f'Dispatching {event} to {url}')

    retry_strategy = Retry(
        total=wh.get('max_retries', DEFAULT_RETRIES),
        status_forcelist=[404, 429, 500, 502, 503, 504],
        method_whitelist=['POST'],
        backoff_factor=wh.get('backoff_factor', DEFAULT_BACKOFF),
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    http = requests.Session()
    http.mount('https://', adapter)
    http.mount('http://', adapter)

    payload = {
        'event': event,
        'payload': payload,
    }
    r = http.post(url, json=payload, headers={
        'x-hook-signature': sign(payload, wh.get('secret'))
    }, timeout=wh.get('timeout', DEFAULT_TIMEOUT))

    if not r.ok:
        log.error(f'Failed dispatching webhook {event} to {url}')
