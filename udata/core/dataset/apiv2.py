import logging

from flask import url_for, abort, jsonify

from webargs import fields as arg_field, validate as arg_validate
from webargs.flaskparser import use_args


from udata import search
from udata.api.fields import paginate_schema
from udata.app import Blueprint
from udata.utils import get_by
from .models import Dataset, CommunityResource
from .permissions import DatasetEditPermission
from .apiv2_schemas import DatasetSchema, ResourceSchema


DEFAULT_SORTING = '-created_at'


log = logging.getLogger(__name__)


ns = Blueprint('datasets', __name__)


SORTS = [
    'created',
    'reuses',
    'followers',
    'views',
    '-created',
    '-reuses',
    '-followers',
    '-views'
]


resources_parser_args = {
    'page': arg_field.Int(missing=1),
    'page_size': arg_field.Int(missing=20),
    'type': arg_field.Str(),
    'q': arg_field.Str()
}


dataset_search_args = {
    "q": arg_field.Str(),
    'tag': arg_field.Str(),
    'badge': arg_field.Str(),
    'organization': arg_field.Str(),
    'owner': arg_field.Str(),
    'license': arg_field.Str(),
    'geozone': arg_field.Str(),
    'granularity': arg_field.Str(),
    'format': arg_field.Str(),
    'schema': arg_field.Str(),
    'temporal_coverage': arg_field.Str(),
    'featured': arg_field.Bool(),
    'sort': arg_field.Str(validate=arg_validate.OneOf(SORTS)),
    'page': arg_field.Int(missing=1),
    'page_size': arg_field.Int(missing=20)
}


@ns.route('/search/', endpoint='dataset_search', methods=['GET'])
@use_args(dataset_search_args, location="query")
def get_dataset_search(args):
    '''List or search all datasets'''
    try:
        result = search.query(Dataset, **args)
        schema = paginate_schema(DatasetSchema)
        return jsonify(schema().dump(result))
    except NotImplementedError:
        abort(501, 'Search endpoint not enabled')
    except RuntimeError:
        abort(500, 'Internal search service error')


@ns.route('/<dataset:dataset>/', endpoint='dataset', methods=['GET'])
def get_specific_dataset_by_id(dataset):
    '''Get a dataset given its identifier'''
    if dataset.deleted and not DatasetEditPermission(dataset).can():
        abort(410, 'Dataset has been deleted')
    return jsonify(DatasetSchema().dump(dataset))


@ns.route('/<dataset:dataset>/resources/', endpoint='resources', methods=['GET'])
@use_args(resources_parser_args, location="query")
def get_resources_paginated(args, dataset):
    '''Get the given dataset resources, paginated.'''
    # args = parser.parse(resources_parser_args, request)
    page = args['page']
    page_size = args['page_size']
    next_page = f"{url_for('apiv2.datasets.resources', dataset=dataset.id, _external=True)}?page={page + 1}&page_size={page_size}"
    previous_page = f"{url_for('apiv2.datasets.resources', dataset=dataset.id, _external=True)}?page={page - 1}&page_size={page_size}"
    res = dataset.resources

    if args.get('type'):
        res = [elem for elem in res if elem['type'] == args['type']]
        next_page += f"&type={args['type']}"
        previous_page += f"&type={args['type']}"

    if args.get('q'):
        res = [elem for elem in res if args['q'].lower() in elem['title'].lower()]
        next_page += f"&q={args['q']}"
        previous_page += f"&q={args['q']}"

    if page > 1:
        offset = page_size * (page - 1)
    else:
        offset = 0
    paginated_result = res[offset:(page_size + offset if page_size is not None else None)]

    return {
        'data': paginated_result,
        'next_page': next_page if page_size + offset < len(res) else None,
        'page': page,
        'page_size': page_size,
        'previous_page': previous_page if page > 1 else None,
        'total': len(res),
    }


@ns.route('/resources/<uuid:rid>/', endpoint='resource', methods=['GET'])
def get_specific_resource_by_rid(rid):
    dataset = Dataset.objects(resources__id=rid).first()
    if dataset:
        resource = get_by(dataset.resources, 'id', rid)
    else:
        resource = CommunityResource.objects(id=rid).first()
    if not resource:
        abort(404, 'Resource does not exist')

    return {
        'resource': ResourceSchema().dump(resource),
        'dataset_id': dataset.id if dataset else None
    }
