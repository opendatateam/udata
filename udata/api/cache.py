# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import httplib
from datetime import datetime
from functools import wraps

from flask import request, make_response as flask_make_response
from werkzeug.datastructures import Headers, ResponseCacheControl

from udata.app import cache

ZERO = 0
ONE_MINUTE = 60
ONE_HOUR = ONE_MINUTE * 60
ONE_DAY = ONE_HOUR * 24
ONE_WEEK = ONE_DAY * 7
ONE_MONTH = ONE_DAY * 30
ONE_YEAR = ONE_DAY * 365


def cache_page(class_instance=None, check_serverside=True, personal=False,
               client_timeout=ZERO, server_timeout=ONE_HOUR,
               key_pattern='cache%s', make_response=flask_make_response):
    """An attempt to make the ultimate Flask cache decorator.

    Differs from the official Flask Caching Decorator
    http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/#caching-decorator
    by dealing with appropriated headers for server AND client-side caches.

    Key points:
    * Generates the cache key using the full path (using the query string).
    * Uses `Cache-Control`, `ETag` and `Last-Modified` headers.
    * Respects browser's hard-refresh.

    Parameters:
    * `class_instance`: allows the decorator to be applied on a class method.
    * `check_serverside`: either the client verifies with the server if
      its cached versions are still valid or not.
    * `personal`: set to `True` if the response contains sensitive
      informations only pertinent for a given user.
    * `client_timeout`: time in seconds before the client considers the
      cache as being invalid.
    * `server_timeout`: time in seconds before the server considers the
      cache as being invalid.
    * `key_pattern`: you can customize the cache key, it can be either
      a callable or a string. If it contains `%s`, the placeholder will
      be replaced by the full path (including query string).
    * `make_response`: a way to override the default Flask way of
      creating a response object.

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
    def _generate_cache_control():
        cache_control = ResponseCacheControl()
        # Before you think the logic is reversed, read Jake's article.
        if check_serverside:
            cache_control.no_cache = True
        else:
            cache_control.must_revalidate = True
        if personal:
            cache_control.private = True
        else:
            cache_control.public = True
        cache_control.max_age = client_timeout
        return cache_control

    def _generate_cache_key(str_or_callable):
        if callable(str_or_callable):
            return str_or_callable()
        else:
            try:
                # Include querystring with `full_path`.
                return str_or_callable % request.full_path
            except TypeError:
                return str_or_callable

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            headers = Headers()
            headers.add('Cache-Control', _generate_cache_control())
            cache_key = _generate_cache_key(key_pattern)
            resp = cache.get(cache_key)
            # Respect the hard-refresh of the browser.
            if resp and not request.cache_control.no_cache:
                headers.add('X-Cache', 'HIT from Server')
                etag, is_weak = resp.get_etag()
                if request.if_none_match.contains(etag):
                    headers.add('X-Cache', 'HIT from Client')
                    resp = make_response('', httplib.NOT_MODIFIED)
            else:
                result = func(*args, **kwargs)
                resp = make_response(result)
                if (request.method in ('GET', 'HEAD') and
                        resp.status_code == httplib.OK):
                    headers.add('X-Cache', 'MISS')
                    resp.add_etag()
                    resp.last_modified = datetime.utcnow()
                    cache.set(cache_key, resp, timeout=server_timeout)
                else:
                    headers.add('X-Cache', 'NOCACHE')
            resp.headers.extend(headers)
            return resp
        return wrapper
    return decorator
