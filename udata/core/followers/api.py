# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from flask.ext.security import current_user

from udata.api import api, API
from udata.models import Follow


@api.doc(notes='Returns the number of followers left after the operation')
class FollowAPI(API):
    '''
    Base Follow Model API.
    '''
    model = Follow

    @api.secure
    def post(self, id):
        '''Follow an object given its ID'''
        follow, created = self.model.objects.get_or_create(follower=current_user.id, following=id, until=None)
        count = self.model.objects.followers(id).count()

        return {'followers': count}, 201 if created else 200

    @api.secure
    def delete(self, id):
        '''Unfollow an object given its ID'''
        follow = self.model.objects.get_or_404(follower=current_user.id, following=id, until=None)
        follow.until = datetime.now()
        follow.save()
        count = self.model.objects.followers(id).count()
        return {'followers': count}, 200
