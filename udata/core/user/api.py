# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from werkzeug.datastructures import FileStorage
from flask.ext.security import current_user

from udata import search
from udata.api import api, ModelAPI, ModelListAPI, API
from udata.models import User, FollowUser, Reuse, Dataset, Issue, Discussion

from udata.core.dataset.api_fields import dataset_fields
from udata.core.followers.api import FollowAPI
from udata.core.reuse.api_fields import reuse_fields

from udata.features.transfer.models import Transfer

from .api_fields import (
    me_fields,
    user_fields,
    user_page_fields,
    user_suggestion_fields,
    notifications_fields,
    avatar_fields
)
from .forms import UserProfileForm
from .search import UserSearch

ns = api.namespace('users', 'User related operations')
me = api.namespace('me', 'Connected user related operations')
search_parser = api.search_parser(UserSearch)


@me.route('/', endpoint='me')
class MeAPI(API):
    @api.secure
    @api.doc('get_me')
    @api.marshal_with(me_fields)
    def get(self):
        '''Fetch the current user (me) identity'''
        return current_user._get_current_object()

    @api.secure
    @api.marshal_with(user_fields)
    @api.doc('update_me', responses={400: 'Validation error'})
    def put(self, **kwargs):
        '''Update my profile'''
        user = current_user._get_current_object()
        form = api.validate(UserProfileForm, user)
        return form.save()


avatar_parser = api.parser()
avatar_parser.add_argument('file', type=FileStorage, location='files')
avatar_parser.add_argument('bbox', type=str, location='form')


@me.route('/avatar', endpoint='my_avatar')
@api.doc(parser=avatar_parser)
class AvatarAPI(API):
    @api.secure
    @api.doc('my_avatar')
    @api.marshal_with(avatar_fields)
    def post(self):
        '''Upload a new avatar'''
        args = avatar_parser.parse_args()

        avatar = args['file']
        bbox = ([int(float(c)) for c in args['bbox'].split(',')]
                if 'bbox' in args else None)
        current_user.avatar.save(avatar, bbox=bbox)
        current_user.save()

        return current_user


@me.route('/reuses/', endpoint='my_reuses')
class MyReusesAPI(API):
    @api.secure
    @api.doc('my_reuses')
    @api.marshal_list_with(reuse_fields)
    def get(self):
        '''List all my reuses (including private ones)'''
        return list(Reuse.objects.owned_by(current_user.id))


@me.route('/datasets/', endpoint='my_datasets')
class MyDatasetsAPI(API):
    @api.secure
    @api.doc('my_datasets')
    @api.marshal_list_with(dataset_fields)
    def get(self):
        '''List all my datasets (including private ones)'''
        return list(Dataset.objects.owned_by(current_user.id))


@me.route('/notifications/', endpoint='notifications')
class NotificationsAPI(API):
    @api.secure
    @api.doc('notifications')
    @api.marshal_list_with(notifications_fields)
    def get(self):
        '''List all current user pending notifications'''

        user = current_user._get_current_object()
        notifications = []

        orgs = [o for o in user.organizations if o.is_member(user)]
        datasets = Dataset.objects.owned_by(user, *orgs)
        reuses = Reuse.objects.owned_by(user, *orgs)

        # TODO: use polymorph field

        # Fetch user open issues
        for issue in Issue.objects(subject__in=list(datasets) + list(reuses)):
            notifications.append({
                'type': 'issue',
                'created_on': issue.created,
                'details': {
                    'id': str(issue.id),
                    'title': issue.title,
                    'subject': {
                        'id': str(issue.subject.id),
                        'type': issue.subject.__class__.__name__.lower(),
                    }
                }
            })

        # Fetch user open discussions
        for discussion in Discussion.objects(
                subject__in=list(datasets) + list(reuses)):
            notifications.append({
                'type': 'discussion',
                'created_on': discussion.created,
                'details': {
                    'id': str(discussion.id),
                    'title': discussion.title,
                    'subject': {
                        'id': str(discussion.subject.id),
                        'type': discussion.subject.__class__.__name__.lower(),
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
        for transfer in Transfer.objects(
                recipient__in=[user] + orgs, status='pending'):
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
@api.doc(get={
    'id': 'list_users',
    'model': user_page_fields,
    'parser': search_parser})
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
    @api.doc(notes="You can't follow yourself.",
             response={403: 'When tring to follow yourself'})
    def post(self, id):
        '''Follow an user given its ID'''
        if id == str(current_user.id):
            api.abort(403, "You can't follow yourself")
        return super(FollowUserAPI, self).post(id)


suggest_parser = api.parser()
suggest_parser.add_argument(
    'q', type=unicode, help='The string to autocomplete/suggest',
    location='args', required=True)
suggest_parser.add_argument(
    'size', type=int, help='The amount of suggestion to fetch',
    location='args', default=10)


@ns.route('/suggest/', endpoint='suggest_users')
class SuggestUsersAPI(API):
    @api.marshal_list_with(user_suggestion_fields)
    @api.doc('suggest_users', parser=suggest_parser)
    def get(self):
        '''Suggest users'''
        args = suggest_parser.parse_args()
        return [
            {
                'id': opt['text'],
                'fullname': opt['payload']['fullname'],
                'avatar_url': opt['payload']['avatar_url'],
                'slug': opt['payload']['slug'],
                'score': opt['score'],
            }
            for opt in search.suggest(args['q'], 'user_suggest', args['size'])
        ]
