# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from werkzeug.datastructures import FileStorage

from udata import search
from udata.api import api, API, ModelAPI, ModelListAPI, SingleObjectAPI
from udata.auth import admin_permission
from udata.forms import ReuseForm
from udata.models import Reuse

from udata.core.issues.api import IssuesAPI
from udata.core.followers.api import FollowAPI

from .api_fields import reuse_fields, reuse_page_fields, reuse_suggestion_fields, image_fields
from .models import ReuseIssue, FollowReuse
from .permissions import ReuseEditPermission
from .search import ReuseSearch

ns = api.namespace('reuses', 'Reuse related operations')

common_doc = {
    'params': {'reuse': 'The reuse ID or slug'}
}
search_parser = api.search_parser(ReuseSearch)


@ns.route('/', endpoint='reuses')
@api.doc(get={'id': 'list_reuses', 'model': reuse_page_fields, 'parser': search_parser})
@api.doc(post={'id': 'create_reuse', 'model': reuse_fields, 'body': reuse_fields})
class ReuseListAPI(ModelListAPI):
    model = Reuse
    form = ReuseForm
    fields = reuse_fields
    search_adapter = ReuseSearch


@ns.route('/<reuse:reuse>/', endpoint='reuse')
@api.doc(model=reuse_fields, **common_doc)
@api.doc(get={'id': 'get_reuse'})
@api.doc(put={'id': 'update_reuse', 'body': reuse_fields})
class ReuseAPI(ModelAPI):
    model = Reuse
    form = ReuseForm
    fields = reuse_fields


@ns.route('/<reuse:reuse>/featured/', endpoint='reuse_featured')
@api.doc(**common_doc)
class ReuseFeaturedAPI(SingleObjectAPI, API):
    model = Reuse

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


@ns.route('/<id>/issues/', endpoint='reuse_issues')
class ReuseIssuesAPI(IssuesAPI):
    model = ReuseIssue


@ns.route('/<id>/followers/', endpoint='reuse_followers')
class FollowReuseAPI(FollowAPI):
    model = FollowReuse


suggest_parser = api.parser()
suggest_parser.add_argument('q', type=unicode, help='The string to autocomplete/suggest', location='args', required=True)
suggest_parser.add_argument('size', type=int, help='The amount of suggestion to fetch', location='args', default=10)


@ns.route('/suggest/', endpoint='suggest_reuses')
class SuggestReusesAPI(API):
    @api.marshal_list_with(reuse_suggestion_fields)
    @api.doc(id='suggest_reuses', parser=suggest_parser)
    def get(self):
        '''Suggest reuses'''
        args = suggest_parser.parse_args()
        return [
            {
                'id': opt['payload']['id'],
                'title': opt['text'],
                'score': opt['score'],
                'slug': opt['payload']['slug'],
                'image_url': opt['payload']['image_url'],
            }
            for opt in search.suggest(args['q'], 'reuse_suggest', args['size'])
        ]


image_parser = api.parser()
image_parser.add_argument('file', type=FileStorage, location='files')
image_parser.add_argument('bbox', type=str, location='form')


@ns.route('/<reuse:reuse>/image', endpoint='reuse_image')
@api.doc(parser=image_parser, **common_doc)
class ReuseImageAPI(API):
    @api.secure
    @api.doc('reuse_image')
    @api.marshal_with(image_fields)
    def post(self, reuse):
        '''Upload a new reuse image'''
        ReuseEditPermission(reuse.id).test()
        args = image_parser.parse_args()

        image = args['file']
        bbox = [int(float(c)) for c in args['bbox'].split(',')] if 'bbox' in args else None
        reuse.image.save(image, bbox=bbox)
        reuse.save()

        return reuse
