import logging

from flask import url_for, abort, jsonify

from webargs import fields as arg_field
from webargs.flaskparser import use_args


from udata import search
from udata.api import apiv2_blueprint as apiv2
from udata.utils import get_by
from .models import Dataset, CommunityResource
from .permissions import DatasetEditPermission
from .apiv2_schemas import DatasetSchema, DatasetPaginationSchema, ResourcePaginationSchema, SpecificResourceSchema
from .search import DatasetSearch


DEFAULT_SORTING = '-created_at'


log = logging.getLogger(__name__)


search_arguments = DatasetSearch.as_request_parser()


resources_parser_args = {
    'page': arg_field.Int(load_default=1),
    'page_size': arg_field.Int(load_default=50),
    'type': arg_field.Str(),
    'q': arg_field.Str()
}


@apiv2.route('/datasets/search/', endpoint='dataset_search', methods=['GET'])
@use_args(search_arguments, location="query")
def get_dataset_search(args):
    """Datasets search endpoint.
    ---
    get:
      parameters:
      - in: query
        name: q
        required: true
        schema:
          type: string
      - in: query
        name: page
        schema:
          type: integer
          default: 1
      - in: query
        name: page_size
        schema:
          type: integer
          default: 20
      - in: query
        name: sort
        schema:
          type: string
          enum: [created, reuses, followers, views]
      - in: query
        name: tag
        schema:
          type: string
      - in: query
        name: organization
        schema:
          type: string
      - in: query
        name: owner
        schema:
          type: string
      - in: query
        name: geozone
        schema:
          type: string
      - in: query
        name: granularity
        schema:
          type: string
      - in: query
        name: format
        schema:
          type: string
      - in: query
        name: schema
        schema:
          type: string
      - in: query
        name: temporal_coverage
        schema:
          type: string
      - in: query
        name: badge
        schema:
          type: string
      - in: query
        name: featured
        schema:
          type: boolean
      - in: query
        name: license
        schema:
          type: string
      responses:
        200:
          content:
            application/json:
              schema: DatasetPaginationSchema
        500:
          content:
            text/plain:
              schema:
                type: string
        501:
          content:
            text/plain:
              schema:
                type: string
    """
    try:
        result = search.query(Dataset, **args)
        return jsonify(DatasetPaginationSchema().dump(result))
    except NotImplementedError:
        abort(501, 'Search endpoint not enabled')
    except RuntimeError:
        abort(500, 'Internal search service error')


@apiv2.route('/datasets/<dataset:dataset>/', endpoint='dataset', methods=['GET'])
def get_specific_dataset_by_id(dataset):
    """Get a dataset given its identifier.
    ---
    get:
      parameters:
      - in: path
        name: dataset_id
        schema:
          type: string
      responses:
        200:
          content:
            application/json:
              schema: DatasetSchema
        410:
          content:
            text/plain:
              schema:
                type: string
    """
    if dataset.deleted and not DatasetEditPermission(dataset).can():
        abort(410, 'Dataset has been deleted')
    return jsonify(DatasetSchema().dump(dataset))


@apiv2.route('/datasets/<dataset:dataset>/resources/', endpoint='resources', methods=['GET'])
@use_args(resources_parser_args, location="query")
def get_resources_paginated(args, dataset):
    """Get the given dataset resources, paginated.
    ---
    get:
      parameters:
      - in: path
        name: dataset_id
        schema:
          type: string
      - in: query
        name: q
        schema:
          type: string
      - in: query
        name: page
        schema:
          type: integer
          default: 1
      - in: query
        name: page_size
        schema:
          type: integer
          default: 20
      - in: query
        name: type
        schema:
          type: string
      responses:
        200:
          content:
            application/json:
              schema: ResourcePaginationSchema
    """
    page = args['page']
    page_size = args['page_size']
    next_page = f"{url_for('apiv2.resources', dataset=dataset.id, _external=True)}?page={page + 1}&page_size={page_size}"
    previous_page = f"{url_for('apiv2.resources', dataset=dataset.id, _external=True)}?page={page - 1}&page_size={page_size}"
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

    response = {
        'data': paginated_result,
        'next_page': next_page if page_size + offset < len(res) else None,
        'page': page,
        'page_size': page_size,
        'previous_page': previous_page if page > 1 else None,
        'total': len(res),
    }
    return jsonify(ResourcePaginationSchema().dump(response))


@apiv2.route('/datasets/resources/<uuid:rid>/', endpoint='resource', methods=['GET'])
def get_specific_resource_by_rid(rid):
    """Get a specific resource given its identifier.
    ---
    get:
      parameters:
      - in: path
        name: rid
        schema:
          type: string
      responses:
        200:
          content:
            application/json:
              schema: SpecificResourceSchema
        404:
          content:
            text/plain:
              schema:
                type: string
    """
    dataset = Dataset.objects(resources__id=rid).first()
    if dataset:
        resource = get_by(dataset.resources, 'id', rid)
    else:
        resource = CommunityResource.objects(id=rid).first()
    if not resource:
        abort(404, 'Resource does not exist')

    response = {
        'resource': resource,
        'dataset_id': dataset.id if dataset else None
    }
    return jsonify(SpecificResourceSchema().dump(response))
