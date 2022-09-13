import logging

from flask import url_for, abort

from flask_apispec import use_kwargs, marshal_with
from webargs import fields


from udata import search
from udata.app import csrf
from udata.api import apiv2_blueprint as apiv2, UDataApiV2
from udata.api.parsers import ModelApiV2Parser
from udata.utils import get_by
from .forms import DatasetForm
from .models import Dataset, CommunityResource, License
from .permissions import DatasetEditPermission
from .apiv2_schemas import DatasetSchema, ResourcePaginationSchema, ResourceWithDatasetIdSchema, DatasetPaginationSchema
from .search import DatasetSearch


DEFAULT_SORTING = '-created_at'


log = logging.getLogger(__name__)


class DatasetApiParser(ModelApiV2Parser):
    sorts = {
        'title': 'title',
        'created': 'created_at',
        'last_modified': 'last_modified',
        'reuses': 'metrics.reuses',
        'followers': 'metrics.followers',
        'views': 'metrics.views',
    }

    def __init__(self):
        super().__init__()
        self.parser.update({
            'tag': fields.Str(),
            'license': fields.Str(),
            'featured': fields.Bool(),
            'geozone': fields.Str(),
            'granularity': fields.Str(),
            'temporal_coverage': fields.Str(),
            'organization': fields.Str(),
            'owner': fields.Str(),
            'format': fields.Str(),
            'schema': fields.Str(),
            'schema_version': fields.Str(),
        })

    @staticmethod
    def parse_filters(datasets, args):
        if args.get('q'):
            # Following code splits the 'q' argument by spaces to surround
            # every word in it with quotes before rebuild it.
            # This allows the search_text method to tokenise with an AND
            # between tokens whereas an OR is used without it.
            phrase_query = ' '.join([f'"{elem}"' for elem in args['q'].split(' ')])
            datasets = datasets.search_text(phrase_query)
        if args.get('tag'):
            datasets = datasets.filter(tags=args['tag'])
        if args.get('license'):
            datasets = datasets.filter(license__in=License.objects.filter(id=args['license']))
        if args.get('geozone'):
            datasets = datasets.filter(spatial__zones=args['geozone'])
        if args.get('granularity'):
            datasets = datasets.filter(spatial__granularity=args['granularity'])
        if args.get('temporal_coverage'):
            datasets = datasets.filter(temporal_coverage__start__gte=args['temporal_coverage'][:9], temporal_coverage__start__lte=args['temporal_coverage'][11:])
        if args.get('featured'):
            datasets = datasets.filter(featured=args['featured'])
        if args.get('organization'):
            datasets = datasets.filter(organization=args['organization'])
        if args.get('owner'):
            datasets = datasets.filter(owner=args['owner'])
        if args.get('format'):
            datasets = datasets.filter(resources__format=args['format'])
        if args.get('schema'):
            datasets = datasets.filter(resources__schema__name=args['schema'])
        if args.get('schema_version'):
            datasets = datasets.filter(resources__schema__version=args['schema_version'])
        return datasets


dataset_parser = DatasetApiParser()
dataset_parser_args = dataset_parser.parser

search_arguments = DatasetSearch.as_request_parser()

resources_parser_args = ModelApiV2Parser().parser

resources_parser_args.update({
    'type': fields.Str()
})


@apiv2.route('/datasets/', endpoint='list_datasets', methods=['GET'])
@use_kwargs(dataset_parser_args, location="query")
@marshal_with(DatasetPaginationSchema())
def get_dataset_list(**kwargs):
    """List or search all datasets"""
    datasets = Dataset.objects(archived=None, deleted=None, private=False)
    datasets = dataset_parser.parse_filters(datasets, kwargs)

    sort = kwargs.get('sort', None) or ('$text_score' if kwargs.get('sort', None) else None) or DEFAULT_SORTING
    return datasets.order_by(sort).paginate(kwargs['page'], kwargs['page_size'])


@apiv2.route('/datasets/', endpoint='create_dataset', methods=['POST'])
@csrf.exempt
@UDataApiV2.secure
@marshal_with(DatasetSchema())
def post_new_dataset():
    '''Create a new dataset'''
    form = UDataApiV2.validate(DatasetForm)
    dataset = form.save()
    return dataset, 201


@apiv2.route('/datasets/search/', endpoint='dataset_search', methods=['GET'])
@use_kwargs(search_arguments, location="query")
@marshal_with(DatasetPaginationSchema())
def get_dataset_search(**kwargs):
    """Datasets search endpoint."""
    try:
        return search.query(Dataset, **kwargs)
    except NotImplementedError:
        abort(501, 'Search endpoint not enabled')
    except RuntimeError:
        abort(500, 'Internal search service error')


@apiv2.route('/datasets/<dataset:dataset>/', endpoint='dataset', methods=['GET'])
@marshal_with(DatasetSchema())
def get_specific_dataset_by_id(dataset):
    """Get a dataset given its identifier."""
    if dataset.deleted and not DatasetEditPermission(dataset).can():
        abort(410, 'Dataset has been deleted')
    return dataset


@apiv2.route('/datasets/<dataset:dataset>/resources/', endpoint='resources', methods=['GET'])
@use_kwargs(resources_parser_args, location="query")
@marshal_with(ResourcePaginationSchema())
def get_resources_paginated(dataset, **kwargs):
    """Get the given dataset resources, paginated."""
    page = kwargs['page']
    page_size = kwargs['page_size']
    next_page = f"{url_for('apiv2.resources', dataset=dataset.id, _external=True)}?page={page + 1}&page_size={page_size}"
    previous_page = f"{url_for('apiv2.resources', dataset=dataset.id, _external=True)}?page={page - 1}&page_size={page_size}"
    res = dataset.resources

    if kwargs.get('type'):
        res = [elem for elem in res if elem['type'] == kwargs['type']]
        next_page += f"&type={kwargs['type']}"
        previous_page += f"&type={kwargs['type']}"

    if kwargs.get('q'):
        res = [elem for elem in res if kwargs['q'].lower() in elem['title'].lower()]
        next_page += f"&q={kwargs['q']}"
        previous_page += f"&q={kwargs['q']}"

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


@apiv2.route('/resources/<uuid:rid>/', endpoint='resource', methods=['GET'])
@marshal_with(ResourceWithDatasetIdSchema())
def get_specific_resource_by_rid(rid):
    """Get a specific resource given its identifier."""
    dataset = Dataset.objects(resources__id=rid).first()
    if dataset:
        resource = get_by(dataset.resources, 'id', rid)
    else:
        resource = CommunityResource.objects(id=rid).first()
    if not resource:
        abort(404, 'Resource does not exist')

    return {
        'resource': resource,
        'dataset_id': dataset.id if dataset else None
    }
