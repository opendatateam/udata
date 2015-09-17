import json
import time

import requests
from flask import current_app


def check_url(url, group=None):
    """Check the given URL against a Croquemort server.

    Return a tuple: (error, response).
    """
    CROQUEMORT = current_app.config.get('CROQUEMORT')
    if CROQUEMORT is None:
        return {'error': 'Check server not configured.'}, {}
    check_url = '{url}/check/one'.format(url=CROQUEMORT['url'])
    delay = CROQUEMORT['delay']
    retry = CROQUEMORT['retry']
    response = requests.post(check_url,
                             data=json.dumps({'url': url, 'group': group}))
    url_hash = response.json()['url-hash']
    retrieve_url = '{url}/url/{url_hash}'.format(
        url=CROQUEMORT['url'], url_hash=url_hash)
    response = requests.get(retrieve_url, params={'url': url, 'group': group})
    attempts = 0
    while response.status_code == 404 or 'status' not in response.json():
        if attempts >= retry:
            msg = ('We were unable to retrieve the URL after'
                   ' {attempts} attempts.').format(attempts=attempts)
            return {'error': msg}, {}
        response = requests.get(retrieve_url, params={'url': url})
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
    response = requests.get(retrieve_url, params={'url': url, 'group': group})
    if response.status_code == 404:
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
    response = requests.get(retrieve_url, params={'group': group})
    if response.status_code == 404:
        return {'error': 'Group {group} not found'.format(group=group)}, {}
    else:
        return {}, response.json()
