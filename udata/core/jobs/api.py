from celery import states
from celery.result import AsyncResult
from celery.utils import get_full_cls_name
from flask import request
from kombu.utils.encoding import safe_repr

from udata.api import API, api, fields
from udata.api_fields import patch_and_save
from udata.auth import admin_permission
from udata.tasks import celery, schedulables
from udata.utils import id_or_404

from .models import PeriodicTask

ns = api.namespace("workers", "Asynchronous workers related operations", path="")

task_fields = api.model(
    "Task",
    {
        "id": fields.String(description="Tha task execution ID", readonly=True),
        "status": fields.String(
            description="Cron expression for hour", readonly=True, enum=list(states.ALL_STATES)
        ),
        "result": fields.String(description="The task results if exists"),
        "exc": fields.String(description="The exception thrown during execution"),
        "traceback": fields.String(description="The execution traceback"),
    },
)


@ns.route("/jobs/", endpoint="jobs")
class JobsAPI(API):
    @api.secure(admin_permission)
    @api.doc(id="list_jobs")
    @api.marshal_list_with(PeriodicTask.__read_fields__)
    def get(self):
        """List all scheduled jobs"""
        return list(PeriodicTask.objects)

    @api.secure(admin_permission)
    @api.expect(PeriodicTask.__write_fields__)
    @api.marshal_with(PeriodicTask.__read_fields__)
    def post(self):
        """Create a new scheduled job"""
        return patch_and_save(PeriodicTask(), request), 201


@ns.route("/jobs/<string:id>/", endpoint="job")
@api.param("id", "A job ID")
class JobAPI(API):
    def get_or_404(self, id):
        task = PeriodicTask.objects(id=id).first()
        if not task:
            api.abort(404)
        return task

    @api.secure(admin_permission)
    @api.marshal_with(PeriodicTask.__read_fields__)
    def get(self, id):
        """Fetch a single scheduled job"""
        return self.get_or_404(id_or_404(id))

    @api.secure(admin_permission)
    @api.expect(PeriodicTask.__write_fields__)
    @api.marshal_with(PeriodicTask.__read_fields__)
    def put(self, id):
        """Update a single scheduled job"""
        task = self.get_or_404(id_or_404(id))
        # Sending one schedule and not the other switches type: drop the one left out,
        # so `clean()` only rejects payloads that really carry both.
        if "crontab" in request.json and "interval" not in request.json:
            task.interval = None
        elif "interval" in request.json and "crontab" not in request.json:
            task.crontab = None
        return patch_and_save(task, request)

    @api.secure(admin_permission)
    @api.response(204, "Successfuly deleted")
    def delete(self, id):
        """Delete a single scheduled job"""
        task = self.get_or_404(id_or_404(id))
        task.delete()
        return "", 204


@ns.route("/tasks/<string:id>/", endpoint="task")
class TaskAPI(API):
    @api.secure(admin_permission)
    @api.marshal_with(task_fields)
    def get(self, id):
        """Get a tasks status given its ID"""
        result = AsyncResult(id, app=celery)
        status, retval = result.status, result.result
        data = {"id": id, "status": status, "result": retval}
        if status in states.EXCEPTION_STATES:
            traceback = result.traceback
            data.update(
                {
                    "result": safe_repr(retval),
                    "exc": get_full_cls_name(retval.__class__),
                    "traceback": traceback,
                }
            )
        return data


@ns.route("/jobs/schedulables/", endpoint="schedulable_jobs")
class JobsReferenceAPI(API):
    @api.secure(admin_permission)
    @api.doc(model=[str])
    def get(self):
        """List all schedulable jobs"""
        return [job.name for job in schedulables()]
