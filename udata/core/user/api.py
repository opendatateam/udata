# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import request
from flask_security import current_user, logout_user

from udata import search
from udata.api import api, API
from udata.auth import admin_permission
from udata.models import CommunityResource, Dataset, Reuse, User

from udata.core.dataset.api_fields import (
    community_resource_fields, dataset_fields
)
from udata.core.followers.api import FollowAPI
from udata.core.issues.actions import issues_for
from udata.core.issues.api import issue_fields
from udata.core.discussions.actions import discussions_for
from udata.core.discussions.api import discussion_fields
from udata.core.reuse.api_fields import reuse_fields
from udata.core.storages.api import (
    uploaded_image_fields, image_parser, parse_uploaded_image
)
from udata.core.user.models import Role
from udata.utils import multi_to_dict

from .api_fields import (
    apikey_fields,
    me_fields,
    me_metrics_fields,
    user_fields,
    user_page_fields,
    user_suggestion_fields,
    user_role_fields,
)
from .forms import UserProfileForm, UserProfileAdminForm
from .search import UserSearch

ns = api.namespace('users', 'User related operations')
me = api.namespace('me', 'Connected user related operations')
search_parser = UserSearch.as_request_parser()
filter_parser = api.parser()
filter_parser.add_argument(
    'q', type=unicode, help='The string to filter items',
    location='args', required=False)


@me.route('/', endpoint='me')
class MeAPI(API):
    @api.secure
    @api.doc('get_me')
    @api.marshal_with(me_fields)
    def get(self):
        '''Fetch the current user (me) identity'''
        return current_user._get_current_object()

    @api.secure
    @api.doc('update_me')
    @api.expect(me_fields)
    @api.marshal_with(me_fields)
    @api.response(400, 'Validation error')
    def put(self, **kwargs):
        '''Update my profile'''
        user = current_user._get_current_object()
        form = api.validate(UserProfileForm, user)
        return form.save()

    @api.secure
    @api.doc('delete_me')
    @api.response(204, 'Object deleted')
    def delete(self, **kwargs):
        '''Delete my profile'''
        user = current_user._get_current_object()
        user.mark_as_deleted()
        logout_user()
        return '', 204


@me.route('/avatar', endpoint='my_avatar')
class AvatarAPI(API):
    @api.secure
    @api.doc('my_avatar')
    @api.expect(image_parser)
    @api.marshal_with(uploaded_image_fields)
    def post(self):
        '''Upload a new avatar'''
        parse_uploaded_image(current_user.avatar)
        current_user.save()
        return {'image': current_user.avatar}


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


@me.route('/metrics/', endpoint='my_metrics')
class MyMetricsAPI(API):
    @api.secure
    @api.doc('my_metrics')
    @api.marshal_list_with(me_metrics_fields)
    def get(self):
        '''Fetch the current user (me) metrics'''
        return current_user._get_current_object()


@me.route('/org_datasets/', endpoint='my_org_datasets')
class MyOrgDatasetsAPI(API):
    @api.secure
    @api.doc('my_org_datasets')
    @api.expect(filter_parser)
    @api.marshal_list_with(dataset_fields)
    def get(self):
        '''List all datasets related to me and my organizations.'''
        q = filter_parser.parse_args().get('q')
        owners = list(current_user.organizations) + [current_user.id]
        datasets = Dataset.objects.owned_by(*owners).order_by('-last_modified')
        if q:
            datasets = datasets.filter(title__icontains=q)
        return list(datasets)


@me.route('/org_community_resources/', endpoint='my_org_community_resources')
class MyOrgCommunityResourcesAPI(API):
    @api.secure
    @api.doc('my_org_community_resources')
    @api.expect(filter_parser)
    @api.marshal_list_with(community_resource_fields)
    def get(self):
        '''List all community resources related to me and my organizations.'''
        q = filter_parser.parse_args().get('q')
        owners = list(current_user.organizations) + [current_user.id]
        community_resources = (CommunityResource.objects.owned_by(*owners)
                               .order_by('-last_modified'))
        if q:
            community_resources = community_resources.filter(
                title__icontains=q)
        return list(community_resources)


@me.route('/org_reuses/', endpoint='my_org_reuses')
class MyOrgReusesAPI(API):
    @api.secure
    @api.doc('my_org_reuses')
    @api.expect(filter_parser)
    @api.marshal_list_with(reuse_fields)
    def get(self):
        '''List all reuses related to me and my organizations.'''
        q = filter_parser.parse_args().get('q')
        owners = list(current_user.organizations) + [current_user.id]
        reuses = Reuse.objects.owned_by(*owners).order_by('-last_modified')
        if q:
            reuses = reuses.filter(title__icontains=q)
        return list(reuses)


@me.route('/org_issues/', endpoint='my_org_issues')
class MyOrgIssuesAPI(API):
    @api.secure
    @api.doc('my_org_issues')
    @api.expect(filter_parser)
    @api.marshal_list_with(issue_fields)
    def get(self):
        '''List all issues related to my organizations.'''
        q = filter_parser.parse_args().get('q')
        issues = issues_for(current_user._get_current_object())
        issues = issues.order_by('-created')
        if q:
            issues = issues.filter(title__icontains=q)
        return list(issues)


