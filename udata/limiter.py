# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import current_app

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)


def init_app(app):
    limiter.init_app(app)


def comment_limit():
    return current_app.config.get('RATELIMIT_DISCUSSIONS')
