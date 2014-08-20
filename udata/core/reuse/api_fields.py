# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask.ext.restful import fields

from udata.api import api, pager

from udata.core.organization.api_fields import OrganizationField
from udata.core.dataset.api_fields import DatasetField

reuse_fields = api.model('Reuse', {
    'id': fields.String,
    'title': fields.String,
    'slug': fields.String,
    'type': fields.String,
    'featured': fields.Boolean,
    'description': fields.String,
    'image_url': fields.String,
    'created_at': fields.ISODateTime,
    'last_modified': fields.ISODateTime,
    'deleted': fields.ISODateTime,
    'datasets': fields.List(DatasetField),
    'organization': OrganizationField,
    'metrics': fields.Raw,
    'uri': fields.UrlFor('api.reuse', lambda o: {'reuse': o}),
    'page': fields.UrlFor('reuses.show', lambda o: {'reuse': o}),
})

reuse_page_fields = api.model('ReusePage', pager(reuse_fields))
