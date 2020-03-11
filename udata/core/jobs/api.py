from celery import states
from celery.result import AsyncResult
from celery.utils import get_full_cls_name
from celery.utils.encoding import safe_repr
from flask import request

from udata.api import api, API, fields
from udata.auth import admin_permission
from udata.tasks import schedulables, celery

from .forms import CrontabTaskForm, IntervalTaskForm
from .models import PeriodicTask, PERIODS

ns = api.namespace(
    'workers', 'Asynchronous workers related operations', path='')

crontab_fields = api.model('Crontab', {
    'minute': fields.String(
        description='Cron expression for minute', required=True, default='*'),
    'hour': fields.String(
        description='Cron expression for hour', required=True, default='*'),
    'day_of_week': fields.String(
        description='Cron expression for day of week', required=True,
        default='*'),
    'day_of_month': fields.String(
        description='Cron expression for day of month', required=True,
        default='*'),
    'month_of_year': fields.String(
        description='Cron expression for month of year', required=True,
        default='*'),
})

interval_fields = api.model('Interval', {
    'every': fields.Integer(
        description='The interval without unit', required=True),
    'period': fields.String(
        description='The period/interval type', required=True, enum=PERIODS),
})

job_fields = api.model('Job', {
    'id': fields.String(
        description='The job unique identifier', readonly=True),
    'name': fields.String(description='The job unique name', required=True),
    'description': fields.String(description='The job description'),
    'task': fields.String(
        description='The task name', required=True,
        enum=[job.name for job in schedulables()]),
    'crontab': fields.Nested(crontab_fields, allow_null=True),
    'interval': fields.Nested(interval_fields, allow_null=True),
    'args': fields.List(
        fields.Raw, description='The job execution arguments', default=[]),
    'kwargs': fields.Raw(
        description='The job execution keyword arguments', default={}),
    'schedule': fields.String(
        attribute='schedule_display',
        description='The schedule display', readonly=True),
    'last_run_at': fields.ISODateTime(
        description='The last job execution date', readonly=True),
    'last_run_id': fields.String(
        description='The last execution task id', readonly=True),
    'enabled': fields.Boolean(
        description='Is this job enabled', default=False),
})

task_fields = api.model('Task', {
    'id': fields.String(description='Tha task execution ID', readonly=True),
    'status': fields.String(
        description='Cron expression for hour', readonly=True,
        enum=list(states.ALL_STATES)),
    'result': fields.String(description='The task results if exists'),
    'exc': fields.String(description='The exception thrown during execution'),
    'traceback': fields.String(description='The execution traceback'),
})


@ns.route('/jobs/', endpoint='jobs')
class JobsAPI(API):
    @api.doc(id='list_jobs')
    @api.marshal_list_with(job_fields)
    def get(self):
        '''List all scheduled jobs'''
        return list(PeriodicTask.objects)

    @api.secure(admin_permission)
    @api.expect(job_fields)
    @api.marshal_with(job_fields)
    def post(self):
        '''Create a new scheduled job'''
        if 'crontab' in request.json and 'interval' in request.json:
            api.abort(400, 'Cannot define both interval and crontab schedule')
        if 'crontab' in request.json:
            form = api.validate(CrontabTaskForm)
        else:
            form = api.validate(IntervalTaskForm)
        return form.save(), 201


@ns.route('/jobs/<string:id>', endpoint='job')
@api.param('id', 'A job ID')
class JobAPI(API):
    def get_or_404(self, id):
        task = PeriodicTask.objects(id=id).first()
        if not task:
            api.abort(404)
        return task

    @api.marshal_with(job_fields)
    def get(self, id):
        '''Fetch a single scheduled job'''
        return self.get_or_404(id)

    @api.secure(admin_permission)
    @api.marshal_with(job_fields)
    def put(self, id):
        '''Update a single scheduled job'''
        task = self.get_or_404(id)
        if 'crontab' in request.json:
            task.interval = None
            task.crontab = PeriodicTask.Crontab()
            form = api.validate(CrontabTaskForm, task)
        else:
            task.crontab = None
            task.interval = PeriodicTask.Interval()
            form = api.validate(IntervalTaskForm, task)
        return form.save()

    @api.secure(admin_permission)
    @api.response(204, 'Successfuly deleted')
    def delete(self, id):
        '''Delete a single scheduled job'''
        task = self.get_or_404(id)
        task.delete()
        return '', 204


@ns.route('/tasks/<string:id>', endpoint='task')
class TaskAPI(API):
    @api.marshal_with(task_fields)
    def get(self, id):
        '''Get a tasks status given its ID'''
        result = AsyncResult(id, app=celery)
        status, retval = result.status, result.result
        data = {'id': id, 'status': status, 'result': retval}
        if status in states.EXCEPTION_STATES:
            traceback = result.traceback
            data.update({
                'result': safe_repr(retval),
                'exc': get_full_cls_name(retval.__class__),
                'traceback': traceback,
            })
        return data


@ns.route('/jobs/schedulables', endpoint='schedulable_jobs')
class JobsReferenceAPI(API):
    @api.doc(model=[str])
    def get(self):
        '''List all schedulable jobs'''
        return [job.name for job in schedulables()]
