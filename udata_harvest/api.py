# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.api import api, API, fields
from udata.auth import admin_permission

from udata.core.dataset.api_fields import dataset_ref_fields

from . import actions
from .models import HARVEST_JOB_STATUS, HARVEST_ITEM_STATUS, HarvestJob

ns = api.namespace('harvest', 'Harvest related operations')

error_fields = api.model('HarvestError', {
    'created_at': fields.ISODateTime(description='The error creation date', required=True),
    'message': fields.String(description='The error short message', required=True),
    'details': fields.String(description='Optionnal details (ie. stacktrace)'),
})

item_fields = api.model('HarvestItem', {
    'remote_id': fields.String(description='The item remote ID to process', required=True),
    'dataset': fields.Nested(dataset_ref_fields, description='The processed dataset'),
    'status': fields.String(description='The item status', required=True, enum=HARVEST_ITEM_STATUS.keys()),
    'created': fields.ISODateTime(description='The item creation date', required=True),
    'started': fields.ISODateTime(description='The item start date'),
    'ended': fields.ISODateTime(description='The item end date'),
    'errors': api.as_list(fields.Nested(error_fields, description='The item errors')),
    'args': fields.List(fields.String, description='The item positional arguments', default=[]),
    'kwargs': fields.Raw(description='The item keyword arguments', default={}),
})

source_fields = api.model('HarvestSource', {
    'id': fields.String(description='The source unique identifier', required=True),
    'name': fields.String(description='The source display name', required=True),
    'description': fields.String(description='The source description'),
    'url': fields.String(description='The source base URL', required=True),
    'backend': fields.String(description='The source backend', required=True, enum=actions.list_backends()),
    'config': fields.Raw(description='The configuration as key-value pairs'),
    'args': fields.List(fields.Raw, description='The job execution arguments', default=[]),
    'kwargs': fields.Raw(description='The job execution keyword arguments', default={}),
    'created_at': fields.ISODateTime(description='The source creation date', required=True),
    'active': fields.Boolean(description='Is this source active', required=True, default=False),
})

job_fields = api.model('HarvestJob', {
    'id': fields.String(description='The job execution ID', required=True),
    'created': fields.ISODateTime(description='The job creation date', required=True),
    'started': fields.ISODateTime(description='The job start date'),
    'ended': fields.ISODateTime(description='The job end date'),
    'status': fields.String(description='The job status', required=True, enum=HARVEST_JOB_STATUS.keys()),
    'errors': api.as_list(fields.Nested(error_fields, description='The job initialization errors')),
    'items': api.as_list(fields.Nested(item_fields, description='The job items')),
    'source': fields.String(description='The source owning the job', required=True),
})

job_page_fields = api.model('HarvestJobPage', fields.pager(job_fields))


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


# @ns.route('/source/<string:ident>/run', endpoint='harvest_source_run')
# @api.doc(params={'ident': 'A source ID or slug'})
# class SourceRunAPI(API):
#     @api.doc(id='get_source')
#     @api.marshal_with(source_fields)
#     def post(self, ident):
#         '''Get a single source given an ID or a slug'''
#         return actions.launch(ident)

#     @api.secure('admin')
#     @api.marshal_with(job_fields)
#     def put(self, id):
#         '''Update a single scheduled job'''
#         task = self.get_or_404(id)
#         if 'crontab' in request.json:
#             task.interval = None
#             task.crontab = PeriodicTask.Crontab()
#             form = api.validate(CrontabTaskForm, task)
#         else:
#             task.crontab = None
#             task.interval = PeriodicTask.Interval()
#             form = api.validate(IntervalTaskForm, task)
#         return form.save()

#     @api.secure('admin')
#     @api.doc(responses={204: 'Successfuly deleted'})
#     def delete(self, id):
#         '''Delete a single scheduled job'''
#         task = self.get_or_404(id)
#         task.delete()
#         return '', 204


parser = api.parser()
parser.add_argument('page', type=int, default=1, location='args', help='The page to fetch')
parser.add_argument('page_size', type=int, default=20, location='args', help='The page size to fetch')


@ns.route('/source/<string:ident>/jobs/', endpoint='harvest_jobs')
class JobsAPI(API):
    @api.doc('list_harvest_jobs', parser=parser)
    @api.marshal_with(job_page_fields)
    def get(self, ident):
        '''List all jobs for a given source'''
        args = parser.parse_args()
        source = actions.get_source(ident)
        return HarvestJob.objects(source=source).order_by('-created').paginate(args['page'], args['page_size'])


@ns.route('/job/<string:ident>/', endpoint='harvest_job')
class JobAPI(API):
    @api.doc('get_harvest_job', parser=parser)
    @api.marshal_with(job_fields)
    def get(self, ident):
        '''List all jobs for a given source'''
        return actions.get_job(ident)
        # args = parser.parse_args()
        # return HarvestJob.objects(source=source).order_by('-created').paginate(args['page'], args['page_size'])


@ns.route('/backends', endpoint='harvest_backends')
class ListBackendAPI(API):
    @api.doc(model=[str])
    def get(self):
        '''List all available harvesters'''
        return actions.list_backends()


@ns.route('/job_status', endpoint='havest_job_status')
class ListHarvesterAPI(API):
    @api.doc(model=[str])
    def get(self):
        '''List all available harvesters'''
        return actions.list_backends()
