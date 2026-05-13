from flask import current_app, request
from flask_login import current_user
from werkzeug.exceptions import BadRequest

from udata.api import API, api, fields
from udata.api_fields import patch
from udata.core.dataservices.models import Dataservice
from udata.core.dataset.api_fields import dataset_fields
from udata.flask_mongoengine.pagination import Pagination
from udata.harvest.backends import get_enabled_backends
from udata.mongo.queryset import DBPaginator

from . import actions
from .forms import HarvestSourceForm
from .models import (
    VALIDATION_ACCEPTED,
    HarvestItem,
    HarvestJob,
    HarvestSource,
    HarvestSourceValidation,
)

ns = api.namespace("harvest", "Harvest related operations")


# Manual preview-specific models: previews don't have a stable ID/URL since
# they describe an unsaved harvest, so we expose them with stubbed `uri`/`page`/...
preview_dataservice_fields = api.clone(
    "DataservicePreview",
    Dataservice.__ref_fields__,
    {
        "self_web_url": fields.Raw(
            attribute=lambda _d: None, description="The dataservice webpage URL (fake)"
        ),
        "self_api_url": fields.Raw(
            attribute=lambda _d: None, description="The dataservice API URL (fake)"
        ),
    },
)


preview_dataset_fields = api.clone(
    "DatasetPreview",
    dataset_fields,
    {
        "uri": fields.Raw(attribute=lambda _d: None, description="The dataset API URL (fake)"),
        "page": fields.Raw(attribute=lambda _d: None, description="The dataset page URL (fake)"),
    },
)

preview_item_fields = api.clone(
    "HarvestItemPreview",
    HarvestItem.__read_fields__,
    {
        "dataset": fields.Nested(
            preview_dataset_fields, description="The processed dataset", allow_null=True
        ),
        "dataservice": fields.Nested(
            preview_dataservice_fields, description="The processed dataservice", allow_null=True
        ),
    },
)

preview_job_fields = api.clone(
    "HarvestJobPreview",
    HarvestJob.__read_fields__,
    {
        "items": fields.List(
            fields.Nested(preview_item_fields), description="The job collected items"
        ),
    },
)


filter_fields = api.model(
    "HarvestFilter",
    {
        "label": fields.String(description="A localized human-readable label"),
        "key": fields.String(description="The filter key"),
        "type": fields.String(description="The filter expected type"),
        "description": fields.String(description="The filter details"),
    },
)

feature_fields = api.model(
    "HarvestFeature",
    {
        "label": fields.String(description="A localized human-readable and descriptive label"),
        "key": fields.String(description="The feature key"),
        "description": fields.String(description="Some details about the behavior"),
        "default": fields.Boolean(description="The feature default state (true is enabled)"),
    },
)

harvest_extra_fields = api.model(
    "HarvestExtraConfig",
    {
        "label": fields.String(description="A localized human-readable and descriptive label"),
        "key": fields.String(description="The config key"),
        "description": fields.String(description="Some details about the behavior"),
        "default": fields.String(description="The config default value"),
    },
)

backend_fields = api.model(
    "HarvestBackend",
    {
        "id": fields.String(description="The backend identifier"),
        "label": fields.String(description="The backend display name"),
        "filters": fields.List(
            fields.Nested(filter_fields), description="The backend supported filters"
        ),
        "features": fields.List(
            fields.Nested(feature_fields), description="The backend optional features"
        ),
        "extra_configs": fields.List(
            fields.Nested(harvest_extra_fields),
            description="The backend extra configuration variables",
        ),
    },
)


# Source listing accepts owner/deleted filters that are not auto-generated
# from the model fields, so we extend the index parser.
source_parser = HarvestSource.__index_parser__.copy()
source_parser.add_argument(
    "owner", type=str, location="args", help="The organization or user ID to filter on"
)
source_parser.add_argument(
    "deleted",
    type=bool,
    location="args",
    default=False,
    help="Include sources flagged as deleted",
)