@me.route('/org_discussions/', endpoint='my_org_discussions')
class MyOrgDiscussionsAPI(API):
    @api.secure
    @api.doc('my_org_discussions')
    @api.expect(filter_parser)
    @api.marshal_list_with(discussion_fields)
    def get(self):
        '''List all discussions related to my organizations.'''
        q = filter_parser.parse_args().get('q')
        discussions = discussions_for(current_user._get_current_object())
        discussions = discussions.order_by('-created')
        if q:
            decoded = q
            discussions = discussions.filter(title__icontains=decoded)
        return list(discussions)


@me.route('/apikey', endpoint='my_apikey')
class ApiKeyAPI(API):
    @api.secure
    @api.doc('generate_apikey')
    @api.marshal_with(apikey_fields)
    @api.response(201, 'API Key generated')
    def post(self):
        '''(Re)Generate my API Key'''
        current_user.generate_api_key()
        current_user.save()
        return current_user, 201

    @api.secure
    @api.doc('clear_apikey')
    @api.response(204, 'API Key deleted/cleared')
    def delete(self):
        '''Clear/destroy an apikey'''
        current_user.apikey = None
        current_user.save()
        return '', 204


@ns.route('/', endpoint='users')
class UserListAPI(API):
    model = User
    fields = user_fields
    form = UserProfileForm
    search_adapter = UserSearch

    @api.doc('list_users')
    @api.expect(search_parser)
    @api.marshal_with(user_page_fields)
    def get(self):
        '''List all users'''
        search_parser.parse_args()
        return search.query(UserSearch, **multi_to_dict(request.args))

    @api.secure(admin_permission)
    @api.doc('create_user')
    @api.expect(user_fields)
    @api.marshal_with(user_fields, code=201)
    @api.response(400, 'Validation error')
    def post(self):
        '''Create a new object'''
        form = api.validate(UserProfileAdminForm)
        user = form.save()
        return user, 201


@ns.route('/<user:user>/', endpoint='user')
@api.response(404, 'User not found')
@api.response(410, 'User is not active or has been deleted')
class UserAPI(API):

    @api.doc('get_user')
    @api.marshal_with(user_fields)
    def get(self, user):
        '''Get a user given its identifier'''
        if current_user.is_anonymous or not current_user.sysadmin:
            if not user.active:
                api.abort(410, 'User is not active')
            if user.deleted:
                api.abort(410, 'User has been deleted')
        return user

    @api.secure(admin_permission)
    @api.doc('update_user')
    @api.expect(user_fields)
    @api.marshal_with(user_fields)
    @api.response(400, 'Validation error')
    def put(self, user):
        '''Update a user given its identifier'''
        form = api.validate(UserProfileAdminForm, user)
        return form.save()

    @api.secure(admin_permission)
    @api.doc('delete_user')
    @api.response(204, 'Object deleted')
    @api.response(403, 'When trying to delete yourself')
    def delete(self, user):
        '''Delete a user given its identifier'''
        if user.deleted:
            api.abort(410, 'User has already been deleted')
        if user == current_user._get_current_object():
            api.abort(403, 'You cannot delete yourself with this API. ' +
                      'Use the "me" API instead.')
        user.mark_as_deleted()
        return '', 204


@ns.route('/<id>/followers/', endpoint='user_followers')
@ns.doc(get={'id': 'list_user_followers'},
        post={'id': 'follow_user'},
        delete={'id': 'unfollow_user'})
class FollowUserAPI(FollowAPI):
    model = User

    @api.secure
    @api.doc(notes="You can't follow yourself.")
    @api.response(403, 'When trying to follow yourself')
    def post(self, id):
        '''Follow a user given its ID'''
        if id == str(current_user.id):
            api.abort(403, "You can't follow yourself")
        return super(FollowUserAPI, self).post(id)


suggest_parser = api.parser()
suggest_parser.add_argument(
    'q', help='The string to autocomplete/suggest', location='args',
    required=True)
suggest_parser.add_argument(
    'size', type=int, help='The amount of suggestion to fetch',
    location='args', default=10)


@ns.route('/suggest/', endpoint='suggest_users')
class SuggestUsersAPI(API):
    @api.doc('suggest_users')
    @api.expect(suggest_parser)
    @api.marshal_list_with(user_suggestion_fields)
    def get(self):
        '''Suggest users'''
        args = suggest_parser.parse_args()
        return [
            {
                'id': opt['text'],
                'first_name': opt['payload']['first_name'],
                'last_name': opt['payload']['last_name'],
                'avatar_url': opt['payload']['avatar_url'],
                'slug': opt['payload']['slug'],
                'score': opt['score'],
            }
            for opt in search.suggest(args['q'], 'user_suggest', args['size'])
        ]


@ns.route('/roles/', endpoint='user_roles')
class UserRolesAPI(API):
    @api.doc('user_roles')
    @api.marshal_list_with(user_role_fields)
    def get(self):
        '''List all possible user roles'''
        return [{'name': role.name} for role in Role.objects()]
