# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from flask import abort

from flask.ext.security import current_user

from udata.api import api, API, marshal
from udata.models import Follow, FollowOrg, FollowDataset


class FollowAPI(API):
    model = Follow

    def post(self, id):
        if not current_user.is_authenticated():
            abort(401)
        follow, created = self.model.objects.get_or_create(follower=current_user.id, following=id)

        return '', 201 if created else 200

    def delete(self, id):
        if not current_user.is_authenticated():
            abort(401)
        follow = self.model.objects.get_or_404(follower=current_user.id, following=id, until=None)
        follow.until = datetime.now()
        follow.save()
        return '', 204


class FollowOrgAPI(FollowAPI):
    model = FollowOrg


class FollowDatasetAPI(FollowAPI):
    model = FollowDataset


api.add_resource(FollowAPI, '/follow/<id>/', endpoint=b'api.follow')
api.add_resource(FollowOrgAPI, '/follow/org/<id>/', endpoint=b'api.follow_org')
api.add_resource(FollowDatasetAPI, '/follow/dataset/<id>/', endpoint=b'api.follow_dataset')
