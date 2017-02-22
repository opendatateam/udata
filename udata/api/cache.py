# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import binascii
import httplib
import os
from datetime import datetime
from functools import wraps

from flask import request, make_response

from udata.app import cache

ONE_MINUTE = 60
ONE_HOUR = ONE_MINUTE * 60
ONE_DAY = ONE_HOUR * 24
ONE_WEEK = ONE_DAY * 7
ONE_MONTH = ONE_DAY * 30
ONE_YEAR = ONE_DAY * 365


def cache_page(class_instance, check_serverside=True, personal=False,
               client_timeout=0, server_timeout=ONE_HOUR, key='view-cache%s',
               x_cache_header=True, serializer=lambda a: a):
    """An attempt to make the ultimate Flask cache decorator.

    Differs from the official Flask Caching Decorator
    http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/#caching-decorator
    by dealing with appropriated headers for server AND client-side caches.

    Key points:
    * Generates the cache key using the full path (using the query string).
    * Uses `Cache-Control`, `ETag` and `Last-Modified` headers.
    * Respects browser's hard-refresh.

    Parameters:
    * `check_serverside`: either the client verifies with the server if
      its cached versions are still valid or not.
    * `personal`: set to `True` if the response contains sensitive
      informations only pertinent for a given user.
    * `client_timeout`: time in seconds before the client considers the
      cache as being invalid.
    * `server_timeout`: time in seconds before the server considers the
      cache as being invalid.
    * `key`: you can customize the cache key, it must contains `%s`
      which will be replaced by the full path (including query string).
    * `x_cache_header`: either put a `X-Cache` header to know which
      cache is being hit or not. Useful to debug but not required.
    * `serializer`: if the response from your view needs to be
      serialized prior to be converted to a Flask Response object.

    Inspirations:
    * http://codereview.stackexchange.com/questions/147038/↩︎
      improving-the-flask-cache-decorator
    * https://gist.github.com/glenrobertson/954da3acec84606885f5

    Resources:
    * https://jakearchibald.com/2016/caching-best-practices/
    * https://developers.google.com/web/fundamentals/performance/↩︎
      optimizing-content-efficiency/http-caching

    Image:
    * https://developers.google.com/web/fundamentals/performance/↩︎
      optimizing-content-efficiency/images/http-cache-decision-tree.png
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Before you think the logic is reversed, read Jake's article.
            cache_policy = check_serverside and 'no-cache' or 'must-revalidate'
            if personal:
                cache_policy += ', private'
            else:
                cache_policy += ', public'
            cache_policy += ', max-age={}'.format(client_timeout)
            headers = {}
            headers['Cache-Control'] = cache_policy
            client_etag = request.headers.get('If-None-Match')
            cache_key = key % request.full_path  # Include querystring.
            resp = cache.get(cache_key)
            cache_control = request.headers.get('Cache-Control', '')
            # Respect the hard-refresh of the browser.
            if resp is not None and cache_control != 'no-cache':
                if x_cache_header:
                    headers['X-Cache'] = 'HIT from Server'
                cached_etag = resp.headers.get('ETag')
                if client_etag and cached_etag and client_etag == cached_etag:
                    if x_cache_header:
                        headers['X-Cache'] = 'HIT from Client'
                    headers['Last-Modified'] = \
                        resp.headers.get('Last-Modified')
                    resp = make_response('', httplib.NOT_MODIFIED)
            else:
                resp = make_response(serializer(func(*args, **kwargs)))
                ok_status = resp.status_code == httplib.OK
                if ok_status and request.method in ['GET', 'HEAD']:
                    if x_cache_header:
                        headers['X-Cache'] = 'MISS'
                    # Add headers to the response object so they get cached.
                    # Alternative algorithm: hex(random.getrandbits(32))
                    resp.headers.add('ETag', binascii.hexlify(os.urandom(4)))
                    resp.headers.add('Last-Modified', str(datetime.utcnow()))
                    cache.set(cache_key, resp, timeout=server_timeout)
                else:
                    if x_cache_header:
                        headers['X-Cache'] = 'NOCACHE'
            resp.headers.extend(headers)
            return resp
        return wrapper
    return decorator
