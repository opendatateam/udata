# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask.ext.security import current_user

from udata import search
from udata.api import api, ModelAPI, ModelListAPI, API
from udata.models import (
    CommunityResource, Dataset, Discussion, FollowUser, Issue, Reuse, User
)

from udata.core.dataset.api_fields import (
    community_resource_fields, dataset_full_fields
)
from udata.core.followers.api import FollowAPI
from udata.core.issues.api import issue_fields
from udata.core.discussions.api import discussion_fields
from udata.core.reuse.api_fields import reuse_fields
from udata.core.storages.api import (
    uploaded_image_fields, image_parser, parse_uploaded_image
)

from .api_fields import (
    apikey_fields,
    me_fields,
    me_metrics_fields,
    user_fields,
    user_page_fields,
    user_suggestion_fields,
)
from .forms import UserProfileForm
from .search import UserSearch

ns = api.namespace('users', 'User related operations')
me = api.namespace('me', 'Connected user related operations')
search_parser = api.search_parser(UserSearch)
filter_parser = api.parser()
filter_parser.add_argument(
    'q', type=str, help='The string to filter items',
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
    @api.marshal_with(user_fields)
    @api.doc('update_me', responses={400: 'Validation error'})
    def put(self, **kwargs):
        '''Update my profile'''
        user = current_user._get_current_object()
        form = api.validate(UserProfileForm, user)
        return form.save()


@me.route('/avatar', endpoint='my_avatar')
@api.doc(parser=image_parser)
class AvatarAPI(API):
    @api.secure
    @api.doc('my_avatar')
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
    @api.marshal_list_with(dataset_full_fields)
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
    @api.doc('my_org_datasets', parser=filter_parser)
    @api.marshal_list_with(dataset_full_fields)
    def get(self):
        '''List all datasets related to me and my organizations.'''
        q = filter_parser.parse_args().get('q')
        owners = list(current_user.organizations) + [current_user.id]
        datasets = Dataset.objects.owned_by(*owners).order_by('-last_modified')
        if q:
            datasets = datasets.filter(title__icontains=q.decode('utf-8'))
        return list(datasets)


@me.route('/org_community_resources/', endpoint='my_org_community_resources')
class MyOrgCommunityResourcesAPI(API):
    @api.secure
    @api.doc('my_org_community_resources', parser=filter_parser)
    @api.marshal_list_with(community_resource_fields)
    def get(self):
        '''List all community resources related to me and my organizations.'''
        q = filter_parser.parse_args().get('q')
        owners = list(current_user.organizations) + [current_user.id]
        community_resources = (CommunityResource.objects.owned_by(*owners)
                               .order_by('-last_modified'))
        if q:
            community_resources = community_resources.filter(
                title__icontains=q.decode('utf-8'))
        return list(community_resources)


@me.route('/org_reuses/', endpoint='my_org_reuses')
class MyOrgReusesAPI(API):
    @api.secure
    @api.doc('my_org_reuses', parser=filter_parser)
    @api.marshal_list_with(reuse_fields)
    def get(self):
        '''List all reuses related to me and my organizations.'''
        q = filter_parser.parse_args().get('q')
        owners = list(current_user.organizations) + [current_user.id]
        reuses = Reuse.objects.owned_by(*owners).order_by('-last_modified')
        if q:
            reuses = reuses.filter(title__icontains=q.decode('utf-8'))
        return list(reuses)


@me.route('/org_issues/', endpoint='my_org_issues')
class MyOrgIssuesAPI(API):
    @api.secure
    @api.doc('my_org_issues', parser=filter_parser)
    @api.marshal_list_with(issue_fields)
    def get(self):
        '''List all issues related to my organizations.'''
        q = filter_parser.parse_args().get('q')
        issues = (Issue.objects.from_organizations(
            current_user._get_current_object(), *current_user.organizations)
            .order_by('-created'))
        if q:
            issues = issues.filter(title__icontains=q.decode('utf-8'))
        return list(issues)


@me.route('/org_discussions/', endpoint='my_org_discussions')
class MyOrgDiscussionsAPI(API):
    @api.secure
    @api.doc('my_org_discussions', parser=filter_parser)
    @api.marshal_list_with(discussion_fields)
    def get(self):
        '''List all discussions related to my organizations.'''
        q = filter_parser.parse_args().get('q')
        discussions = (Discussion.objects.from_organizations(
            current_user._get_current_object(), *current_user.organizations)
            .order_by('-created'))
        if q:
            discussions = discussions.filter(title__icontains=q.decode('utf-8'))
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
    'q', type=str, help='The string to autocomplete/suggest',
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
                'first_name': opt['payload']['first_name'],
                'last_name': opt['payload']['last_name'],
                'avatar_url': opt['payload']['avatar_url'],
                'slug': opt['payload']['slug'],
                'score': opt['score'],
            }
            for opt in search.suggest(args['q'], 'user_suggest', args['size'])
        ]
