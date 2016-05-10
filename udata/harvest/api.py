# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.api import api, API, fields
from udata.auth import admin_permission

from udata.core.dataset.api_fields import dataset_ref_fields, dataset_fields
from udata.core.organization.api_fields import org_ref_fields
from udata.core.organization.permissions import EditOrganizationPermission
from udata.core.user.api_fields import user_ref_fields

from . import actions
from .forms import HarvestSourceForm, HarvestSourceValidationForm
from .models import (
    HARVEST_JOB_STATUS, HARVEST_ITEM_STATUS, HarvestJob,
    VALIDATION_STATES, VALIDATION_ACCEPTED
)

ns = api.namespace('harvest', 'Harvest related operations')

backends_ids = [b.name for b in actions.list_backends()]

error_fields = api.model('HarvestError', {
    'created_at': fields.ISODateTime(description='The error creation date',
                                     required=True),
    'message': fields.String(description='The error short message',
                             required=True),
    'details': fields.String(description='Optionnal details (ie. stacktrace)'),
})

item_fields = api.model('HarvestItem', {
    'remote_id': fields.String(description='The item remote ID to process',
                               required=True),
    'dataset': fields.Nested(dataset_ref_fields,
                             description='The processed dataset',
                             allow_null=True),
    'status': fields.String(description='The item status',
                            required=True,
                            enum=HARVEST_ITEM_STATUS.keys()),
    'created': fields.ISODateTime(description='The item creation date',
                                  required=True),
    'started': fields.ISODateTime(description='The item start date'),
    'ended': fields.ISODateTime(description='The item end date'),
    'errors': fields.List(fields.Nested(error_fields),
                          description='The item errors'),
    'args': fields.List(fields.String,
                        description='The item positional arguments',
                        default=[]),
    'kwargs': fields.Raw(description='The item keyword arguments',
                         default={}),
})

job_fields = api.model('HarvestJob', {
    'id': fields.String(description='The job execution ID', required=True),
    'created': fields.ISODateTime(description='The job creation date',
                                  required=True),
    'started': fields.ISODateTime(description='The job start date'),
    'ended': fields.ISODateTime(description='The job end date'),
    'status': fields.String(description='The job status',
                            required=True, enum=HARVEST_JOB_STATUS.keys()),
    'errors': fields.List(fields.Nested(error_fields),
                          description='The job initialization errors'),
    'items': fields.List(fields.Nested(item_fields),
                         description='The job collected items'),
    'source': fields.String(description='The source owning the job',
                            required=True),
})

job_page_fields = api.model('HarvestJobPage', fields.pager(job_fields))

validation_fields = api.model('HarvestSourceValidation', {
    'state': fields.String(description='Is it validated or not',
                           enum=VALIDATION_STATES.keys(),
                           required=True),
    'by': fields.Nested(user_ref_fields, allow_null=True, readonly=True,
                        description='Who performed the validation'),
    'on': fields.ISODateTime(
        readonly=True,
        description='Date date on which validation was performed'
    ),
    'comment': fields.String(
        description='A comment about the validation. Required on rejection'
    )
})

source_fields = api.model('HarvestSource', {
    'id': fields.String(description='The source unique identifier',
                        readonly=True),
    'name': fields.String(description='The source display name',
                          required=True),
    'description': fields.Markdown(description='The source description'),
    'url': fields.String(description='The source base URL',
                         required=True),
    'backend': fields.String(description='The source backend',
                             enum=backends_ids,
                             required=True),
    'config': fields.Raw(description='The configuration as key-value pairs'),
    'created_at': fields.ISODateTime(description='The source creation date',
                                     required=True),
    'active': fields.Boolean(description='Is this source active',
                             required=True, default=False),
    'validation': fields.Nested(validation_fields, readonly=True,
                                description='Has the source been validated'),
    'config': fields.Raw(description='The source specific configuration',
                         default={}),
    'last_job': fields.Nested(job_fields,
                              description='The last job for this source',
                              allow_null=True, readonly=True),
    'owner': fields.Nested(user_ref_fields, allow_null=True,
                           description='The owner information'),
    'organization': fields.Nested(org_ref_fields, allow_null=True,
                                  description='The producer organization'),
    'deleted': fields.ISODateTime(description='The source deletion date'),
})

backend_fields = api.model('HarvestBackend', {
    'id': fields.String(description='The backend identifier'),
    'label': fields.String(description='The backend display name')
})

