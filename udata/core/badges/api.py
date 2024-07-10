from udata.api import api

from .forms import badge_form


def add(obj):
    """
    Handle a badge add API.

    - Expecting badge_fieds as payload
    - Return the badge as payload
    - Return 200 if the badge is already
    - Return 201 if the badge is added
    """
    Form = badge_form(obj.__class__)
    form = api.validate(Form)
    kind = form.kind.data
    badge = obj.get_badge(kind)
    if badge:
        return badge
    else:
        return obj.add_badge(kind), 201


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