@ns.route("/sources/", endpoint="harvest_sources")
class SourcesAPI(API):
    @api.doc("list_harvest_sources")
    @api.expect(source_parser)
    @api.marshal_list_with(HarvestSource.__page_fields__)
    def get(self):
        """List all harvest sources"""
        args = source_parser.parse_args()

        sources = HarvestSource.objects()

        if not args["deleted"]:
            sources = sources.visible()

        # `owner` is overloaded here: it matches sources owned by the user
        # OR by the organization, so we cannot reuse the auto-generated
        # `owner` filter from the Owned mixin (which only matches `owner=`).
        if args["owner"]:
            sources = sources.owned_by(args["owner"])

        if args["q"]:
            phrase_query = " ".join([f'"{elem}"' for elem in args["q"].split(" ")])
            sources = sources.search_text(phrase_query)

        return sources.paginate(args["page"], args["page_size"])

    @api.secure
    @api.doc("create_harvest_source")
    @api.expect(HarvestSource.__write_fields__)
    @api.marshal_with(HarvestSource.__read_fields__)
    def post(self):
        """Create a new harvest source"""
        form = api.validate(HarvestSourceForm)
        if form.organization.data:
            form.organization.data.permissions["harvest"].test()
        source = actions.create_source(**form.data)
        return source, 201


@ns.route("/source/<harvest_source:source>/", endpoint="harvest_source")
class SourceAPI(API):
    @api.doc("get_harvest_source")
    @api.marshal_with(HarvestSource.__read_fields__)
    def get(self, source: HarvestSource):
        """Get a single source given an ID or a slug"""
        return source

    @api.secure
    @api.doc("update_harvest_source")
    @api.expect(HarvestSource.__write_fields__)
    @api.marshal_with(HarvestSource.__read_fields__)
    def put(self, source: HarvestSource):
        """Update a harvest source"""
        source.permissions["edit"].test()
        form = api.validate(HarvestSourceForm, source)
        source = actions.update_source(source, form.data)
        return source

    @api.secure
    @api.doc("delete_harvest_source")
    @api.marshal_with(HarvestSource.__read_fields__)
    def delete(self, source: HarvestSource):
        source.permissions["delete"].test()
        return actions.delete_source(source), 204


@ns.route("/source/<harvest_source:source>/validate/", endpoint="validate_harvest_source")
class ValidateSourceAPI(API):
    @api.doc("validate_harvest_source")
    @api.secure
    @api.expect(HarvestSourceValidation.__write_fields__)
    @api.marshal_with(HarvestSource.__read_fields__)
    def post(self, source: HarvestSource):
        """Validate or reject an harvest source"""
        source.permissions["validate"].test()
        validation = patch(HarvestSourceValidation(), request)
        if validation.state == VALIDATION_ACCEPTED:
            return actions.validate_source(source, validation.comment)
        return actions.reject_source(source, validation.comment)


@ns.route("/source/<harvest_source:source>/run/", endpoint="run_harvest_source")
class RunSourceAPI(API):
    @api.doc("run_harvest_source")
    @api.secure
    @api.marshal_with(HarvestSource.__read_fields__)
    def post(self, source: HarvestSource):
        enabled = current_app.config.get("HARVEST_ENABLE_MANUAL_RUN")
        if not enabled and not current_user.sysadmin:
            api.abort(
                400,
                "Cannot run source manually. Please contact the platform if you need to reschedule the harvester.",
            )

        source.permissions["run"].test()

        if source.validation.state != VALIDATION_ACCEPTED:
            api.abort(400, "Source is not validated. Please validate the source before running.")

        actions.launch(source)

        return source


