from flask import request

from udata.api import api
from udata.api_fields import patch

from .models import Badge


def add(obj):
    badge = patch(Badge(), request)
    existing = obj.get_badge(badge.kind)
    if existing:
        return existing
    return obj.add_badge(badge.kind), 201


def remove(obj, kind):
    """
    Handle badge removal API

    - Returns 404 if the badge for this kind is absent
    - Returns 204 on success
    """
    if not obj.get_badge(kind):
        api.abort(404, "Badge does not exists")
    obj.remove_badge(kind)
    return "", 204
