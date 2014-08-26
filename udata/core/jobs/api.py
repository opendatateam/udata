# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from celery import states
from celery.result import AsyncResult
from celery.utils import get_full_cls_name
from celery.utils.encoding import safe_repr
from flask import request

from udata.api import api, API, refs, fields
from udata.auth import admin_permission
from udata.tasks import schedulables, celery

from .forms import CrontabTaskForm, IntervalTaskForm
from .models import PeriodicTask

crontab_fields = api.model('Crontab', {
    'minute': fields.String,
    'hour': fields.String,
    'day_of_week': fields.String,
    'day_of_month': fields.String,
    'month_of_year': fields.String,
})

interval_fields = api.model('Interval', {
    'every': fields.Integer,
    'period': fields.String,
})

job_fields = api.model('Job', {
    'id': fields.String,
    'name': fields.String,
    'description': fields.String,
    'task': fields.String,
    'crontab': fields.Nested(crontab_fields, allow_null=True),
    'interval': fields.Nested(interval_fields, allow_null=True),
    'args': fields.List(fields.Raw),
    'kwargs': fields.Raw,
    'schedule': fields.String(attribute='schedule_display'),
    'last_run_at': fields.String,
    'last_run_id': fields.String,
    'enabled': fields.Boolean,
})

task_fields = api.model('Task', {
    'id': fields.String,
    'status': fields.String,
    'result': fields.String,
    'exc': fields.String,
    'traceback': fields.String,
})


@api.route('/jobs/', endpoint='jobs')
class JobsAPI(API):
    @api.marshal_list_with(job_fields)
    def get(self):
        '''List all scheduled jobs'''
        return list(PeriodicTask.objects)

    @api.secure(admin_permission)
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


@api.route('/jobs/<string:id>', endpoint='job')
@api.doc(params={'id': 'A job ID'})
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

    @api.secure('admin')
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

    @api.secure('admin')
    @api.doc(responses={204: 'Successfuly deleted'})
    def delete(self, id):
        '''Delete a single scheduled job'''
        task = self.get_or_404(id)
        task.delete()
        return '', 204


@api.route('/tasks/<string:id>', endpoint='task')
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


@refs.route('/jobs', endpoint='schedulable_jobs')
class JobsReferenceAPI(API):
    @api.doc(model=[str])
    def get(self):
        '''List all schedulable jobs'''
        return [job.name for job in schedulables()]