preview_dataset_fields = api.clone('DatasetPreview', dataset_fields, {
    'uri': fields.UrlFor(
        'api.dataset', lambda o: {'dataset': 'not-available'},
        description='The dataset API URI (fake)'),
    'page': fields.UrlFor(
        'datasets.show', lambda o: {'dataset': 'not-available'},
        description='The dataset page URL (fake)'),
})

preview_item_fields = api.clone('HarvestItemPreview', item_fields, {
    'dataset': fields.Nested(preview_dataset_fields,
                             description='The processed dataset',
                             allow_null=True),
})

preview_job_fields = api.clone('HarvestJobPreview', job_fields, {
    'items': fields.List(fields.Nested(preview_item_fields),
                         description='The job collected items'),
})

source_parser = api.parser()
source_parser.add_argument('owner', type=str, location='args',
                           help='The organization or user ID to filter on')


@ns.route('/sources/', endpoint='harvest_sources')
class SourcesAPI(API):
    @api.doc('list_harvest_sources', parser=source_parser)
    @api.marshal_list_with(source_fields)
    def get(self):
        '''List all harvest sources'''
        args = source_parser.parse_args()
        return actions.list_sources(args.get('owner'))

    @api.doc('create_harvest_source')
    @api.secure
    @api.expect(source_fields)
    @api.marshal_with(source_fields)
    def post(self):
        '''Create a new harvests source'''
        form = api.validate(HarvestSourceForm)
        if form.organization.data:
            EditOrganizationPermission(form.organization.data).test()
        source = actions.create_source(**form.data)
        return source, 201


@ns.route('/source/<string:ident>', endpoint='harvest_source')
@api.doc(params={'ident': 'A source ID or slug'})
class SourceAPI(API):
    @api.doc('get_harvest_source')
    @api.marshal_with(source_fields)
    def get(self, ident):
        '''Get a single source given an ID or a slug'''
        return actions.get_source(ident)

    @api.secure
    @api.doc('delete_harvest_source')
    @api.marshal_with(source_fields)
    def delete(self, ident):
        return actions.delete_source(ident), 204


@ns.route('/source/<string:ident>/validate',
          endpoint='validate_harvest_source')
@api.doc(params={'ident': 'A source ID or slug'})
class ValidateSourceAPI(API):
    @api.doc('validate_harvest_source')
    @api.secure(admin_permission)
    @api.expect(validation_fields)
    @api.marshal_with(source_fields)
    def post(self, ident):
        '''Validate or reject an harvest source'''
        form = api.validate(HarvestSourceValidationForm)
        if form.state.data == VALIDATION_ACCEPTED:
            return actions.validate_source(ident, form.comment.data)
        else:
            return actions.reject_source(ident, form.comment.data)


@ns.route('/source/<string:ident>/preview', endpoint='preview_harvest_source')
@api.doc(params={'ident': 'A source ID or slug'})
class PreviewSourceAPI(API):
    @api.doc('preview_harvest_source')
    @api.marshal_with(preview_job_fields)
    def get(self, ident):
        '''Preview a single harvest source given an ID or a slug'''
        return actions.preview(ident)


parser = api.parser()
parser.add_argument('page', type=int, default=1, location='args',
                    help='The page to fetch')
parser.add_argument('page_size', type=int, default=20, location='args',
                    help='The page size to fetch')


@ns.route('/source/<string:ident>/jobs/', endpoint='harvest_jobs')
class JobsAPI(API):
    @api.doc('list_harvest_jobs', parser=parser)
    @api.marshal_with(job_page_fields)
    def get(self, ident):
        '''List all jobs for a given source'''
        args = parser.parse_args()
        source = actions.get_source(ident)
        qs = HarvestJob.objects(source=source)
        qs = qs.order_by('-created')
        return qs.paginate(args['page'], args['page_size'])


@ns.route('/job/<string:ident>/', endpoint='harvest_job')
class JobAPI(API):
    @api.doc('get_harvest_job', parser=parser)
    @api.marshal_with(job_fields)
    def get(self, ident):
        '''List all jobs for a given source'''
        return actions.get_job(ident)


@ns.route('/backends', endpoint='harvest_backends')
class ListBackendsAPI(API):
    @api.doc('harvest_backends')
    @api.marshal_with(backend_fields)
    def get(self):
        '''List all available harvest backends'''
        return [
            {'id': b.name, 'label': b.display_name}
            for b in actions.list_backends()
        ]


@ns.route('/job_status', endpoint='havest_job_status')
class ListHarvesterAPI(API):
    @api.doc(model=[str])
    def get(self):
        '''List all available harvesters'''
        return actions.list_backends()
