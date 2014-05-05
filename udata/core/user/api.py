# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import abort, url_for
from flask.ext.security import current_user

from udata.api import api, ModelAPI, SingleObjectAPI, API, marshal, fields
from udata.models import Dataset, Reuse, Organization, User
from udata.forms import UserProfileForm


user_fields = {
    'id': fields.String,
    'slug': fields.String,
    'email': fields.String,
    'first_name': fields.String,
    'last_name': fields.String,
    'avatar_url': fields.String,
    'website': fields.String,
    'about': fields.String,
}


class UserField(fields.Raw):
    def format(self, user):
        return {
            'id': str(user.id),
            # 'uri': url_for('api.organization', slug=organization.slug, _external=True),
            'page': url_for('users.show', user=user, _external=True),
        }


class MeAPI(ModelAPI):
    model = User
    form = UserProfileForm
    fields = user_fields


class StarredModelAPI(SingleObjectAPI, API):
    def post(self, slug):
        if not current_user.is_authenticated():
            abort(401)
        obj = self.get_or_404(slug=slug)
        key = obj.__class__.__name__.lower()
        starred = getattr(current_user, 'starred_{0}s'.format(key))

        if obj not in starred:
            starred.append(obj)
            current_user.save()
            obj.on_star.send(obj)
            return marshal(current_user, user_fields), 201
        else:
            return marshal(current_user, user_fields)

    def delete(self, slug):
        if not current_user.is_authenticated():
            abort(401)
        obj = self.get_or_404(slug=slug)
        key = obj.__class__.__name__.lower()
        starred = getattr(current_user, 'starred_{0}s'.format(key))
        starred.remove(obj)
        current_user.save()
        obj.on_unstar.send(obj)
        return marshal(current_user, user_fields), 204


class StarredDatasetsAPI(StarredModelAPI):
    model = Dataset


class StarredReusesAPI(StarredModelAPI):
    model = Reuse


class StarredOrganizationsAPI(StarredModelAPI):
    model = Organization


api.add_resource(MeAPI, '/me/', endpoint=b'api.me')
api.add_resource(StarredDatasetsAPI, '/me/starred_datasets/<string:slug>', endpoint=b'api.starred_datasets')
api.add_resource(StarredReusesAPI, '/me/starred_reuses/<string:slug>', endpoint=b'api.starred_reuses')
api.add_resource(StarredOrganizationsAPI, '/me/starred_organizations/<string:slug>', endpoint=b'api.starred_organizations')
