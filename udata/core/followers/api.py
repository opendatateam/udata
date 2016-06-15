# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from flask import current_app, request
from flask_security import current_user

from udata import tracking
from udata.api import api, API, fields
from udata.models import Follow
from udata.core.user.api_fields import user_ref_fields

from .signals import on_new_follow


follow_fields = api.model('Follow', {
    'id': fields.String(
        description='The follow object technical ID', readonly=True),
    'follower': fields.Nested(
        user_ref_fields, description='The follower', readonly=True),
    'since': fields.ISODateTime(
        description='The date from which the user started following',
        readonly=True)
})

follow_page_fields = api.model('FollowPage', fields.pager(follow_fields))

parser = api.parser()
parser.add_argument(
    'page', type=int, default=1, location='args', help='The page to fetch')
parser.add_argument(
    'page_size', type=int, default=20, location='args',
    help='The page size to fetch')

NOTE = 'Returns the number of followers left after the operation'


class FollowAPI(API):
    '''
    Base Follow Model API.
    '''
    model = None

    @api.doc('list_followers', parser=parser)
    @api.marshal_with(follow_page_fields)
    def get(self, id):
        '''List all followers for a given object'''
        args = parser.parse_args()
        model = self.model.objects.only('id').get_or_404(id=id)
        qs = Follow.objects(following=model, until=None)
        return qs.paginate(args['page'], args['page_size'])

    @api.secure
    @api.doc('follow', description=NOTE)
    def post(self, id):
        '''Follow an object given its ID'''
        model = self.model.objects.only('id').get_or_404(id=id)
        follow, created = Follow.objects.get_or_create(
            follower=current_user.id, following=model, until=None)
        count = Follow.objects.followers(model).count()
        if not current_app.config['TESTING']:
            tracking.send_signal(on_new_follow, request, current_user)
        return {'followers': count}, 201 if created else 200

    @api.secure
    @api.doc('unfollow', description=NOTE)
    def delete(self, id):
        '''Unfollow an object given its ID'''
        model = self.model.objects.only('id').get_or_404(id=id)
        follow = Follow.objects.get_or_404(follower=current_user.id,
                                           following=model,
                                           until=None)
        follow.until = datetime.now()
        follow.save()
        count = Follow.objects.followers(model).count()
        return {'followers': count}, 200
