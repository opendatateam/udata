import logging

from flask import url_for, abort

from flask_apispec import use_kwargs, marshal_with
from webargs import fields


from udata import search
from udata.api import apiv2_blueprint as apiv2
from udata.api.parsers import ModelApiV2Parser
from udata.utils import get_by
from .models import Dataset, CommunityResource
from .permissions import DatasetEditPermission
from .apiv2_schemas import DatasetSchema, ResourcePaginationSchema, ResourceWithDatasetIdSchema, DatasetPaginationSchema
from .search import DatasetSearch


DEFAULT_SORTING = '-created_at'


log = logging.getLogger(__name__)


search_arguments = DatasetSearch.as_request_parser()

resources_parser_args = ModelApiV2Parser.as_request_parser()

resources_parser_args.update({
    'type': fields.Str()
})


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


@apiv2.route('/datasets/resources/<uuid:rid>/', endpoint='resource', methods=['GET'])
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
