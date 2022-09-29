import logging
from datetime import datetime

from flask import url_for, abort, request, redirect, make_response

from flask_apispec import use_kwargs, marshal_with
from webargs import fields


from udata import search
from udata.app import csrf
from udata.api import apiv2_blueprint as apiv2, UDataApiV2
from udata.api.parsers import ModelApiV2Parser
from udata.auth import admin_permission
from udata.core.badges import api as badges_api
from udata.utils import get_by
from udata.rdf import (
    RDF_EXTENSIONS,
    negociate_content, graph_response
)
from .forms import DatasetForm, ResourceForm, ResourcesListForm
from .models import Dataset, CommunityResource, License, Resource
from .permissions import DatasetEditPermission, ResourceEditPermission
from .apiv2_schemas import (
    DatasetSchema, ResourcePaginationSchema, ResourceWithDatasetIdSchema, DatasetPaginationSchema, ResourceSchema
)
from .rdf import dataset_to_rdf
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


#############################
#  Dataset Search Endpoint  #
#############################

@apiv2.route('/datasets/search/', endpoint='dataset_search', methods=['GET'])
@use_kwargs(search_arguments, location="query")
@marshal_with(DatasetPaginationSchema)
def get_dataset_search(**kwargs):
    """Datasets search endpoint."""
    try:
        return search.query(Dataset, **kwargs)
    except NotImplementedError:
        abort(501, 'Search endpoint not enabled')
    except RuntimeError:
        abort(500, 'Internal search service error')


#############################
#  Dataset Group Endpoints  #
#############################

@apiv2.route('/datasets/', endpoint='list_datasets', methods=['GET'])
@use_kwargs(dataset_parser_args, location="query")
@marshal_with(DatasetPaginationSchema)
def get_datasets_list(**kwargs):
    """List or search all datasets"""
    datasets = Dataset.objects(archived=None, deleted=None, private=False)
    datasets = dataset_parser.parse_filters(datasets, kwargs)

    sort = kwargs.get('sort', None) or ('$text_score' if kwargs.get('sort', None) else None) or DEFAULT_SORTING
    return datasets.order_by(sort).paginate(kwargs['page'], kwargs['page_size'])


@apiv2.route('/datasets/', endpoint='create_dataset', methods=['POST'])
@UDataApiV2.secure
@marshal_with(DatasetSchema, code=201)
def post_new_dataset(**kwargs):
    """Create a new dataset"""
    form = UDataApiV2.validate(DatasetForm)
    dataset = form.save()
    return dataset, 201


@apiv2.route('/datasets/badges/', endpoint='get_available_dataset_badges', methods=['GET'])
def get_available_dataset_badges():
    """List all available dataset badges and their labels"""
    return Dataset.__badges__


##############################
#   Dataset Item Endpoints   #
##############################

@apiv2.route('/datasets/<dataset:dataset>/', endpoint='get_dataset', methods=['GET'])
@marshal_with(DatasetSchema)
def get_specific_dataset_by_id(dataset):
    """Get a dataset given its identifier."""
    if dataset.deleted and not DatasetEditPermission(dataset).can():
        abort(410, 'Dataset has been deleted')
    return dataset


@apiv2.route('/datasets/<dataset:dataset>/', endpoint='update_dataset', methods=['PUT'])
@csrf.exempt
@UDataApiV2.secure
@marshal_with(DatasetSchema)
def update_specific_dataset_by_id(dataset):
    """Update a dataset given its identifier"""
    request_deleted = request.json.get('deleted', True)
    if dataset.deleted and request_deleted is not None:
        abort(410, 'Dataset has been deleted')
    DatasetEditPermission(dataset).test()
    dataset.last_modified = datetime.now()
    form = UDataApiV2.validate(DatasetForm, dataset)
    return form.save()


@apiv2.route('/datasets/<dataset:dataset>/', endpoint='delete_dataset', methods=['DELETE'])
@UDataApiV2.secure
def delete_specific_dataset_by_id(dataset):
    """Delete a dataset given its identifier"""
    if dataset.deleted:
        abort(410, 'Dataset has been deleted')
    DatasetEditPermission(dataset).test()
    dataset.deleted = datetime.now()
    dataset.last_modified = datetime.now()
    dataset.save()
    return '', 204


@apiv2.route('/datasets/<dataset:dataset>/featured/', endpoint='mark_dataset_featured', methods=['POST'])
@UDataApiV2.secure(admin_permission)
@marshal_with(DatasetSchema)
def mark_specific_dataset_featured(dataset):
    """Mark the dataset as featured"""
    dataset.featured = True
    dataset.save()
    return dataset


