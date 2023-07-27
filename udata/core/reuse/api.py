from datetime import datetime

from flask import request

from udata.api import api, API, errors
from udata.api.parsers import ModelApiParser
from udata.auth import admin_permission
from udata.models import Dataset
from udata.utils import id_or_404

from udata.core.badges import api as badges_api
from udata.core.dataset.api_fields import dataset_ref_fields
from udata.core.followers.api import FollowAPI
from udata.core.storages.api import (
    uploaded_image_fields, image_parser, parse_uploaded_image
)

from .api_fields import (
    reuse_fields, reuse_page_fields,
    reuse_type_fields,
    reuse_suggestion_fields,
    reuse_topic_fields
)
from .forms import ReuseForm
from .models import Reuse, REUSE_TYPES, REUSE_TOPICS
from .permissions import ReuseEditPermission


DEFAULT_SORTING = '-created_at'
SUGGEST_SORTING = '-metrics.followers'


class ReuseApiParser(ModelApiParser):
    sorts = {
        'title': 'title',
        'created': 'created_at',
        'last_modified': 'last_modified',
        'datasets': 'metrics.datasets',
        'followers': 'metrics.followers',
        'views': 'metrics.views',
    }

    def __init__(self):
        super().__init__()
        self.parser.add_argument('dataset', type=str, location='args')
        self.parser.add_argument('tag', type=str, location='args')
        self.parser.add_argument('organization', type=str, location='args')
        self.parser.add_argument('owner', type=str, location='args')
        self.parser.add_argument('type', type=str, location='args')
        self.parser.add_argument('topic', type=str, location='args')
        self.parser.add_argument('featured', type=bool, location='args')

    @staticmethod
    def parse_filters(reuses, args):
        if args.get('q'):
            # Following code splits the 'q' argument by spaces to surround
            # every word in it with quotes before rebuild it.
            # This allows the search_text method to tokenise with an AND
            # between tokens whereas an OR is used without it.
            phrase_query = ' '.join([f'"{elem}"' for elem in args['q'].split(' ')])
            reuses = reuses.search_text(phrase_query)
        if args.get('dataset'):
            reuses = reuses.filter(datasets=args['dataset'])
        if args.get('featured'):
            reuses = reuses.filter(featured=args['featured'])
        if args.get('topic'):
            reuses = reuses.filter(topic=args['topic'])
        if args.get('type'):
            reuses = reuses.filter(type=args['type'])
        if args.get('tag'):
            reuses = reuses.filter(tags=args['tag'])
        if args.get('organization'):
            reuses = reuses.filter(organization=args['organization'])
        if args.get('owner'):
            reuses = reuses.filter(owner=args['owner'])
        return reuses


ns = api.namespace('reuses', 'Reuse related operations')

common_doc = {
    'params': {'reuse': 'The reuse ID or slug'}
}

reuse_parser = ReuseApiParser()


@ns.route('/', endpoint='reuses')
class ReuseListAPI(API):
    @api.doc('list_reuses')
    @api.expect(reuse_parser.parser)
    @api.marshal_with(reuse_page_fields)
    def get(self):
        args = reuse_parser.parse()
        reuses = Reuse.objects(deleted=None, private__ne=True)
        reuses = reuse_parser.parse_filters(reuses, args)
        sort = args['sort'] or ('$text_score' if args['q'] else None) or DEFAULT_SORTING
        return reuses.order_by(sort).paginate(args['page'], args['page_size'])

    @api.secure
    @api.doc('create_reuse')
    @api.expect(reuse_fields)
    @api.response(400, 'Validation error')
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
        request_deleted = request.json.get('deleted', True)
        if reuse.deleted and request_deleted is not None:
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
        reuse.deleted = datetime.utcnow()
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
            dataset = Dataset.objects.get_or_404(id=id_or_404(request.json['id']))
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
@ns.doc(get={'id': 'list_reuse_followers'},
        post={'id': 'follow_reuse'},
        delete={'id': 'unfollow_reuse'})
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
class ReusesSuggestAPI(API):
    @api.doc('suggest_reuses')
    @api.expect(suggest_parser)
    @api.marshal_list_with(reuse_suggestion_fields)
    def get(self):
        '''Reuses suggest endpoint using mongoDB contains'''
        args = suggest_parser.parse_args()
        reuses = Reuse.objects(deleted=None, private__ne=True, title__icontains=args['q'])
        return [
            {
                'id': reuse.id,
                'title': reuse.title,
                'slug': reuse.slug,
                'image_url': reuse.image,
            }
            for reuse in reuses.order_by(SUGGEST_SORTING).limit(args['size'])
        ]


@ns.route('/<reuse:reuse>/image', endpoint='reuse_image')
@api.doc(**common_doc)
class ReuseImageAPI(API):
    @api.secure
    @api.doc('reuse_image')
    @api.expect(image_parser)  # Swagger 2.0 does not support formData at path level
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


@ns.route('/topics/', endpoint='reuse_topics')
class ReuseTopicsAPI(API):
    @api.doc('reuse_topics')
    @api.marshal_list_with(reuse_topic_fields)
    def get(self):
        '''List all reuse topics'''
        return [{'id': id, 'label': label}
                for id, label in REUSE_TOPICS.items()]
