# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask.ext.security import current_user

from udata import search
from udata.api import api, ModelAPI, ModelListAPI, API
from udata.models import User, FollowUser, Reuse, Dataset, Issue
from udata.forms import UserProfileForm

from udata.core.followers.api import FollowAPI
from udata.core.reuse.api_fields import reuse_fields

from udata.features.transfer.models import Transfer

from .api_fields import user_fields, user_page_fields, user_suggestion_fields, notifications_fields
from .search import UserSearch

ns = api.namespace('users', 'User related operations')
search_parser = api.search_parser(UserSearch)


@api.route('/me/', endpoint='me')
@api.doc(get={'model': user_fields, 'id': 'get_me'})
class MeAPI(ModelAPI):
    model = User
    form = UserProfileForm
    fields = user_fields
    decorators = [api.secure]

    def get_or_404(self, **kwargs):
        if not current_user.is_authenticated():
            api.abort(404)
        return current_user._get_current_object()


@api.route('/me/reuses/', endpoint='my_reuses')
class MyReusesAPI(API):
    @api.marshal_list_with(reuse_fields)
    def get(self):
        '''List all my reuses (including private ones)'''
        if not current_user.is_authenticated():
            api.abort(401)
        return list(Reuse.objects(owner=current_user.id))


@api.route('/me/notifications/', endpoint='notifications')
class NotificationsAPI(API):
    @api.doc('notifications')
    @api.marshal_list_with(notifications_fields)
    def get(self):
        '''List all current user pending notifications'''
        if not current_user.is_authenticated():
            api.abort(401)

        user = current_user._get_current_object()
        notifications = []

        orgs = [o for o in user.organizations if o.is_admin(user)]

        # Fetch user open issues
        datasets = Dataset.objects.owned_by(user, *orgs)
        reuses = Reuse.objects.owned_by(user, *orgs)
        for issue in Issue.objects(subject__in=list(datasets)+list(reuses)):
            notifications.append({
                'type': 'issue',
                'created_on': issue.created,
                'details': {
                    'subject': {
                        'type': issue.subject.__class__.__name__.lower(),
                        'id': str(issue.subject)
                    }
                }
            })

        # Fetch pending membership requests
        for org in orgs:
            for request in org.pending_requests:
                notifications.append({
                    'type': 'membership_request',
                    'created_on': request.created,
                    'details': {
                        'organization': org.id,
                        'user': {
                            'id': str(request.user.id),
                            'fullname': request.user.fullname,
                            'avatar': str(request.user.avatar)
                        }
                    }
                })

        # Fetch pending transfer requests
        for transfer in Transfer.objects(recipient__in=[user]+orgs, status='pending'):
            notifications.append({
                'type': 'transfer_request',
                'created_on': transfer.created,
                'details': {
                    'id': str(transfer.id),
                    'subject': {
                        'class': transfer.subject.__class__.__name__.lower(),
                        'id': str(transfer.subject.id)
                    }
                }
            })

        return notifications


@ns.route('/', endpoint='users')
@api.doc(get={'id': 'list_users', 'model': user_page_fields, 'parser': search_parser})
@api.doc(post={'id': 'create_user', 'model': user_fields})
class UserListAPI(ModelListAPI):
    model = User
    fields = user_fields
    form = UserProfileForm
    search_adapter = UserSearch


@ns.route('/<user:user>/', endpoint='user')
@api.doc(model=user_fields, get={'id': 'get_user'})
@api.doc(put={'id': 'update_user', 'body': user_fields})
class UserAPI(ModelAPI):
    model = User
    fields = user_fields
    form = UserProfileForm


@ns.route('/<id>/followers/', endpoint='user_followers')
class FollowUserAPI(FollowAPI):
    model = FollowUser

    @api.secure
    @api.doc(notes="You can't follow yourself.", response={403: 'When tring to follow yourself'})
    def post(self, id):
        '''Follow an user given its ID'''
        if id == str(current_user.id):
            api.abort(403, "You can't follow yourself")
        return super(FollowUserAPI, self).post(id)



suggest_parser = api.parser()
suggest_parser.add_argument('q', type=unicode, help='The string to autocomplete/suggest', location='args', required=True)
suggest_parser.add_argument('size', type=int, help='The amount of suggestion to fetch', location='args', default=10)


@ns.route('/suggest/', endpoint='suggest_users')
class SuggestReusesAPI(API):
    @api.marshal_list_with(user_suggestion_fields)
    @api.doc(id='suggest_users', parser=suggest_parser)
    def get(self):
        '''Suggest users'''
        args = suggest_parser.parse_args()
        return [
            {
                'id': opt['payload']['id'],
                'fullname': opt['payload']['fullname'],
                'avatar_url': opt['payload']['avatar_url'],
                'slug': opt['payload']['slug'],
                'score': opt['score'],
            }
            for opt in search.suggest(args['q'], 'user_suggest', args['size'])
        ]
