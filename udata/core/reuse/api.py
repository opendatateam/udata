# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from flask import request

from udata import search
from udata.api import api, API, errors
from udata.auth import admin_permission
from udata.models import Dataset
from udata.utils import multi_to_dict

from udata.core.badges import api as badges_api
from udata.core.followers.api import FollowAPI
from udata.core.storages.api import (
    uploaded_image_fields, image_parser, parse_uploaded_image
)

from .api_fields import (
    reuse_fields, reuse_page_fields, reuse_suggestion_fields,
    reuse_type_fields, dataset_ref_fields
)
from .forms import ReuseForm
from .models import Reuse, REUSE_TYPES
from .permissions import ReuseEditPermission
from .search import ReuseSearch

ns = api.namespace('reuses', 'Reuse related operations')

common_doc = {
    'params': {'reuse': 'The reuse ID or slug'}
}
search_parser = ReuseSearch.as_request_parser()


@ns.route('/', endpoint='reuses')
class ReuseListAPI(API):
    @api.doc('list_reuses', parser=search_parser)
    @api.marshal_with(reuse_page_fields)
    def get(self):
        search_parser.parse_args()
        return search.query(ReuseSearch, **multi_to_dict(request.args))

    @api.secure
    @api.doc('create_reuse', responses={400: 'Validation error'})
    @api.expect(reuse_fields)
    @api.marshal_with(reuse_fields)
    def post(self):
        '''Create a new object'''
        form = api.validate(ReuseForm)
        return form.save(), 201


@ns.route('/<reuse:reuse>/', endpoint='reuse', doc=common_doc)
@api.response(404, 'Reuse not found')
@api.response(410, 'Reuse has been deleted')
class ReuseAPI(API):
    @api.doc('get_reuse')
    @api.marshal_with(reuse_fields)
    def get(self, reuse):
        '''Fetch a given reuse'''
        if reuse.deleted and not ReuseEditPermission(reuse).can():
            api.abort(410, 'This reuse has been deleted')
        return reuse

    @api.secure
    @api.doc('update_reuse')
    @api.expect(reuse_fields)
    @api.marshal_with(reuse_fields)
    @api.response(400, errors.VALIDATION_ERROR)
    def put(self, reuse):
        '''Update a given reuse'''
        if reuse.deleted:
            api.abort(410, 'This reuse has been deleted')
        ReuseEditPermission(reuse).test()
        form = api.validate(ReuseForm, reuse)
        return form.save()

    @api.secure
    @api.doc('delete_reuse')
    @api.response(204, 'Reuse deleted')
    def delete(self, reuse):
        '''Delete a given reuse'''
        if reuse.deleted:
            api.abort(410, 'This reuse has been deleted')
        ReuseEditPermission(reuse).test()
        reuse.deleted = datetime.now()
        reuse.save()
        return '', 204


@ns.route('/<reuse:reuse>/datasets/', endpoint='reuse_add_dataset')
class ReuseDatasetsAPI(API):
    @api.secure
    @api.doc('reuse_add_dataset', **common_doc)
    @api.expect(dataset_ref_fields)
    @api.response(200, 'The dataset is already present', reuse_fields)
    @api.marshal_with(reuse_fields, code=201)
    def post(self, reuse):
        '''Add a dataset to a given reuse'''
        if 'id' not in request.json:
            api.abort(400, 'Expect a dataset identifier')
        try:
            dataset = Dataset.objects.get_or_404(id=request.json['id'])
        except Dataset.DoesNotExist:
            msg = 'Dataset {0} does not exists'.format(request.json['id'])
            api.abort(404, msg)
        if dataset in reuse.datasets:
            return reuse
        reuse.datasets.append(dataset)
        reuse.save()
        return reuse, 201


@ns.route('/badges/', endpoint='available_reuse_badges')
class AvailableDatasetBadgesAPI(API):
    @api.doc('available_reuse_badges')
    def get(self):
        '''List all available reuse badges and their labels'''
        return Reuse.__badges__


@ns.route('/<reuse:reuse>/badges/', endpoint='reuse_badges')
class ReuseBadgesAPI(API):
    @api.doc('add_reuse_badge', **common_doc)
    @api.expect(badges_api.badge_fields)
    @api.marshal_with(badges_api.badge_fields)
    @api.secure(admin_permission)
    def post(self, reuse):
        '''Create a new badge for a given reuse'''
        return badges_api.add(reuse)


@ns.route('/<reuse:reuse>/badges/<badge_kind>/', endpoint='reuse_badge')
class ReuseBadgeAPI(API):
    @api.doc('delete_reuse_badge', **common_doc)
    @api.secure(admin_permission)
    def delete(self, reuse, badge_kind):
        '''Delete a badge for a given reuse'''
        return badges_api.remove(reuse, badge_kind)


@ns.route('/<reuse:reuse>/featured/', endpoint='reuse_featured')
@api.doc(**common_doc)
class ReuseFeaturedAPI(API):
    @api.doc('feature_reuse')
    @api.secure(admin_permission)
    @api.marshal_with(reuse_fields)
    def post(self, reuse):
        '''Mark a reuse as featured'''
        reuse.featured = True
        reuse.save()
        return reuse

    @api.doc('unfeature_reuse')
    @api.secure(admin_permission)
    @api.marshal_with(reuse_fields)
    def delete(self, reuse):
        '''Unmark a reuse as featured'''
        reuse.featured = False
        reuse.save()
        return reuse


@ns.route('/<id>/followers/', endpoint='reuse_followers')
class FollowReuseAPI(FollowAPI):
    model = Reuse


suggest_parser = api.parser()
suggest_parser.add_argument(
    'q', help='The string to autocomplete/suggest', location='args',
    required=True)
suggest_parser.add_argument(
    'size', type=int, help='The amount of suggestion to fetch',
    location='args', default=10)


@ns.route('/suggest/', endpoint='suggest_reuses')
class SuggestReusesAPI(API):
    @api.marshal_list_with(reuse_suggestion_fields)
    @api.doc(id='suggest_reuses', parser=suggest_parser)
    def get(self):
        '''Suggest reuses'''
        args = suggest_parser.parse_args()
        return [
            {
                'id': opt['text'],
                'title': opt['payload']['title'],
                'score': opt['score'],
                'slug': opt['payload']['slug'],
                'image_url': opt['payload']['image_url'],
            }
            for opt in search.suggest(args['q'], 'reuse_suggest', args['size'])
        ]


@ns.route('/<reuse:reuse>/image', endpoint='reuse_image')
@api.doc(parser=image_parser, **common_doc)
class ReuseImageAPI(API):
    @api.secure
    @api.doc('reuse_image')
    @api.marshal_with(uploaded_image_fields)
    def post(self, reuse):
        '''Upload a new reuse image'''
        ReuseEditPermission(reuse).test()
        parse_uploaded_image(reuse.image)
        reuse.save()

        return reuse


@ns.route('/types/', endpoint='reuse_types')
class ReuseTypesAPI(API):
    @api.doc('reuse_types')
    @api.marshal_list_with(reuse_type_fields)
    def get(self):
        '''List all reuse types'''
        return [{'id': id, 'label': label}
                for id, label in REUSE_TYPES.items()]