@apiv2.route('/datasets/<dataset:dataset>/featured/', endpoint='unmark_dataset_featured', methods=['DELETE'])
@UDataApiV2.secure(admin_permission)
@marshal_with(DatasetSchema)
def unmark_specific_dataset_featured(dataset):
    """Unmark the dataset as featured"""
    dataset.featured = False
    dataset.save()
    return dataset


@apiv2.route('/datasets/<dataset:dataset>/rdf', endpoint='get_dataset_rdf', methods=['GET'])
def get_dataset_rdf(dataset):
    """Get dataset rdf"""
    format = RDF_EXTENSIONS[negociate_content()]
    url = url_for('api.dataset_rdf_format', dataset=dataset.id, format=format)
    return redirect(url)


@apiv2.route('/datasets/<dataset:dataset>/rdf.<format>', endpoint='get_dataset_rdf_format', methods=['GET'])
def get_dataset_rdf_format(dataset):
    """Get dataset rdf specific format"""
    if not DatasetEditPermission(dataset).can():
        if dataset.private:
            abort(404)
        elif dataset.deleted:
            abort(410)

    resource = dataset_to_rdf(dataset)
    # bypass flask-restplus make_response, since graph_response
    # is handling the content negociation directly
    return make_response(*graph_response(resource, format))


@apiv2.route('/datasets/<dataset:dataset>/badges/', endpoint='add_dataset_badges', methods=['POST'])
@UDataApiV2.secure(admin_permission)
@use_kwargs(badges_api.BadgeSchema, location="json")
@marshal_with(badges_api.BadgeSchema)
def post_dataset_badges(dataset, **kwargs):
    """Create a new badge for a given dataset"""
    return badges_api.add(dataset)


@apiv2.route('/<dataset:dataset>/badges/<badge_kind>/', endpoint='delete_dataset_badges', methods=['DELETE'])
@UDataApiV2.secure(admin_permission)
@marshal_with(badges_api.BadgeSchema)
def delete_dataset_badges(dataset, badge_kind):
    """Delete a badge for a given dataset"""
    return badges_api.remove(dataset, badge_kind)


#################################
#   Resources Group Endpoints   #
#################################

@apiv2.route('/datasets/<dataset:dataset>/resources/', endpoint='get_dataset_resources_paginated', methods=['GET'])
@use_kwargs(resources_parser_args, location="query")
@marshal_with(ResourcePaginationSchema)
def get_resources_paginated(dataset, **kwargs):
    """Get the given dataset resources, paginated."""
    page = kwargs['page']
    page_size = kwargs['page_size']
    next_page = f"{url_for('apiv2.get_dataset_resources_paginated', dataset=dataset.id, _external=True)}?page={page + 1}&page_size={page_size}"
    previous_page = f"{url_for('apiv2.get_dataset_resources_paginated', dataset=dataset.id, _external=True)}?page={page - 1}&page_size={page_size}"
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


@apiv2.route('/datasets/<dataset:dataset>/resources/', endpoint='create_dataset_resource', methods=['POST'])
@UDataApiV2.secure
@marshal_with(ResourceSchema, code=201)
def create_dataset_resource(dataset):
    """Create a new resource for a given dataset"""
    ResourceEditPermission(dataset).test()
    form = UDataApiV2.validate(ResourceForm)
    resource = Resource()
    if form._fields.get('filetype').data != 'remote':
        return 'This endpoint only supports remote resources', 400
    form.populate_obj(resource)
    dataset.add_resource(resource)
    dataset.last_modified = datetime.now()
    dataset.save()
    return resource, 201


@apiv2.route('/datasets/<dataset:dataset>/resources/', endpoint='reorder_dataset_resources', methods=['PUT'])
@UDataApiV2.secure
@marshal_with(ResourceSchema, code=200)
def reorder_dataset_resources(dataset):
    """Reorder resources"""
    ResourceEditPermission(dataset).test()
    data = {'resources': request.json}
    form = ResourcesListForm.from_json(data, obj=dataset, instance=dataset,
                                       meta={'csrf': False})
    if not form.validate():
        abort(400, errors=form.errors['resources'])

    dataset = form.save()
    return dataset.resources, 200


################################
#   Resources Item Endpoints   #
################################

@apiv2.route('/datasets/resources/<uuid:rid>/', endpoint='resource', methods=['GET'])
@marshal_with(ResourceWithDatasetIdSchema)
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
