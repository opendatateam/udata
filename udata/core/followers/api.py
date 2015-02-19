# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from flask.ext.security import current_user

from udata.api import api, API, fields, pager
from udata.models import Follow

from udata.core.user.api_fields import user_ref_fields

follow_fields = api.model('Follow', {
    'id': fields.String(description='The follow object technical ID', readonly=True),
    'follower': fields.Nested(user_ref_fields, description='The follower', readonly=True),
    'since':  fields.ISODateTime(description='The date from which the user started following', readonly=True)
})

follow_page_fields = api.model('FollowPage', pager(follow_fields))

parser = api.parser()
parser.add_argument('page', type=int, default=1, location='args', help='The page to fetch')
parser.add_argument('page_size', type=int, default=20, location='args', help='The page size to fetch')

NOTE = 'Returns the number of followers left after the operation'


class FollowAPI(API):
    '''
    Base Follow Model API.
    '''
    model = Follow

    @api.doc(id='list_followers', parser=parser)
    @api.marshal_with(follow_page_fields)
    def get(self, id):
        '''List all followers for a given object'''
        args = parser.parse_args()
        return self.model.objects(following=id, until=None).paginate(args['page'], args['page_size'])

    @api.secure
    @api.doc(id='follow', description=NOTE)
    def post(self, id):
        '''Follow an object given its ID'''
        follow, created = self.model.objects.get_or_create(follower=current_user.id, following=id, until=None)
        count = self.model.objects.followers(id).count()

        return {'followers': count}, 201 if created else 200

    @api.secure
    @api.doc(id='unfollow', description=NOTE)
    def delete(self, id):
        '''Unfollow an object given its ID'''
        follow = self.model.objects.get_or_404(follower=current_user.id, following=id, until=None)
        follow.until = datetime.now()
        follow.save()
        count = self.model.objects.followers(id).count()
        return {'followers': count}, 200
