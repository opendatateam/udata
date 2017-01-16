import json
import logging
import time

import requests

from requests.status_codes import codes

from flask import current_app

log = logging.getLogger(__name__)

# See http://docs.python-requests.org/en/latest/user/advanced/#timeouts
# We are waiting 3 sec for the connexion and 9 for the response.
TIMEOUT = (3.1, 9.1)

DEFAULT_DELAY = 5
DEFAULT_RETRY = 10
CONNECTION_ERROR_MSG = 'Unable to reach the URL checker'

ERROR_LOG_MSG = 'Unable to connect to croquemort'
TIMEOUT_LOG_MSG = 'Timeout connectin to Croquemort'


def is_pending(response):
    if response.status_code == codes.not_found:
        return True
    try:
        return 'status' not in response.json()
    except ValueError:
        return True


def check_url(url, group=None):
    """Check the given URL against a Croquemort server.

    Return a tuple: (error, response).
    """
    CROQUEMORT = current_app.config.get('CROQUEMORT')
    if CROQUEMORT is None:
        return {'error': 'Check server not configured.'}, {}
    check_url = '{url}/check/one'.format(url=CROQUEMORT['url'])
    delay = CROQUEMORT.get('delay', DEFAULT_DELAY)
    retry = CROQUEMORT.get('retry', DEFAULT_RETRY)
    params = {'url': url, 'group': group}
    try:
        response = requests.post(check_url,
                                 data=json.dumps(params),
                                 timeout=TIMEOUT)
    except requests.Timeout:
        log.error(TIMEOUT_LOG_MSG, exc_info=True)
        return {}, codes.service_unavailable
    except requests.RequestException:
        log.error(ERROR_LOG_MSG, exc_info=True)
        return {}, codes.service_unavailable
    try:
        url_hash = response.json()['url-hash']
        retrieve_url = '{url}/url/{url_hash}'.format(
            url=CROQUEMORT['url'], url_hash=url_hash)
    except ValueError:
        return {}, codes.service_unavailable
    try:
        response = requests.get(retrieve_url, params=params, timeout=TIMEOUT)
    except requests.Timeout:
        log.error(TIMEOUT_LOG_MSG, exc_info=True)
        return {}, codes.service_unavailable
    except requests.RequestException:
        log.error(ERROR_LOG_MSG, exc_info=True)
        return {}, codes.service_unavailable
    attempts = 0
    while is_pending(response):
        if attempts >= retry:
            msg = ('We were unable to retrieve the URL after'
                   ' {attempts} attempts.').format(attempts=attempts)
            return {'error': msg}, {}
        try:
            response = requests.get(retrieve_url,
                                    params=params,
                                    timeout=TIMEOUT)
        except requests.Timeout:
            log.error(TIMEOUT_LOG_MSG, exc_info=True)
            return {}, codes.service_unavailable
        except requests.RequestException:
            log.error(ERROR_LOG_MSG, exc_info=True)
            return {}, codes.service_unavailable
        time.sleep(delay)
        attempts += 1
    return {}, response.json()


def check_url_from_cache(url, group=None):
    """Check the given URL against the cache of a Croquemort server.

    Return a tuple: (error, response).
    """
    CROQUEMORT = current_app.config.get('CROQUEMORT')
    if CROQUEMORT is None:
        return {'error': 'Check server not configured.'}, {}
    retrieve_url = '{url}/url'.format(url=CROQUEMORT['url'])
    try:
        response = requests.get(retrieve_url,
                                params={'url': url, 'group': group},
                                timeout=TIMEOUT)
    except requests.Timeout:
        log.error(TIMEOUT_LOG_MSG, exc_info=True)
        return {'error': CONNECTION_ERROR_MSG}, {}
    except requests.RequestException:
        log.error(ERROR_LOG_MSG, exc_info=True)
        return {'error': CONNECTION_ERROR_MSG}, {}
    if response.status_code == codes.not_found:
        return {'error': 'URL {url} not found'.format(url=url)}, {}
    else:
        return {}, response.json()


def check_url_from_group(group):
    """Check the given group against the cache of a Croquemort server.

    Return a tuple: (error, response).
    """
    CROQUEMORT = current_app.config.get('CROQUEMORT')
    if CROQUEMORT is None:
        return {'error': 'Check server not configured.'}, {}
    retrieve_url = '{url}/group'.format(url=CROQUEMORT['url'])
    try:
        response = requests.get(retrieve_url,
                                params={'group': group},
                                timeout=TIMEOUT)
    except requests.Timeout:
        log.error(TIMEOUT_LOG_MSG, exc_info=True)
        return {'error': CONNECTION_ERROR_MSG}, {}
    except requests.RequestException:
        log.error(ERROR_LOG_MSG, exc_info=True)
        return {'error': CONNECTION_ERROR_MSG}, {}
    if response.status_code == codes.not_found:
        return {'error': 'Group {group} not found'.format(group=group)}, {}
    else:
        return {}, response.json()
