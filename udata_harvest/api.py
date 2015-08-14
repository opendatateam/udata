# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.api import api, API, fields
from udata.auth import admin_permission

from udata.core.dataset.api_fields import dataset_ref_fields

from . import actions
from .models import HARVEST_JOB_STATUS, HARVEST_ITEM_STATUS, HarvestJob

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

source_fields = api.model('HarvestSource', {
    'id': fields.String(description='The source unique identifier',
                        readonly=True),
    'name': fields.String(description='The source display name',
                          required=True),
    'description': fields.String(description='The source description'),
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
    'config': fields.Raw(description='The source specific configuration',
                         default={}),
    'last_job': fields.Nested(job_fields,
                              description='The last job for this source',
                              allow_null=True)
})

backend_fields = api.model('HarvestBackend', {
    'id': fields.String(description='The backend identifier'),
    'label': fields.String(description='The backend display name')
})


@ns.route('/sources/', endpoint='harvest_sources')
class SourcesAPI(API):
    @api.doc('list_harvest_sources')
    @api.marshal_list_with(source_fields)
    def get(self):
        '''List all harvest sources'''
        return actions.list_sources()

    @api.doc('create_harvest_source')
    @api.secure(admin_permission)
    @api.marshal_with(source_fields)
    def post(self):
        '''Create a new harvests source'''
        # if 'crontab' in request.json and 'interval' in request.json:
        #     api.abort(400, 'Cannot define both interval and crontab schedule')
        # if 'crontab' in request.json:
        #     form = api.validate(CrontabTaskForm)
        # else:
        #     form = api.validate(IntervalTaskForm)
        # return form.save(), 201


@ns.route('/source/<string:ident>', endpoint='harvest_source')
@api.doc(params={'ident': 'A source ID or slug'})
class SourceAPI(API):
    @api.doc('get_harvest_source')
    @api.marshal_with(source_fields)
    def get(self, ident):
        '''Get a single source given an ID or a slug'''
        return actions.get_source(ident)

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
        return qs.order_by('-created').paginate(args['page'], args['page_size'])


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