@ns.route("/source/<harvest_source:source>/schedule/", endpoint="schedule_harvest_source")
class ScheduleSourceAPI(API):
    @api.doc("schedule_harvest_source")
    @api.secure
    @api.expect((str, "A cron expression"))
    @api.marshal_with(HarvestSource.__read_fields__)
    def post(self, source: HarvestSource):
        """Schedule an harvest source"""
        source.permissions["schedule"].test()
        # Handle both syntax: quoted and unquoted
        try:
            data = request.json
        except BadRequest:
            data = request.data.decode("utf-8")
        return actions.schedule(source, data)

    @api.doc("unschedule_harvest_source")
    @api.secure
    @api.marshal_with(HarvestSource.__read_fields__)
    def delete(self, source: HarvestSource):
        """Unschedule an harvest source"""
        source.permissions["schedule"].test()
        return actions.unschedule(source), 204


@ns.route("/source/preview/", endpoint="preview_harvest_source_config")
class PreviewSourceConfigAPI(API):
    @api.secure
    @api.expect(HarvestSource.__write_fields__)
    @api.doc("preview_harvest_source_config")
    @api.marshal_with(preview_job_fields)
    def post(self):
        """Preview an harvesting from a source created with the given payload"""
        form = api.validate(HarvestSourceForm)
        if form.organization.data:
            form.organization.data.permissions["harvest"].test()
        return actions.preview_from_config(**form.data)


@ns.route("/source/<harvest_source:source>/preview/", endpoint="preview_harvest_source")
class PreviewSourceAPI(API):
    @api.secure
    @api.doc("preview_harvest_source")
    @api.marshal_with(preview_job_fields)
    def get(self, source: HarvestSource):
        """Preview a single harvest source given an ID or a slug"""
        source.permissions["preview"].test()
        return actions.preview(source)


page_parser = api.page_parser()


@ns.route("/source/<harvest_source:source>/jobs/", endpoint="harvest_jobs")
class JobsAPI(API):
    @api.doc("list_harvest_jobs")
    @api.expect(page_parser)
    @api.marshal_with(HarvestJob.__page_fields__)
    def get(self, source: HarvestSource):
        """List all jobs for a given source"""
        args = page_parser.parse_args()
        qs = HarvestJob.objects(source=source)
        qs = qs.order_by("-created")
        return qs.paginate(args["page"], args["page_size"])


@ns.route("/job/<string:ident>/", endpoint="harvest_job")
class JobAPI(API):
    @api.doc("get_harvest_job")
    @api.marshal_with(HarvestJob.__read_fields__)
    def get(self, ident):
        """Get a single job given an ID"""
        return actions.get_job(ident)


@ns.route("/job/<string:ident>/items/", endpoint="harvest_job_items")
class JobItemsAPI(API):
    @api.doc("list_harvest_job_items")
    @api.expect(HarvestItem.__index_parser__)
    @api.marshal_with(HarvestItem.__page_fields__)
    def get(self, ident):
        """List the items of a given harvest job (paginated)"""
        job = actions.get_job(ident)
        args = HarvestItem.__index_parser__.parse_args()
        # Items are embedded documents on the job, so the auto-generated
        # apply_sort_filters (which calls queryset.filter) does not apply here.
        items = job.items
        if args["status"]:
            items = [item for item in items if item.status == args["status"]]
        # Wrap in DBPaginator so the pager marshaller can compute
        # next_page/previous_page URLs from has_next/has_prev.
        return DBPaginator(Pagination(items, args["page"], args["page_size"]))


@ns.route("/backends/", endpoint="harvest_backends")
class ListBackendsAPI(API):
    @api.doc("harvest_backends")
    @api.marshal_with(backend_fields)
    def get(self):
        """List all available harvest backends"""
        return sorted(
            [
                {
                    "id": b.name,
                    "label": b.display_name,
                    "filters": [f.as_dict() for f in b.filters],
                    "features": [f.as_dict() for f in b.features],
                    "extra_configs": [f.as_dict() for f in b.extra_configs],
                }
                for b in get_enabled_backends().values()
            ],
            key=lambda b: b["label"],
        )
