# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from flask.ext.security import current_user

from udata.api import api, API
from udata.models import FollowOrg, FollowDataset, Follow, FollowReuse, FollowUser

from .signals import on_unfollow


ns = api.namespace('follow', 'Follower/Followee related operations')


class FollowAPI(API):
    '''
    Base Follow Model API.
    '''
    model = Follow

    @api.secure
    def post(self, id):
        '''Follow a given object'''
        follow, created = self.model.objects.get_or_create(follower=current_user.id, following=id, until=None)
        count = self.model.objects.followers(id).count()

        return {'followers': count}, 201 if created else 200

    @api.secure
    def delete(self, id):
        '''Unfollow a given object'''
        follow = self.model.objects.get_or_404(follower=current_user.id, following=id, until=None)
        follow.until = datetime.now()
        follow.save()
        on_unfollow.send(follow)
        count = self.model.objects.followers(id).count()
        return {'followers': count}, 200


@ns.resource('/user/<id>/', endpoint='follow_user')
class FollowUserAPI(FollowAPI):
    model = FollowUser

    @api.secure
    def post(self, id):
        if id == str(current_user.id):
            api.abort(403, "You can't follow yourself")
        return super(FollowUserAPI, self).post(id)


@ns.resource('/organization/<id>/', endpoint='follow_organization')
class FollowOrgAPI(FollowAPI):
    model = FollowOrg


@ns.resource('/dataset/<id>/', endpoint='follow_dataset')
class FollowDatasetAPI(FollowAPI):
    model = FollowDataset


@ns.resource('/reuse/<id>/', endpoint='follow_reuse')
class FollowReuseAPI(FollowAPI):
    model = FollowReuse
